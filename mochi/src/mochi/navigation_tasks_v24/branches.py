"""Measured component alternatives from physically reached prefix states."""
import math
import time
import numpy as np

from mochi.balanced.sequence import PhysicalStop
from mochi.smooth_v16.objective import branch_metrics
from mochi.navigation_v23.engine import ACTIONS as NAVIGATION_ACTIONS
from . import policy
from .approaches import candidate_approach, task_pose, transit
from .snapshot import restore


def evaluate(saved, domain, task, action):
    w = restore(saved, record=False)
    start, wall = float(w.d.time), time.perf_counter()
    steps = w.step_counter.summary()['attempts']
    first_measurement = len(w.measurements)
    result, recovery, failure = None, None, None
    try:
        if domain == 'navigation':
            goal = task_pose(w, task)
            approach = candidate_approach(w, goal)
            if approach.get('direct_fine'):
                return {'domain': domain, 'task': task, 'action': action,
                    'excluded': 'Shared fine alignment has no route-selector decision',
                    'wall_seconds': time.perf_counter() - wall}
            arrivals = transit(w, approach['pose'], task,
                choose=lambda *_: {'action': action, 'source': 'Measured training candidate'},
                fine_goal=goal, fine_mode=approach['alignment_mode'])
            result = {'success': all(r['success'] for r in arrivals), 'arrivals': arrivals}
        else:
            result = policy.execute(w, domain, task, action)
            if result['success'] and domain != 'recovery':
                recovery = policy.execute(w, 'recovery', task, 'R4')
    except PhysicalStop as error:
        failure = str(error)
    measurements = w.measurements[first_measurement:]
    metrics = branch_metrics(measurements)
    support, longest = 0., 0.
    for a, b in zip(measurements, measurements[1:]):
        support = support + b['t'] - a['t'] if sum(b['loads_n'].values()) < .1 else 0.
        longest = max(longest, support)
    duration = float(w.d.time) - start
    episode = w.episode()
    moving = [s for s in episode['flat_foot_clearance']['swings']
        if s['start_t'] >= start and s['category'] in ['flat_transit', 'turning', 'fixture_clearance']]
    clearance = float(np.median([s['peak_minimum_sole_clearance_m'] for s in moving])) if moving else None
    accelerations, torque_changes = [], []
    for a, b in zip(measurements, measurements[1:]):
        if a['gait_phase'] == b['gait_phase'] == 'native-walk':
            accelerations.extend(((np.asarray(b['qd']) - a['qd']) / (b['t'] - a['t'])).tolist())
            torque_changes.extend((np.asarray(b['tau']) - a['tau']).tolist())
    native_acceleration = float(np.sqrt(np.mean(np.square(accelerations)))) if accelerations else None
    native_torque_change = float(np.sqrt(np.mean(np.square(torque_changes)))) if torque_changes else None
    valid = bool(result and result['success'] and not failure and not w.fall and not w.invalid_contact
        and (domain == 'recovery' or domain == 'navigation' or recovery and recovery['success'])
        and metrics['roll_rms_deg'] is not None and metrics['roll_rms_deg'] <= 2
        and metrics['roll_peak_deg'] <= 12 and longest <= .06
        and (native_acceleration is None or native_acceleration <= 161.4)
        and (native_torque_change is None or native_torque_change <= .00371)
        and (domain != 'navigation' or len(moving) >= 2 and clearance >= .0045))
    steps = w.step_counter.summary(since=start)['attempts']
    arm_travel = (result or {}).get('arm_joint_travel_rad', 0.)
    rank = [steps, duration] if domain == 'navigation' else [arm_travel, duration] if domain == 'recovery' else [duration, (result or {}).get('max_force_n', 0.)]
    return {'domain': domain, 'task': task, 'action': action, 'valid': valid,
        'result': result, 'coupled_recovery': recovery, 'failure': failure,
        'fall': w.fall, 'invalid_contact': w.invalid_contact, 'metrics': metrics,
        'longest_unsupported_seconds': longest, 'steps': steps, 'physical_seconds': duration,
        'moving_swings': len(moving), 'moving_sole_clearance_m': clearance,
        'native_acceleration_rms': native_acceleration, 'native_torque_change_rms': native_torque_change,
        'arm_travel_rad': arm_travel, 'rank': rank, 'wall_seconds': time.perf_counter() - wall,
        'scope': 'Component branch of a real reached state, not a continuous four-task demo.'}
