"""Audit existing completed V16 evidence. Never runs physics or training."""
import argparse
from collections import defaultdict
from copy import deepcopy
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

ROOT=Path(__file__).resolve().parents[1]
SOURCE='795a664f98433e514b5a76e9c2c606ba6136b130'
def read(p):return json.loads(p.read_text())
def close(a,b):assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9),(a,b)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);a=p.parse_args();folder=Path(a.source)
    from mochi.smooth_v16.objective import summary,paired,valid_branch
    from mochi.smooth_v16.verification import forward_descent_check
    from mochi.control_v8.verification import full_success
    r=read(folder/'report.json');cfg=r['protocol'];assert r['status']=='completed' and r['source_sha']==SOURCE
    assert r['optimizer_updates_completed']==16 and [x['update'] for x in r['training_log']]==list(range(1,17))
    assert all(x['optimizer_completed'] and x['forward_backward_completed'] and set(x['domain_loss_metrics'])==set(cfg['training']['domains']) for x in r['training_log'])
    assert all(r['first_optimizer_behavioral_probe'][d]>1e-7 for d in ['walk','recovery'])
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in cfg['frozen_sha256'].items())
    cps={c['update']:c for c in r['checkpoints']};assert set(cps)=={0,1,4,8,16}
    assert all(c['cumulative_updates']==121+c['update'] and len(c['checkpoint_id'])==64 for c in cps.values())
    selection=read(folder/'selection-freeze.json');assert not selection['held_out_opened'] and not selection.get('held_out')
    assert selection['selected_checkpoint']['checkpoint_id']==r['selected_checkpoint']['checkpoint_id']
    partitions=[set(cfg[k]) for k in ['training_seeds','development_seeds','held_out_seeds']]
    assert not any(a&b for i,a in enumerate(partitions) for b in partitions[i+1:])
    held={label:read(folder/('held-out-'+label+'.json')) for label in ['parent','selected','fixed','static']}
    for label,rows in held.items():
        assert len(rows)==4 and {x['seed'] for x in rows}==partitions[2]
        recomputed=summary(deepcopy(rows),cfg)
        for key in ['n','complete_successes','qualified_complete_successes','falls','invalid_contacts']:
            assert recomputed[key]==r['held_out'][label][key]
        for key in ['successful_mean_steps','successful_mean_seconds','successful_mean_recovery_arm_joint_travel_rad','successful_mean_intertask_arm_joint_travel_rad']:
            if recomputed[key] is not None:close(recomputed[key],r['held_out'][label][key])
        for row in rows:
            e=row['episode'];assert row['qualified_complete'] is False or row['complete_sequence_success']
            if row['complete_sequence_success']:
                assert full_success(e) and not e['fall'] and not e['invalid_contact'] and e['maximum_applied_base_force']==0
                assert e['postit_crossings'] and forward_descent_check(e['step_events'],e['book_motion_samples'])['verified']
                assert e['scene']['version']=='richdesk-v16-open-hinge'
                assert len(e['recoveries'])==4 and all(x['success'] for x in e['recoveries'])
                assert all(e['results'][task]['contacts']>0 and e['results'][task]['non_hand_contact_steps']==0 and e['results'][task]['max_force_n']<.8 for task in ['alarm','drawer','laptop','globe'])
                turn=next(x for x in row['arrivals'] if x['label']=='book-top-turnaround')
                assert turn['success'] and turn['heading_error_degrees']<=10 and turn['book_top']['instant_valid']
    pp=paired(held['parent'],held['selected']);assert pp['n']==r['paired_held_out']['n']
    for key in ['mean_step_reduction_fraction','mean_time_reduction_fraction','mean_recovery_arm_travel_reduction_fraction','mean_intertask_arm_travel_reduction_fraction']:
        if pp[key] is not None:close(pp[key],r['paired_held_out'][key])
    goal=bool(r['held_out']['selected']['qualified_complete_successes']==4 and pp['n']>=2 and pp['mean_step_reduction_fraction']>=.10 and pp['mean_recovery_arm_travel_reduction_fraction']>=.15 and pp['mean_time_reduction_fraction']>=0 and r['held_out']['selected']['falls']<=r['held_out']['parent']['falls'] and r['held_out']['selected']['invalid_contacts']<=r['held_out']['parent']['invalid_contacts'])
    assert goal==r['improvement_goal_met']
    comparisons=[]
    static={x['seed']:x for x in held['static']}
    for row in held['selected']:
        def actions(x):return {d['observation']['domain']+':'+d['observation'].get('station',d['observation'].get('task',d['observation']['domain'])):d['action'] for d in x['model_decisions']}
        left,right=actions(row),actions(static[row['seed']]);common=left.keys()&right.keys()
        comparisons.append({'seed':row['seed'],'selected_decisions':len(left),'static_decisions':len(right),'common_decisions':len(common),'matching_decisions':sum(left[k]==right[k] for k in common),'differences':{k:{'selected':left[k],'static':right[k]} for k in common if left[k]!=right[k]}})
    components=defaultdict(list)
    for batch in r['component_results']:
        for row in batch['results']:components[row['domain']+':'+row['task']].append(row)
    reached=[]
    for rows in components.values():
        rows=[x for x in rows if x.get('status')!='reference_not_reached']
        if rows:
            assert len(rows)==2 and {x['model'] for x in rows}=={'parent','selected'}
            assert len({x['initial_state_sha256'] for x in rows})==1
            reached+=rows
    public=ROOT/'web/desk/smooth-v16';m=read(public/'manifest.json');assert m['source_sha']==SOURCE and m['selected_update']==r['selected_checkpoint']['update']
    starts={}
    for name,meta in m['recordings'].items():
        data=(public/name).read_bytes();assert hashlib.sha256(data).hexdigest()==meta['sha256']
        raw=gzip.decompress(data);assert hashlib.sha256(raw).hexdigest()==meta['uncompressed_sha256'];e=json.loads(raw)
        f=e['trajectory']['frames'];assert f[0]['t']==0 and 0<=e['duration']-f[-1]['t']<=.05
        assert all(0<b['t']-a['t']<=.05 for a,b in zip(f,f[1:]));assert e['maximum_applied_base_force']==0
        assert len(e['step_events'])==e['steps']['attempts']==meta['steps']['attempts'];starts[name]=f[0]
    for scene in m['scenarios']:
        for version in scene['versions']:assert starts[scene['parent_file']]==starts[version['file']]
    usage=r['budget_usage_or_reserved'];eng=cfg['engineering_usage'];receipts=[x['receipt'] for x in r['physics_receipts']]
    assert usage['physical_rollouts']==eng['physical_rollouts']+sum(x['physical_rollouts'] for x in receipts)==r['total_physical_rollouts_completed']
    close(usage['simulation_cpu_hours'],eng['simulation_cpu_hours']+sum(x['duration_seconds']*x['cpu']/3600 for x in receipts))
    assert all(0<=usage[k]<=v for k,v in cfg['bounds'].items() if k!='modal_concurrency')
    eligible=r['services']['eligibility'];assert eligible['writers']>1 and eligible['readers']>1 and eligible['cross_agent_reads']>0 and eligible['isolation_passed']
    assert not r['services'].get('pending_ingestions')
    assert r['services']['sources'] and all(x['request_id'] and x['sources'] for x in r['services']['sources'])
    audit={'study':r['study'],'source_sha':SOURCE,'run_id':r['run_id'],'optimizer_updates':16,'domain_backward_calls':96,
        'selected_update':r['selected_checkpoint']['update'],'selected_checkpoint_id':r['selected_checkpoint']['checkpoint_id'],
        'held_out':r['held_out'],'paired_summary':pp,'improvement_goal_met':goal,'usage':usage,'engineering_usage':eng,
        'component_branches':len(reached),'valid_component_branches':sum(valid_branch(x) for x in reached),
        'static_choice_audit':comparisons,'public_recordings_verified':len(starts),'selection_preceded_final_tests':True,
        'service_eligibility':eligible,'limits':['Four final scenarios in one fixed furnished layout. No hardware validation.','Native gait and physical controllers remain fixed; Tinker updates shared LoRA decision weights.','Engineering changes include the forward descent, route shortcut, paper-top support rule, hinge friction and laptop release. These are shared by all new checkpoints.','No causal memory/search ablation. Static-policy equivalence and unchanged decisions limit adaptation claims.']}
    (ROOT/'docs/smooth-v16-assessment.json').write_text(json.dumps(audit,indent=2)+'\n')
    def num(x):return 'Unavailable' if x is None else f'{x:.2f}'
    lines=['# Walking and arm-recovery post-training results','',f"Frozen source: `{SOURCE}`. Run: `{r['run_id']}`.",'','Tinker completed16 optimizer updates with96 domain-gradient calls. Native gait weights stayed fixed. Counts0,1,4,8 and16 are additional updates after the verified121-update parent.','','| Policy | Qualified | Mean steps | Mean recovery travel, rad | Physical seconds |','| --- | --- | --- | --- | --- |']
    for label,stats in r['held_out'].items():lines.append(f"| {label} | {stats['qualified_complete_successes']}/{stats['n']} | {num(stats['successful_mean_steps'])} | {num(stats['successful_mean_recovery_arm_joint_travel_rad'])} | {num(stats['successful_mean_seconds'])} |")
    lines+=['',f"The selected checkpoint is update{audit['selected_update']}. The declared joint target was {'met' if goal else 'not met'} on the final cohort. Matched qualified pairs: {pp['n']}.",'',f"Total physical rollouts: {usage['physical_rollouts']}, including{eng['physical_rollouts']} engineering attempts. Simulation worker-hours: {usage['simulation_cpu_hours']:.3f}. All are inside the authorized224-rollout,18-hour,16-update limits.",'',f"Verified{len(starts)} continuous public recordings. Component diagnostics reached{len(reached)} branches; {audit['valid_component_branches']} passed the frozen branch criteria. Diagnostics are separate from uninterrupted routes.",'','## Limitations','']+['- '+x for x in audit['limits']]+['','Numerical details, static-policy choices, confidence intervals and provider activity are retained in the companion JSON and campaign report. The first frame, scenario, task order and playback speed match within each displayed pair.','']
    text='\n'.join(lines)
    for old,new in [('completed16','completed 16'),('with96','with 96'),('Counts0','Counts 0'),('and16','and 16'),('verified121','verified 121'),('update'+str(audit['selected_update']),'update '+str(audit['selected_update'])),('including'+str(eng['physical_rollouts']),'including '+str(eng['physical_rollouts'])),('authorized224','authorized 224'),(',18-hour',', 18-hour'),(',16-update',', 16-update'),('Verified'+str(len(starts)),'Verified '+str(len(starts))),('reached'+str(len(reached)),'reached '+str(len(reached)))]:text=text.replace(old,new)
    (ROOT/'docs/smooth-v16-assessment.md').write_text(text)
    print(json.dumps({'updates':16,'goal_met':goal,'selected_update':audit['selected_update'],'recordings':len(starts),'rollouts':usage['physical_rollouts']}))
if __name__=='__main__':main()
