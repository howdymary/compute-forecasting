"""Audit completed V17 evidence. Never runs physics or training."""
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
BASE_SOURCE='795a664f98433e514b5a76e9c2c606ba6136b130'
def read(p):return json.loads(p.read_text())
def close(a,b):assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9),(a,b)
def failure_details(row):
    e=row['episode'];seen=set();contacts=[]
    for contact in e.get('contact_failures',[]):
        key=(contact.get('body'),contact.get('fixture'))
        if key not in seen:
            seen.add(key);contacts.append({k:contact.get(k) for k in ['body','fixture','phase','force_n']})
    return {'seed':row['seed'],'failure':row['failure'],'duration_s':e['duration'],
        'last_station':row['arrivals'][-1]['label'] if row['arrivals'] else None,
        'last_decision_domain':row['model_decisions'][-1]['observation']['domain'] if row['model_decisions'] else None,
        'verified_tasks':[task for task,r in e['results'].items() if r['success']],
        'postit_loaded_contact':bool(e['postit_crossings']),
        'contact_examples':contacts}
def qualification_failures(row,cfg):
    e=row['episode'];m=e['balance_metrics'];s=cfg['smoothness'];n=e['native_smoothness']
    checks={
        'sequence_completed':(row['complete_sequence_success'],True),
        'efficiency_validity':(e['efficiency_validity'],True),
        'roll_rms_deg':(m['roll_rms_deg'],s['roll_rms_degrees_max']),
        'roll_peak_deg':(m['roll_peak_deg'],s['roll_peak_degrees_max']),
        'lateral_rms_m':(m['lateral_rms_m'],s['path_lateral_rms_m_max']),
        'lateral_peak_to_peak_m':(m['lateral_peak_to_peak_m'],s['path_lateral_peak_to_peak_m_max']),
        'duration_s':(e['duration'],s['sequence_time_seconds_max']),
        'loaded_contact_travel_m':(sum(e['foot_slip_estimate_m'].values()),s['loaded_contact_travel_estimate_m_max']),
        'native_acceleration_rms':(n['sampled_acceleration_rms_rad_s2'],s['native_acceleration_rms_max']),
        'native_torque_change_rms':(n['sampled_torque_change_rms_nm'],s['native_torque_change_rms_max'])}
    failures={k:{'observed':v,'limit':limit} for k,(v,limit) in checks.items() if (not v if isinstance(limit,bool) else v is None or v>limit)}
    direction=row['direction_metrics']['forward_facing_fraction']
    if direction is None or direction<.9:failures['forward_facing_fraction']={'observed':direction,'minimum':.9}
    assert bool(failures)==(not row['qualified_complete'])
    return failures

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);a=p.parse_args();folder=Path(a.source)
    from mochi.smooth_v16.objective import summary,paired,valid_branch
    from mochi.smooth_v16.verification import forward_descent_check
    from mochi.control_v8.verification import full_success
    r=read(folder/'report.json');cfg=r['protocol'];SOURCE=r['source_sha'];assert r['status']=='completed' and r['base_source_sha']==BASE_SOURCE
    if r.get('memory_finalization'):
        from mochi.smooth_v17.finalize_memory import result_digest
        recovery=r['memory_finalization']
        assert recovery['additional_optimizer_updates']==recovery['additional_physical_stages']==0
        assert recovery['frozen_result_sha256_before']==recovery['frozen_result_sha256_after']==result_digest(r)
    assert r['optimizer_updates_completed']==16 and [x['update'] for x in r['training_log']]==list(range(1,17))
    assert all(x['optimizer_completed'] and x['forward_backward_completed'] and set(x['domain_loss_metrics'])==set(cfg['training']['domains']) for x in r['training_log'])
    assert all(r['first_optimizer_behavioral_probe'][d]>1e-7 for d in ['walk','recovery'])
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in cfg['frozen_sha256'].items())
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in cfg['continuation_frozen_sha256'].items())
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
    probe=r['first_optimizer_physical_probe']
    before,after=probe['parent'],probe['updated']
    def decision_sequence(row):
        return [(d['observation']['domain'],d['observation'].get('station',d['observation'].get('task')),d['action']) for d in row['model_decisions']]
    probe_variation={'seed':before['seed'],'identical_action_sequence':decision_sequence(before)==decision_sequence(after),
        'identical_initial_physical_hash':before['model_decisions'][0]['initial_physical_state_sha256']==after['model_decisions'][0]['initial_physical_state_sha256'],
        'parent_steps':before['steps']['attempts'],'update_1_steps':after['steps']['attempts'],
        'parent_seconds':before['duration_s'],'update_1_seconds':after['duration_s'],
        'interpretation':'Identical discrete actions do not guarantee identical measured trajectories in these remote executions. The cause of this variation was not isolated. Do not attribute such cost differences to learned action selection.'}
    development_choices=[];development_falls=[]
    parent_development={row['seed']:row for row in read(folder/'checkpoint-0.json')}
    for update in [1,4,8,16]:
        for row in read(folder/f'checkpoint-{update}.json'):
            if row['episode']['fall']:development_falls.append({'update':update,**failure_details(row)})
            parent_row=parent_development[row['seed']]
            old,new=decision_sequence(parent_row),decision_sequence(row)
            common=min(len(old),len(new))
            development_choices.append({'update':update,'seed':row['seed'],
                'parent_decisions':len(old),'checkpoint_decisions':len(new),'common_prefix_length':common,
                'shared_action_prefix_equal':old[:common]==new[:common],
                'whole_action_sequence_equal':old==new,
                'changed_shared_decisions':[{'position':i,'parent':a,'checkpoint':b} for i,(a,b) in enumerate(zip(old,new)) if a!=b],
                'parent_complete':parent_row['complete_sequence_success'],'checkpoint_complete':row['complete_sequence_success'],
                'parent_qualified':parent_row['qualified_complete'],'checkpoint_qualified':row['qualified_complete']})
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
    public=ROOT/'web/desk/smooth-v17';m=read(public/'manifest.json');assert m['source_sha']==SOURCE and m['selected_update']==r['selected_checkpoint']['update']
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
    assert usage['physical_rollouts']==eng['physical_rollouts']+sum(x['physical_rollouts'] for x in receipts)==r['total_physical_attempts_accounted']
    assert r['total_physical_rollouts_completed']==usage['physical_rollouts']-cfg['carried_budget_reconciliation']['unfinished_remote_stages']
    close(usage['simulation_cpu_hours'],eng['simulation_cpu_hours']+sum(x['duration_seconds']*x['cpu']/3600 for x in receipts))
    assert all(0<=usage[k]<=v for k,v in cfg['bounds'].items() if k!='modal_concurrency')
    eligible=r['services']['eligibility'];assert eligible['writers']>1 and eligible['readers']>1 and eligible['cross_agent_reads']>0 and eligible['isolation_passed']
    assert not r['services'].get('pending_ingestions')
    assert r['services']['sources'] and all(x['request_id'] and x['sources'] for x in r['services']['sources'])
    audit={'study':r['study'],'source_sha':SOURCE,'run_id':r['run_id'],'optimizer_updates':16,'domain_backward_calls':96,
        'selected_update':r['selected_checkpoint']['update'],'selected_checkpoint_id':r['selected_checkpoint']['checkpoint_id'],
        'held_out':r['held_out'],'paired_summary':pp,'improvement_goal_met':goal,'usage':usage,'engineering_usage':eng,
        'prior_execution':r.get('prior_execution'),'data_collection_provenance':r.get('data_collection_provenance'),
        'execution_source_sha':r.get('execution_source_sha',SOURCE),'component_branches':len(reached),'valid_component_branches':sum(valid_branch(x) for x in reached),
        'component_reference_seed':r['component_reference_seed'],
        'qualification_failures':{label:[{'seed':row['seed'],'failed_criteria':qualification_failures(row,cfg)} for row in rows] for label,rows in held.items()},
        'static_choice_audit':comparisons,'first_checkpoint_same_action_variation':probe_variation,
        'development_choice_audit':development_choices,
        'post_test_failure_localization':{label:[failure_details(row) for row in rows if not row['complete_sequence_success']] for label,rows in held.items()},
        'later_development_falls':development_falls,
        'public_recordings_verified':len(starts),'selection_preceded_final_tests':True,
        'service_eligibility':eligible,'memory_finalization':r.get('memory_finalization'),
        'limits':['Four final scenarios in one fixed furnished layout. No hardware validation.','Native gait and physical controllers remain fixed; Tinker updates shared LoRA decision weights.','Engineering changes include home-regularized clock IK, the bounded P4 laptop force/horizon and W6 globe-leg commands. These are shared by all new checkpoints, including the parent.',f"Component tests cover the fixed reference trajectory on seed {r['component_reference_seed']}; they do not cover every state reached by the learned policy.",'No causal memory/search ablation. Static-policy equivalence and unchanged decisions limit adaptation claims.']}
    (ROOT/'docs/smooth-v17-assessment.json').write_text(json.dumps(audit,indent=2)+'\n')
    def num(x):return 'Unavailable' if x is None else f'{x:.2f}'
    parent_stats,selected_stats=r['held_out']['parent'],r['held_out']['selected']
    lines=['# Walking and arm-recovery post-training results','',
        f"Tinker completed 16 optimizer updates and 96 domain-gradient calls. The declared joint improvement target was {'met' if goal else 'not met'}.",'',
        f"Development selection chose update {audit['selected_update']}. On four fresh scenarios it completed {selected_stats['complete_successes']}/4 sequences, with {selected_stats['qualified_complete_successes']}/4 within all quality limits. The parent completed {parent_stats['complete_successes']}/4, with {parent_stats['qualified_complete_successes']}/4 qualified. Matched qualified pairs: {pp['n']}.",'',
        'The target required at least 10% fewer measured steps and 15% less recovery joint travel, without lower completion or longer successful time.',
        f"Frozen source: `{SOURCE}`. Run: `{r['run_id']}`.",'',
        '## Final scenarios','',
        '| Policy | Complete | Within all quality limits | Mean steps | Mean recovery travel, rad | Physical seconds |',
        '| --- | --- | --- | --- | --- | --- |']
    for label,stats in r['held_out'].items():
        lines.append(f"| {label} | {stats['complete_successes']}/{stats['n']} | {stats['qualified_complete_successes']}/{stats['n']} | {num(stats['successful_mean_steps'])} | {num(stats['successful_mean_recovery_arm_joint_travel_rad'])} | {num(stats['successful_mean_seconds'])} |")
    lines+=['',
        'Cost means use qualified completions only. Mean recovery travel is per recovery; the replay counter totals all recoveries. Early failures do not count as cheap successful runs.',
        'A comparison with no matched qualified pair has no defined step, time or recovery reduction. Four scenarios in one layout do not establish performance on other desks or hardware.','',
        '## Development checkpoints','',
        'Counts 0, 1, 4, 8 and 16 are additional updates after the verified 121-update parent. Native gait weights stayed fixed. Tinker updated the shared LoRA model that chooses walking, contact and recovery controllers.','',
        '| New updates | Complete | Qualified | Falls | Forbidden contacts |',
        '| --- | --- | --- | --- | --- |']
    for update,c in sorted(cps.items()):
        s=c['development'];lines.append(f"| {update} | {s['complete_successes']}/{s['n']} | {s['qualified_complete_successes']}/{s['n']} | {s['falls']} | {s['invalid_contacts']} |")
    lines+=['',
        'All versions received the same engineered H0 clock reach, P4 laptop action and W6 globe approach. The fixed native gait, route, scene, task verifiers and quality limits were shared. Local controller engineering is recorded separately from model post-training.','',
        '## Recordings and component checks','',
        f"The audit verified {len(starts)} continuous public recordings. The first frame, scenario, task order and playback speed match within each displayed pair. Failed attempts remain available.",
        f"Component diagnostics reached {len(reached)} branches; {audit['valid_component_branches']} passed the frozen branch criteria. Parent and selected policies used identical saved physical states. These branches are separate from the uninterrupted route recordings.",'',
        f"The reference states came from the fixed controller on seed {r['component_reference_seed']}. Their coverage is limited to that reference trajectory. The results motivate collecting and checking the laptop-contact states reached by the learned policy.",'',
        '## Resource accounting','',
        f"Accounted physical attempts and stages: {usage['physical_rollouts']}, including {eng['physical_rollouts']} carried attempts. Confirmed completed attempts and stages: {r['total_physical_rollouts_completed']}.",
        f"Accounted CPU-hours: {usage['simulation_cpu_hours']:.3f}, including conservative bounds for interrupted calls and supervisors. These are budget records, not a billing receipt. Usage stayed within the authorized 224-attempt, 18-hour and 16-update limits."]
    selected_failures=audit['post_test_failure_localization']['selected']
    if len(selected_failures)==4 and all(x['last_decision_domain']=='laptop' for x in selected_failures):
        lines+=['','## Post-test failure localization','',
            'All four selected-model attempts completed the clock and drawer and arrived at the laptop. They then failed during the laptop action: two falls and two forbidden contacts. The contact records identify the right knee against the printer output tray on seed 103001 and the left hip against the laptop on seed 103002.',
            'The later development checkpoints also fell during the laptop action on seed 102001. These observations locate the failures; they do not isolate the physical cause of the falls. Laptop stance, force control and fixture clearance are the next controller issues to investigate. No controller was changed after the final tests were opened.','']
    if r.get('prior_execution'):
        prior=r['prior_execution'];u=prior['budget_usage_or_reserved']
        lines+=['','## Preserved interrupted executions','',f"The preceding execution `{prior['run_id']}` stopped before training with `{prior['error_type']}`. Its original ledger snapshot recorded {u['physical_rollouts']} reserved physical attempts and {u['simulation_cpu_hours']:.3f} reserved CPU-hours. This continuation uses the same pool after the documented reconciliation of reservations against completed receipts and conservative interruption bounds. It did not open a fresh allowance. Those reservations include unfinished work and are not an invoice.",'',f"This continuation reused {len(r['data_collection_provenance']['historical_prefixes'])} historical parent-prefix states and measured new alternatives from their recorded physical snapshots. New collection uses exact snapshots between training stages. The displayed evaluations are uninterrupted physical episodes.",'',"The starting budget includes the interrupted R1 stages, supervisor bounds and local controller probes. Two unfinished calls remain charged at full timeout bounds. No previous resource counter was reset.",'',"Recovery examples can retain an already good parent choice. Only measured physical differences establish an improvement. The table reports mean joint travel per recovery; the viewer counter totals the four recoveries.",'']
    if r.get('earlier_execution'):
        earlier=r['earlier_execution'];u=earlier['budget_usage_or_reserved']
        lines+=['',f"The earlier execution `{earlier['run_id']}` has a separately preserved ledger of {u['physical_rollouts']} reserved attempts and {u['simulation_cpu_hours']:.3f} reserved CPU-hours. It stopped before any optimizer update. Its reservations are not represented as completed work or included in the current pool.",'']
    if probe_variation['identical_action_sequence']:
        lines+=['','## Variation with identical choices','',f"The first-checkpoint probe selected the same action sequence as the parent, but used {probe_variation['update_1_steps']} steps versus {probe_variation['parent_steps']} and {probe_variation['update_1_seconds']:.2f} physical seconds versus {probe_variation['parent_seconds']:.2f}. Their initial physical-state hashes match. The cause of this variation was not isolated. These differences do not establish an effect from learned action selection. Interpret small cost differences and static-policy comparisons with this limitation.",'']
    first=[x for x in development_choices if x['update']==1]
    unchanged=[x for x in first if x['shared_action_prefix_equal']]
    changed_outcomes=[x for x in unchanged if x['parent_complete']!=x['checkpoint_complete']]
    lines+=['',f"Across the three development scenarios, update 1 matched the parent's shared action prefix in {len(unchanged)}/3 cases. Of those cases, {len(changed_outcomes)} had a different completion outcome. A changed outcome before any changed selected action does not establish a benefit from learned action selection. Per-checkpoint decision comparisons are retained in the JSON audit.",'']
    lines+=['','## Limitations','']+['- '+x for x in audit['limits']]+['',
        'The companion JSON retains per-case qualification failures, static-policy choices, confidence intervals, initial-state checks and provider activity. Search and shared memory were used in the workflow; this study did not isolate their causal effect on performance.','']
    text='\n'.join(lines)
    (ROOT/'docs/smooth-v17-assessment.md').write_text(text)
    print(json.dumps({'updates':16,'goal_met':goal,'selected_update':audit['selected_update'],'recordings':len(starts),'rollouts':usage['physical_rollouts']}))
if __name__=='__main__':main()
