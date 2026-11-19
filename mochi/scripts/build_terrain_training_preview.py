"""Export actual completed checkpoints and paired tests, excluding private paths."""
import argparse,gzip,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'web/desk/terrain-training'

def rounded(x):
    if isinstance(x,float):return round(x,6)
    if isinstance(x,list):return [rounded(v) for v in x]
    if isinstance(x,dict):return {k:rounded(v) for k,v in x.items()}
    return x

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);a=p.parse_args()
    source=Path(a.source);report=json.loads((source/'report.json').read_text())
    assert report['status']=='completed' and report['held_out_opened'],'Do not publish an unfinished test as a completed campaign'
    OUT.mkdir(parents=True,exist_ok=True)
    cps={c['update']:c for c in report['checkpoints']};selected=report['selected_checkpoint']['update'];files={}
    def recording(row,update,kind):
        seed=row['seed'];name=f'{kind}-{seed}-{update}.json.gz'
        if name in files:return name
        e=row['episode'];keep=['scenario','scene','events','results','fall','invalid_contact','duration',
            'maximum_applied_base_force','balance_metrics','foot_slip_estimate_m','final_object_states',
            'final_object_speeds','trajectory','recoveries','decisions']
        clip={k:e[k] for k in keep if k in e}
        clip['balance_measurements']=[{k:v for k,v in m.items() if k in ['t','phase','gait_phase','roll_rad','loads_n','lateral_m']} for m in e['balance_measurements']]
        (OUT/name).write_bytes(gzip.compress(json.dumps(rounded(clip),separators=(',',':')).encode(),compresslevel=9))
        files[name]={'checkpoint_update':update,'checkpoint_id':cps[update]['checkpoint_id'],
                     'cumulative_updates':cps[update]['cumulative_updates'],'seed':seed,
                     'complete':row['complete_sequence_success'],'failure':row['failure'],'archive':row.get('archive'),
                     'task_outcomes':{t:r['success'] for t,r in e['results'].items()},'duration':e['duration']}
        return name
    scenarios=[]
    devseed=report['protocol']['development_seeds'][0]
    versions=[]
    for update in sorted(cps):
        rows=json.loads((source/f'checkpoint-{update}.json').read_text());row=next(r for r in rows if r['seed']==devseed)
        versions.append({'update':update,'file':recording(row,update,'development')})
    scenarios.append({'id':'development-'+str(devseed),'label':f'Checkpoint selection scenario · {devseed}',
                      'partition':'development','versions':versions,'parent_file':versions[0]['file']})
    parents=json.loads((source/'held-out-parent.json').read_text());trained=json.loads((source/'held-out-selected.json').read_text())
    for before,after in zip(parents,trained):
        assert before['seed']==after['seed']
        bf=recording(before,0,'held-out');af=recording(after,selected,'held-out')
        scenarios.append({'id':'held-out-'+str(before['seed']),'label':f'Final unseen scenario · {before["seed"]}',
                          'partition':'held_out','parent_file':bf,'versions':[{'update':selected,'file':af}]})
    manifest={'study':report['study'],'optimizer_updates_completed':report['optimizer_updates_completed'],
              'selected_update':selected,'scope':report['scope'],'scene':json.loads((ROOT/'configs/richdesk-v9.json').read_text()),
              'scenarios':scenarios,'recordings':files,'checkpoints':report['checkpoints'],'held_out':report['held_out'],
              'isolated':report['isolated'],'default_scenario':'held-out-'+str(report['protocol']['held_out_seeds'][0]),
              'workflow_run':report['run_id'],'source_sha':report['source_sha'],
              'services':report['services']['eligibility'],
              'campaign_modal_rollouts_completed':report.get('campaign_modal_rollouts_completed'),
              'memory_review_pending':report.get('memory_review_pending'),
              'final_memory_review_pending':report.get('final_memory_review_pending'),
              'display_note':'Complete measured 25 Hz body trajectories with six-decimal display quantization. No physical instability is filtered. Full numerical originals are archived on Modal.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Only the explicitly public report is copied. Never export checkpoint-paths.json.
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'scenarios':len(scenarios),'recordings':len(files),'new_updates':report['optimizer_updates_completed'],
                      'selected_update':selected,'compressed_mb':sum(p.stat().st_size for p in OUT.glob('*.gz'))/1e6}))

if __name__=='__main__':main()
