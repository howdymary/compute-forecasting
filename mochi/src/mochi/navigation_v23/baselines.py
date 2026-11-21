"""Conventional tuning on exactly the same measured interaction data."""
import numpy as np

from mochi.navigation_v23.engine import ACTIONS


def features(observed):
    values = []
    for name in ACTIONS:
        p = observed['options'][name]
        values += [float(p['feasible']), p.get('length_m', 3.), p.get('turns', 12.),
            p.get('minimum_envelope_clearance_m', 0.)]
    values += [observed['goal_heading_error_rad'], *observed['goal_body_frame_m']]
    return values


def tune(trials):
    fixed = max(ACTIONS, key=lambda a: sum(t['outcomes'][a]['reward'] for t in trials))
    matrix = np.asarray([features(t['observation']) for t in trials])
    best = {'feature': 0, 'threshold': 0., 'left': fixed, 'right': fixed,
        'training_reward': sum(t['outcomes'][fixed]['reward'] for t in trials)}
    for column in range(matrix.shape[1]):
        values = np.unique(matrix[:, column])
        for threshold in (values[:-1] + values[1:]) / 2:
            left = matrix[:, column] <= threshold
            if not left.any() or left.all():
                continue
            a = max(ACTIONS, key=lambda a: sum(t['outcomes'][a]['reward'] for t, take in zip(trials, left) if take))
            b = max(ACTIONS, key=lambda a: sum(t['outcomes'][a]['reward'] for t, take in zip(trials, left) if not take))
            reward = sum(t['outcomes'][a if take else b]['reward'] for t, take in zip(trials, left))
            if reward > best['training_reward']:
                best = {'feature': column, 'threshold': float(threshold), 'left': a, 'right': b, 'training_reward': reward}
    return {'fixed': fixed, 'contextual_tuning': best,
        'scope': 'Grid-tuned decision stump and global fixed profile, using the same physical candidate outcomes as SFT.'}


def conventional(observed, model):
    return model['left'] if features(observed)[model['feature']] <= model['threshold'] else model['right']


def summary(rows):
    valid = [r for r in rows if r['qualified']]
    return {'n': len(rows), 'qualified': len(valid), 'complete': sum(r['complete'] for r in rows),
        'falls': sum(r['fall'] for r in rows), 'contacts': sum(r['invalid_contact'] for r in rows),
        'qualified_mean_steps': sum(r['steps']['attempts'] for r in valid) / len(valid) if valid else None,
        'qualified_mean_distance_m': sum(r['executed_distance_m'] for r in valid) / len(valid) if valid else None,
        'qualified_mean_seconds': sum(r['physical_seconds'] for r in valid) / len(valid) if valid else None}
