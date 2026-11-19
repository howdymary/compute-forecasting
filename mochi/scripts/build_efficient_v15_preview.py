"""Download hash-verified public recordings from a completed real campaign."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import modal
from build_terrain_training_preview import public_report

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True)
    a=p.parse_args()
    source=Path(a.source)
    report=json.loads((source/'report.json').read_text())
    assert report['status']=='completed' and report['held_out_opened']
    assert report['study']=='mochi-efficient-v15'
    out=ROOT/'web/desk/efficient-v15'
    out.mkdir(parents=True,exist_ok=True)
    volume=modal.Volume.from_name('mochi-efficient-v15-artifacts')
    cps={c['update']:c for c in report['checkpoints']}
    assert set(cps)=={0,1,4,8,16} and report['optimizer_updates_completed']==16
    selected=report['selected_checkpoint']['update']
    files={}

    def recording(row,update,kind):
        descriptor=row['public_recording']
        name=f'{kind}-{row["seed"]}-{update}.json.gz'
        target=out/name
        if target.exists():
            assert hashlib.sha256(target.read_bytes()).hexdigest()==descriptor['sha256']
        else:
            temporary=target.with_suffix('.download')
            with temporary.open('wb') as stream:
                for chunk in volume.read_file(descriptor['path']):
                    stream.write(chunk)
            assert hashlib.sha256(temporary.read_bytes()).hexdigest()==descriptor['sha256']
            temporary.replace(target)
        raw=gzip.decompress(target.read_bytes())
        assert hashlib.sha256(raw).hexdigest()==descriptor['uncompressed_sha256']
        e=json.loads(raw)
        assert e['scenario']['seed']==row['seed']
        assert e['steps']['attempts']==len(e['step_events'])
        assert e['maximum_applied_base_force']==0
        files[name]={'checkpoint_update':update,'checkpoint_id':cps[update]['checkpoint_id'],
            'cumulative_updates':cps[update]['cumulative_updates'],'seed':row['seed'],
            'complete':row['complete_sequence_success'],'qualified_complete':row['qualified_complete'],
            'failure':row['failure'],'archive':row['archive'],'sha256':descriptor['sha256'],
            'uncompressed_sha256':descriptor['uncompressed_sha256'],
            'steps':e['steps'],'duration':e['duration'],'direction_metrics':row['direction_metrics'],
            'native_smoothness':e['native_smoothness'],
            'task_outcomes':{t:r['success'] for t,r in e['results'].items()}}
        return name

    scenarios=[]
    development={update:json.loads((source/f'checkpoint-{update}.json').read_text()) for update in cps}
    for seed in report['protocol']['development_seeds']:
        versions=[]
        for update in sorted(cps):
            row=next(r for r in development[update] if r['seed']==seed)
            versions.append({'update':update,'file':recording(row,update,'development')})
        scenarios.append({'id':'development-'+str(seed),'label':f'Development scenario · {seed}',
            'partition':'development','versions':versions,'parent_file':versions[0]['file']})
    parents=json.loads((source/'held-out-parent.json').read_text())
    trained={r['seed']:r for r in json.loads((source/'held-out-selected.json').read_text())}
    assert len(parents)==len(trained)==len(report['protocol']['held_out_seeds'])
    for before in parents:
        after=trained[before['seed']]
        bf=recording(before,0,'held-out-parent')
        af=recording(after,selected,'held-out-selected')
        scenarios.append({'id':'held-out-'+str(before['seed']),'label':f'Final test scenario · {before["seed"]}',
            'partition':'held_out','parent_file':bf,'versions':[{'update':selected,'file':af}]})
    manifest={'study':report['study'],'optimizer_updates_completed':report['optimizer_updates_completed'],
        'selected_update':selected,'scope':report['scope'],'scene':json.loads((ROOT/'configs/richdesk-v9.json').read_text()),
        'scenarios':scenarios,'recordings':files,'checkpoints':[cps[k] for k in sorted(cps)],
        'held_out':report['held_out'],'paired_held_out':report['paired_held_out'],
        'improvement_goal_met':report['improvement_goal_met'],'component_results':report['component_results'],
        'test_pairs_available':len(parents),'evaluation_status':'completed','selection_finalized':True,
        'default_scenario':scenarios[0]['id'],'workflow_run':report['run_id'],'source_sha':report['source_sha'],
        'services':report['services']['eligibility'],'campaign_modal_rollouts_completed':report['campaign_modal_rollouts_completed'],
        'display_note':'Actual uninterrupted 25-Hz MuJoCo trajectories, display precision six decimals. Steps are measured from 100-Hz sole poses and contacts. Both sides use the turning fix and identical playback speed. Native gait weights remain fixed.'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    published=public_report(report)
    encoded=json.dumps(published,indent=2)+'\n'
    assert 'tinker://' not in encoded, 'Private optimizer references must stay backend-only'
    (out/'report.json').write_text(encoded)
    print(json.dumps({'recordings':len(files),'scenarios':len(scenarios),'updates':report['optimizer_updates_completed'],
                      'selected':selected,'goal_met':report['improvement_goal_met']}))


if __name__=='__main__':
    main()
