"""Download hash-verified public recordings from a completed real campaign."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import modal
from build_terrain_training_preview import public_report
from foot_clearance_evidence import after_descent_clearance

ROOT=Path(__file__).resolve().parents[1]


def public_evidence(value,campaign):
    """Keep the verified Mochi handoff and omit unrelated recall metadata."""
    if isinstance(value,list):
        return [public_evidence(item,campaign) for item in value]
    if isinstance(value,dict):
        result={key:public_evidence(item,campaign) for key,item in value.items() if key!='returned_source_ids'}
        if 'returned_source_ids' in value:
            ids=value['returned_source_ids']
            result['returned_source_ids']=[item for item in ids if item.startswith(campaign)]
            result['unrelated_source_ids_omitted']=sum(not item.startswith(campaign) for item in ids)
            result['all_returned_source_ids_sha256']=hashlib.sha256(json.dumps(ids).encode()).hexdigest()
        return result
    return value


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True)
    p.add_argument('--execution-workflow-run',type=int,default=44800327838)
    p.add_argument('--development-preview',action='store_true',help='Inspect completed development recordings while the final cohort is still pending; never marks the campaign complete.')
    a=p.parse_args()
    source=Path(a.source)
    report=json.loads((source/'report.json').read_text())
    if a.development_preview:
        assert report['status']=='running' and not report.get('held_out'), 'Use the completed export for completed final tests'
    else:
        assert report['status']=='completed' and report['held_out_opened']
    assert report['study']=='mochi-contact-v18'
    out=ROOT/'web/desk/contact-v18'
    if a.development_preview and (out/'manifest.json').exists():
        assert json.loads((out/'manifest.json').read_text()).get('evaluation_status')!='completed', 'Preserve the completed public evidence'
    out.mkdir(parents=True,exist_ok=True)
    volumes={}
    cps={c['update']:c for c in report['checkpoints']}
    assert set(cps)=={0,1,4,8,16} and report['optimizer_updates_completed']==16
    evaluated={u:c for u,c in cps.items() if c['development'] is not None}
    assert set(evaluated)==set(report['protocol']['training'].get('evaluation_checkpoints',cps))
    selected=report['selected_checkpoint']['update']
    files={}

    def recording(row,update,kind):
        descriptor=row['public_recording']
        volume_name=descriptor['volume']
        if volume_name not in volumes:
            volumes[volume_name]=modal.Volume.from_name(volume_name)
        volume=volumes[volume_name]
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
            'native_smoothness':e['native_smoothness'],'flat_foot_clearance':e.get('flat_foot_clearance'),
            'after_descent_clearance':after_descent_clearance(e),
            'recovery_arm_joint_travel_rad':sum(x['arm_joint_travel_rad'] for x in e['recoveries']),
            'intertask_arm_joint_travel_rad':sum(e['intertask_arm_joint_travel_rad'].values()),
            'postit_loaded_contacts':len(e['postit_crossings']),
            'book_turnaround_verified':any(a['label']=='book-top-turnaround' and a['success'] and a.get('book_top',{}).get('instant_valid') for a in row['arrivals']),
            'forward_descent_verified':any(a['label']=='book-forward-descent' and a['success'] and a.get('forward_verification',{}).get('verified') for a in row['arrivals']),
            'task_outcomes':{t:r['success'] for t,r in e['results'].items()}}
        return name

    scenarios=[]
    development={update:json.loads((source/f'checkpoint-{update}.json').read_text()) for update in evaluated}
    # The coordinator saves raw rows before computing the frozen qualification
    # flags. Derive presentation flags using exactly those unchanged criteria.
    from mochi.smooth_v16.objective import qualify
    for rows in development.values():
        for row in rows:
            qualify(row,report['protocol'])
    for seed in report['protocol']['development_seeds']:
        versions=[]
        for update in sorted(evaluated):
            row=next(r for r in development[update] if r['seed']==seed)
            versions.append({'update':update,'file':recording(row,update,'development')})
        scenarios.append({'id':'development-'+str(seed),'label':f'Development scenario · {seed}',
            'partition':'development','versions':versions,'parent_file':versions[0]['file']})
    parents=[] if a.development_preview else json.loads((source/'held-out-parent.json').read_text())
    trained={} if a.development_preview else {r['seed']:r for r in json.loads((source/'held-out-selected.json').read_text())}
    if not a.development_preview:
        assert len(parents)==len(trained)==len(report['protocol']['held_out_seeds'])
    for before in parents:
        after=trained[before['seed']]
        bf=recording(before,0,'held-out-parent')
        af=recording(after,selected,'held-out-selected')
        scenarios.append({'id':'held-out-'+str(before['seed']),'label':f'Final test scenario · {before["seed"]}',
            'partition':'held_out','parent_file':bf,'versions':[{'update':selected,'file':af}]})
    manifest={'study':report['study'],'optimizer_updates_completed':report['optimizer_updates_completed'],
        'execution_source_sha':report.get('execution_source_sha',report['source_sha']),
        'prior_execution':report.get('prior_execution'),'data_collection_provenance':report.get('data_collection_provenance'),
        'runtime_amendment':report.get('runtime_amendment'),'carried_baseline':report.get('carried_baseline'),
        'runtime_reservation_reconciliation':report.get('runtime_reservation_reconciliation'),
        'interrupted_physical_attempts_accounted':report.get('interrupted_physical_attempts_accounted',0),
        'physical_evaluation_updates':sorted(evaluated),'saved_checkpoint_updates':sorted(cps),
        'selected_update':selected,'scope':report['scope'],'scene':json.loads((ROOT/'configs/richdesk-v9.json').read_text()),
        'scene_revision':report['protocol']['scene_revision'],'scenarios':scenarios,'recordings':files,'checkpoints':[cps[k] for k in sorted(cps)],
        'held_out':report.get('held_out'),'paired_held_out':report.get('paired_held_out'),
        'improvement_goal_met':report.get('improvement_goal_met'),'component_results':report.get('component_results'),
        'test_pairs_available':len(parents),'evaluation_status':'development_preview' if a.development_preview else 'completed','selection_finalized':True,
        'default_scenario':next((s['id'] for s in scenarios if s['partition']=='held_out'),scenarios[0]['id']),'workflow_run':report['run_id'],
        'campaign_id':report['run_id'],'execution_workflow_run':a.execution_workflow_run,'source_sha':report['source_sha'],
        'services':report['services']['eligibility'],'campaign_modal_rollouts_completed':report['campaign_modal_rollouts_completed'],
        'total_physical_attempts_accounted':report['total_physical_attempts_accounted'],
        'total_physical_rollouts_completed':report['total_physical_rollouts_completed'],'engineering_usage':report['engineering_usage'],
        'display_note':'Actual uninterrupted MuJoCo trajectories, target100-Hz flat transit/25-Hz elsewhere, using real timestamps; display precision six decimals. Steps are measured from 100-Hz sole poses and contacts. Every checkpoint uses the same frozen contact-repair library and playback speed. Native gait weights remain fixed. Training changes controller-selection weights.'}
    manifest['scene']['version']=report['protocol']['scene_revision']['version']
    manifest['scene']['physics']={'laptop_hinge_friction_increment_nm':.015}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    published=public_evidence(public_report(report),report['run_id'])
    published['execution_workflow_run']=a.execution_workflow_run
    encoded=json.dumps(published,indent=2)+'\n'
    assert 'tinker://' not in encoded, 'Private optimizer references must stay backend-only'
    (out/'report.json').write_text(encoded)
    print(json.dumps({'recordings':len(files),'scenarios':len(scenarios),'updates':report['optimizer_updates_completed'],
                      'selected':selected,'evaluation_status':manifest['evaluation_status'],'goal_met':report.get('improvement_goal_met')}))


if __name__=='__main__':
    main()
