"""Unchanged physical safety, with explicit walking-clearance preference."""
from ..smooth_v16.objective import valid_branch,paired,branch_metrics
from ..smooth_v16.objective import branch_rank as old_rank,summary as old_summary
from ..smooth_v16_resume.objective import select_checkpoint as old_select

def select_checkpoint(checkpoints,development,cfg):
    # The user added visible foot lift before this campaign started. Keep
    # completion/safety first, then prefer the measured clearance target.
    best_complete=max(c['development']['qualified_complete_successes'] for c in checkpoints)
    candidates=[c for c in checkpoints if c['development']['qualified_complete_successes']==best_complete]
    best_clear=max(c['development']['clear_stepping_successes'] for c in candidates)
    candidates=[c for c in candidates if c['development']['clear_stepping_successes']==best_clear]
    if best_complete==0:return old_select(checkpoints,development,cfg)
    base=checkpoints[0]['development']
    def cost(c):
        s=c['development']
        return (s['falls'],s['invalid_contacts'],
          s['successful_mean_steps']/(base['successful_mean_steps'] or 500.)+
          s['successful_mean_recovery_arm_joint_travel_rad']/(base['successful_mean_recovery_arm_joint_travel_rad'] or 5.)+
          .1*s['successful_mean_seconds']/(base['successful_mean_seconds'] or 420.),c['update'])
    return min(candidates,key=cost)

def branch_rank(domain,row):
    if domain=='walk' and row.get('flat_foot_clearance',{}).get('moving_swings_measured',0)>=2:
        c=row['flat_foot_clearance']
        clear=c['moving_median_peak_m']>=.0045
        return (not clear,*old_rank(domain,row))
    if domain=='walk':return (False,*old_rank(domain,row))
    return old_rank(domain,row)

def summary(rows,cfg):
    value=old_summary(rows,cfg)
    selected=[r for r in rows if r['qualified_complete']]
    clear=[r['episode']['flat_foot_clearance'] for r in selected
           if r['episode'].get('flat_foot_clearance',{}).get('moving_median_peak_m') is not None]
    value['successful_mean_flat_sole_clearance_m']=sum(c['moving_median_peak_m'] for c in clear)/len(clear) if clear else None
    value['clear_stepping_successes']=sum(c['moving_median_peak_m']>=.0045 for c in clear)
    return value
