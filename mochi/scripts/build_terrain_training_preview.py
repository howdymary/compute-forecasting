"""Export actual completed checkpoints and paired tests, excluding private paths."""
import argparse,gzip,json
from statistics import mean
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'web/desk/terrain-training'

def rounded(x):
    if isinstance(x,float):return round(x,6)
    if isinstance(x,list):return [rounded(v) for v in x]
    if isinstance(x,dict):return {k:rounded(v) for k,v in x.items()}
    return x

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--development-preview',action='store_true');a=p.parse_args()
    source=Path(a.source);report=json.loads((source/'report.json').read_text())
    if a.development_preview:
        assert report.get('held_out') is None,'Use completed evaluation results when final test results exist'
        if (OUT/'manifest.json').exists():
            assert json.loads((OUT/'manifest.json').read_text()).get('evaluation_status')!='completed','Do not replace completed evidence with a preview'
    else:assert report['status']=='completed' and report['held_out_opened'],'Do not publish an unfinished test as a completed campaign'
    OUT.mkdir(parents=True,exist_ok=True)
    cps={c['update']:c for c in report['checkpoints'] if c['development']}
    assert 0 in cps and len(cps)>=2
    def rank(c):
        x=c['development'];return (x['complete_successes'],-x['falls'],-x['invalid_contacts'],sum(x['task_successes'].values()),x['smooth_complete_successes'],x['recovery_successes'],-x['mean_roll_rms_deg'],-(x['successful_recovery_mean_joint_travel_rad'] or 0),-x['mean_duration_s'])
    selected=report['selected_checkpoint']['update'] if report.get('selected_checkpoint') else max(cps.values(),key=rank)['update']
    files={}
    def recording(row,update,kind):
        seed=row['seed'];name=f'{kind}-{seed}-{update}.json.gz'
        if name in files:return name
        e=row['episode'];keep=['scenario','scene','events','results','fall','invalid_contact','duration',
            'maximum_applied_base_force','balance_metrics','foot_slip_estimate_m','final_object_states',
            'final_object_speeds','trajectory','recoveries','decisions','executed_root_distance_m']
        clip={k:e[k] for k in keep if k in e}
        clip['balance_measurements']=[{k:v for k,v in m.items() if k in ['t','phase','gait_phase','roll_rad','loads_n','lateral_m']} for m in e['balance_measurements']]
        (OUT/name).write_bytes(gzip.compress(json.dumps(rounded(clip),separators=(',',':')).encode(),compresslevel=9,mtime=0))
        files[name]={'checkpoint_update':update,'checkpoint_id':cps[update]['checkpoint_id'],
                     'cumulative_updates':cps[update]['cumulative_updates'],'seed':seed,
                     'complete':row['complete_sequence_success'],'failure':row['failure'],'archive':row.get('archive'),
                     'task_outcomes':{t:r['success'] for t,r in e['results'].items()},'duration':e['duration'],
                     'executed_root_distance_m':e.get('executed_root_distance_m')}
        return name
    scenarios=[]
    development_rows={update:json.loads((source/f'checkpoint-{update}.json').read_text()) for update in cps}
    for devseed in report['protocol']['development_seeds']:
        versions=[]
        for update in sorted(cps):
            row=next(r for r in development_rows[update] if r['seed']==devseed)
            versions.append({'update':update,'file':recording(row,update,'development')})
        scenarios.append({'id':'development-'+str(devseed),'label':f'Checkpoint selection scenario · {devseed}',
                          'partition':'development','versions':versions,'parent_file':versions[0]['file']})
    if not a.development_preview:
        parents=json.loads((source/'held-out-parent.json').read_text());trained=json.loads((source/'held-out-selected.json').read_text())
        for label in ['parent','selected','fixed']:
            rows=json.loads((source/('held-out-'+label+'.json')).read_text())
            complete=[r['episode'] for r in rows if r['complete_sequence_success']]
            distances=[e['executed_root_distance_m'] for e in complete if e.get('executed_root_distance_m') is not None]
            report['held_out'][label]['successful_completion_time_mean_s']=mean(e['duration'] for e in complete) if complete else None
            report['held_out'][label]['successful_executed_distance_mean_m']=mean(distances) if distances else None
        paired=[{'seed':a['seed'],'time_change_s':b['episode']['duration']-a['episode']['duration'],
                 'distance_change_m':b['episode']['executed_root_distance_m']-a['episode']['executed_root_distance_m']}
                for a,b in zip(parents,trained) if a['complete_sequence_success'] and b['complete_sequence_success']]
        report['paired_successful_completion_differences']={'n':len(paired),'cases':paired,
            'scope':'Only paired cases where both checkpoints complete; do not interpret early failed attempts as faster completions.'}
        for before,after in zip(parents,trained):
            assert before['seed']==after['seed']
            bf=recording(before,0,'held-out-parent');af=recording(after,selected,'held-out-selected')
            scenarios.append({'id':'held-out-'+str(before['seed']),'label':f'Final unseen scenario · {before["seed"]}',
                              'partition':'held_out','parent_file':bf,'versions':[{'update':selected,'file':af}]})
    manifest={'study':report['study'],'optimizer_updates_completed':report['optimizer_updates_completed'],
              'selected_update':selected,'scope':report['scope'],'scene':json.loads((ROOT/'configs/richdesk-v9.json').read_text()),
              'scenarios':scenarios,'recordings':files,'checkpoints':[cps[k] for k in sorted(cps)],'held_out':report.get('held_out'),
              'isolated':report.get('isolated'),
              'evaluation_status':'development_preview' if a.development_preview else 'completed',
              'selection_finalized':bool(report.get('selected_checkpoint')),'default_scenario':'development-'+str(report['protocol']['development_seeds'][0]),
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
                      'selected_update':selected,'evaluation_status':manifest['evaluation_status'],'compressed_mb':sum(p.stat().st_size for p in OUT.glob('*.gz'))/1e6}))

if __name__=='__main__':main()
