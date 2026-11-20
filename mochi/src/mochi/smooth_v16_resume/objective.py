"""Predeclared development selection when the parent has no qualified baseline."""
from ..smooth_v16.objective import select_checkpoint as original_selection


def select_checkpoint(checkpoints,development,cfg):
    if checkpoints[0]['development']['qualified_complete_successes']:
        return original_selection(checkpoints,development,cfg)
    units=cfg['selection_without_qualified_parent']
    def order(cp):
        s=cp['development'];complete=s['qualified_complete_successes']
        cost=(s['successful_mean_steps']/units['steps']+
              s['successful_mean_recovery_arm_joint_travel_rad']/units['recovery_rad']+
              .1*s['successful_mean_seconds']/units['seconds']) if complete else float('inf')
        return (complete,-s['falls'],-s['invalid_contacts'],-cost,-cp['update'])
    return max(checkpoints,key=order)
