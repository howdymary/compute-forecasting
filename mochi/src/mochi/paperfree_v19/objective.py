"""Valid completion first, then an explicit one-point cost per measured step."""
from ..smooth_v16.objective import qualify as qualify_limits, valid_branch as prior_valid, paired, branch_metrics


INVALID_REWARD = -1_000_000.


def step_reward(steps, seconds, arm_travel=0., valid=False):
    if not valid:
        return INVALID_REWARD
    # Each step costs one point. All tie-breakers together cost less than .002.
    return 1000. - steps - .001 * min(max(arm_travel, 0.), 100.) / 100. - .0001 * min(max(seconds, 0.), 420.) / 420.


def valid_branch(row, domain):
    if not prior_valid(row):
        return False
    if domain == 'walk':
        clearance = row.get('flat_foot_clearance') or {}
        return clearance.get('moving_swings_measured', 0) >= 2 and clearance.get('moving_median_peak_m', 0.) >= .0045
    return True


def branch_reward(domain, row):
    recovery = (row.get('coupled_recovery') or {}).get('arm_joint_travel_rad', 0.)
    if domain == 'recovery':
        recovery = row.get('result', {}).get('arm_joint_travel_rad', 0.)
    return step_reward(row['steps']['attempts'], row['duration_s'], recovery, valid_branch(row, domain))


def qualify(row, cfg):
    qualify_limits(row, cfg)
    legs = row['episode'].get('flat_legs', [])
    row['qualified_complete'] = bool(row['qualified_complete'] and len(legs) == 3
        and all(leg['success'] and leg['moving_swings'] >= 2 and leg['moving_minimum_sole_clearance_m'] >= .0045 for leg in legs)
        and not row['episode']['paper_geometry_present'])
    row['step_reward'] = step_reward(row['episode']['steps']['attempts'], row['episode']['duration'],
        sum(r['arm_joint_travel_rad'] for r in row['episode']['recoveries']), row['qualified_complete'])
    return row


def summary(rows, cfg):
    from ..smooth_v16.objective import summary as original_summary
    # The original summary re-runs its less restrictive qualifier. Restore our
    # per-leg clearance gate before computing the actual eligibility and costs.
    basic = original_summary(rows, cfg)
    for row in rows:
        qualify(row, cfg)
    good = [r for r in rows if r['qualified_complete']]
    basic.update(qualified_complete_successes=len(good),
        smooth_complete_successes=len(good),
        successful_mean_steps=sum(r['episode']['steps']['attempts'] for r in good) / len(good) if good else None,
        successful_mean_seconds=sum(r['episode']['duration'] for r in good) / len(good) if good else None,
        successful_mean_forward_facing_fraction=sum(r['direction_metrics']['forward_facing_fraction'] for r in good) / len(good) if good else None,
        successful_mean_recovery_arm_joint_travel_rad=sum(sum(v['arm_joint_travel_rad'] for v in r['episode']['recoveries']) / 4 for r in good) / len(good) if good else None,
        successful_mean_intertask_arm_joint_travel_rad=sum(sum(r['episode']['intertask_arm_joint_travel_rad'].values()) for r in good) / len(good) if good else None,
        mean_valid_step_reward=sum(r['step_reward'] for r in good) / len(good) if good else None)
    return basic


def select_checkpoint(checkpoints):
    return max(checkpoints, key=lambda c: (
        c['development']['qualified_complete_successes'],
        -(c['development']['successful_mean_steps'] if c['development']['successful_mean_steps'] is not None else float('inf')),
        -(c['development']['successful_mean_recovery_arm_joint_travel_rad'] if c['development']['successful_mean_recovery_arm_joint_travel_rad'] is not None else float('inf')),
        -(c['development']['successful_mean_seconds'] if c['development']['successful_mean_seconds'] is not None else float('inf')),
        -c['update']))
