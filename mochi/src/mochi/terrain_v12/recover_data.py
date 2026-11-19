"""Recover completed teacher artifacts after a failed batch; no new rollouts."""
import asyncio,copy,gzip,hashlib,json,os
from collections import Counter,defaultdict
from pathlib import Path
import modal
from modal.exception import NotFoundError

async def main():
    source=Path(os.environ['MOCHI_RECOVERY_SOURCE']);p=source/'progress.json';original=json.loads(p.read_text())
    assert original['optimizer_updates_completed']==0 and original['budget_usage_or_reserved'].get('optimizer_updates',0)==0
    if (source/'training-observations.json').exists() and original.get('valid_teacher_sequences') and original.get('data_audit'):
        print('Preserved training dataset is already available; no simulation or model calls.');return
    volume=modal.Volume.from_name('mochi-terrain-v12-artifacts');teachers=[];missing=[];evidence=[]
    for seed in original['protocol']['training_seeds']:
        path=f'{original["run_id"]}/teacher-{seed}.json.gz'
        local=source/f'teacher-{seed}.json'
        try:
            if local.exists():raw=local.read_bytes();row=json.loads(raw)
            else:
                chunks=[]
                async for part in volume.read_file.aio(path):chunks.append(part)
                raw=gzip.decompress(b''.join(chunks));row=json.loads(raw)
        except (FileNotFoundError,NotFoundError):missing.append(seed);continue
        assert row['seed']==seed and not row['preflight']
        teachers.append(row);evidence.append({'seed':seed,'path':path,'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),'receipt':row['receipt'],'valid':row['valid']})
        (source/f'teacher-{seed}.json').write_text(json.dumps(row,separators=(',',':')))
    data=defaultdict(list)
    for row in teachers:
        for item in row['examples']:data[item['domain']].append((item['observation'],item['action']))
    domains=original['protocol']['training']['domains'];assert all(data[d] for d in domains),'Incomplete domain coverage; no training'
    assert any(r['valid'] for r in teachers),'No valid continuous teacher sequence'
    walk=[t for r in teachers for t in r['trials'] if t['domain']=='walk']
    assert any(len({(x['success'],round(x['duration_s'],2)) for x in t['outcomes']})>1 for t in walk),'No consequential walking action difference'
    report=copy.deepcopy(original)
    report['valid_teacher_sequences']=sum(r['valid'] for r in teachers)
    report['data_audit']={d:{'examples':len(data[d]),'labels':dict(Counter(a for _,a in data[d]))} for d in domains}
    report['walking_label_diversity']=len(report['data_audit']['walk']['labels'])
    report['walking_adaptation_qualification']='A single preferred action is a learned fixed preference, not evidence of adaptive control.'
    report['data_recovery']={'new_physical_rollouts':0,'completed_teacher_evidence':evidence,'missing_teacher_seeds':missing,
        'scope':'Only complete immutable teacher artifacts are recovered. Missing and failed workers are retained in the source execution; their partial results are not invented.'}
    counted={r.get('seed') for r in report['physics_receipts'] if r.get('phase')=='Physical training branches on Modal'}
    for row in teachers:
        if row['seed'] not in counted:
            report['physics_receipts'].append({'phase':'Recovered completed teacher artifact','seed':row['seed'],'receipt':row['receipt']})
            report['campaign_modal_rollouts_completed']+=row['receipt']['physical_rollouts']
    (source/'source-progress-original.json').write_text(json.dumps(original,indent=2)+'\n')
    (source/'training-observations.json').write_text(json.dumps(data,indent=2)+'\n');p.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'recovered_complete_teachers':len(teachers),'missing_seeds':missing,'valid_sequences':report['valid_teacher_sequences'],'new_rollouts':0}))

if __name__=='__main__':asyncio.run(main())
