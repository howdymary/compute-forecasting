"""Frozen validity and step-first ranking for labels and checkpoints."""
import math
import numpy as np
from ..terrain_v13.objective import static_from_training


def branch_metrics(rows):
    from ..balanced.verification import metrics
    return {**metrics(rows),'roll_peak_deg':max((math.degrees(abs(r['roll_rad'])) for r in rows),default=float('inf')),
            'sampled_joint_speed_rms_rad_s':float(np.sqrt(np.mean([v*v for r in rows for v in r['qd']]))) if rows else None}


def valid_branch(row):
    m=row['metrics']
    native=row['native_smoothness']
    return bool(row['success'] and not row['fall'] and not row['invalid_contact']
        and m['roll_rms_deg']<=2. and m['roll_peak_deg']<=12.
        and row['longest_unsupported_seconds']<=.06
        and (native['sampled_acceleration_rms_rad_s2'] is None or native['sampled_acceleration_rms_rad_s2']<=161.4)
        and (native['sampled_torque_change_rms_nm'] is None or native['sampled_torque_change_rms_nm']<=.00371))


def branch_rank(domain,row):
    if domain=='walk':
        return (row['steps']['attempts'],round(row['duration_s'],1))
    recovery=row['result'] if domain=='recovery' else row['coupled_recovery']
    return (row['duration_s']+.25*recovery['arm_joint_travel_rad'],row['result'].get('max_force_n',0.))


def rank(summary,rows):
    valid=[r for r in rows if r['qualified_complete']]
    return (summary['qualified_complete_successes'],-summary['falls'],-summary['invalid_contacts'],
        sum(summary['task_successes'].values()),
        -sum(r['episode']['steps']['attempts'] for r in valid)/len(valid) if valid else -1e12,
        -sum(r['episode']['duration'] for r in valid)/len(valid) if valid else -1e12)


def meaningful_corrections(teachers):
    counts={}
    for teacher in teachers:
        for trial in teacher['trials']:
            by_action={r['action']:r for r in trial['outcomes']}
            before=by_action[trial['student_preference']]
            valid=[r for r in trial['outcomes'] if valid_branch(r)]
            if not valid:
                continue
            after=min(valid,key=lambda r:branch_rank(trial['domain'],r))
            substantial=not valid_branch(before)
            if valid_branch(before):
                if trial['domain']=='walk':
                    substantial=before['steps']['attempts']>after['steps']['attempts']
                else:
                    substantial=branch_rank(trial['domain'],before)[0]-branch_rank(trial['domain'],after)[0]>=.1
            if substantial:
                counts[trial['domain']]=counts.get(trial['domain'],0)+1
    return counts


def qualify(row,cfg):
    e=row['episode'];m=e['balance_metrics'];s=cfg['smoothness']
    d=row['direction_metrics']['forward_facing_fraction']
    native=e['native_smoothness']
    row['qualified_complete']=bool(row['complete_sequence_success'] and e['efficiency_validity']
        and m['roll_rms_deg']<=s['roll_rms_degrees_max'] and m['roll_peak_deg']<=s['roll_peak_degrees_max']
        and m['lateral_rms_m']<=s['path_lateral_rms_m_max']
        and m['lateral_peak_to_peak_m']<=s['path_lateral_peak_to_peak_m_max']
        and e['duration']<=s['sequence_time_seconds_max']
        and sum(e['foot_slip_estimate_m'].values())<=s['loaded_contact_travel_estimate_m_max']
        and native['sampled_acceleration_rms_rad_s2']<=s['native_acceleration_rms_max']
        and native['sampled_torque_change_rms_nm']<=s['native_torque_change_rms_max']
        and d is not None and d>=.9)
    return row


def summary(rows,cfg):
    from ..terrain_v12.train import summary as prior_summary
    for row in rows:
        qualify(row,cfg)
    q=[r for r in rows if r['qualified_complete']]
    return {**prior_summary(rows,cfg),'qualified_complete_successes':len(q),
        'successful_mean_steps':sum(r['episode']['steps']['attempts'] for r in q)/len(q) if q else None,
        'successful_mean_seconds':sum(r['episode']['duration'] for r in q)/len(q) if q else None,
        'successful_mean_forward_facing_fraction':sum(r['direction_metrics']['forward_facing_fraction'] for r in q)/len(q) if q else None}


def paired(before,after):
    by_seed={r['seed']:r for r in before}
    pairs=[(by_seed[r['seed']],r) for r in after if by_seed[r['seed']]['qualified_complete'] and r['qualified_complete']]
    result={'n':len(pairs),'scenario_step_reductions':[],'mean_step_reduction_fraction':None,'mean_time_reduction_fraction':None,
        'mean_step_reduction_bootstrap_95':None,'mean_time_reduction_bootstrap_95':None,
        'uncertainty_scope':'Deterministic paired resampling of this small fixed-layout cohort; not a guarantee for other layouts or hardware.'}
    if pairs:
        steps=[1-b['episode']['steps']['attempts']/a['episode']['steps']['attempts'] for a,b in pairs]
        times=[1-b['episode']['duration']/a['episode']['duration'] for a,b in pairs]
        result.update(mean_step_reduction_fraction=sum(steps)/len(steps),mean_time_reduction_fraction=sum(times)/len(times),
            scenario_step_reductions=[{'seed':a['seed'],'before':a['episode']['steps']['attempts'],
                'after':b['episode']['steps']['attempts'],'reduction_fraction':delta} for (a,b),delta in zip(pairs,steps)])
        if len(pairs)>=2:
            indices=np.random.default_rng(151120).integers(len(pairs),size=(20000,len(pairs)))
            result['mean_step_reduction_bootstrap_95']=np.quantile(np.asarray(steps)[indices].mean(axis=1),[.025,.975]).tolist()
            result['mean_time_reduction_bootstrap_95']=np.quantile(np.asarray(times)[indices].mean(axis=1),[.025,.975]).tolist()
    return result
