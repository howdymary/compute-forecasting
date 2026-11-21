"""Apply local constraints to branches and aggregate limits to full routes."""
from ..paperfree_v19.objective import (
    INVALID_REWARD, step_reward, qualify, summary, select_checkpoint, paired,
)


def valid_branch(row, domain):
    m = row['metrics']
    valid = bool(row['success'] and not row['fall'] and not row['invalid_contact']
        and m['roll_rms_deg'] <= 2. and m['roll_peak_deg'] <= 12.
        and row['longest_unsupported_seconds'] <= .06)
    if domain == 'walk':
        c = row.get('flat_foot_clearance') or {}
        valid = bool(valid and c.get('moving_swings_measured', 0) >= 2
            and c.get('moving_median_peak_m', 0.) >= .0045)
    return valid


def branch_reward(domain, row):
    travel = (row.get('coupled_recovery') or {}).get('arm_joint_travel_rad', 0.)
    if domain == 'recovery':
        travel = row.get('result', {}).get('arm_joint_travel_rad', 0.)
    return step_reward(row['steps']['attempts'], row['duration_s'], travel, valid_branch(row, domain))
