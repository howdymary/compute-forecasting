"""Identical physical arm-motion measurements for every controller."""
import numpy as np


def arm_smoothness(episode, since=0.):
    rows = [r for r in episode['control_telemetry'] if r['t'] >= since]
    if len(rows) < 5:
        return {'samples': len(rows), 'velocity_rms_rad_s': None, 'acceleration_rms_rad_s2': None, 'jerk_rms_rad_s3': None}
    times = np.asarray([r['t'] for r in rows])
    q = np.asarray([r['q']['left'] + r['q']['right'] for r in rows])
    dt = np.diff(times)
    assert np.all(dt > 0)
    velocity = np.diff(q, axis=0) / dt[:, None]
    acceleration = np.diff(velocity, axis=0) / ((dt[1:] + dt[:-1]) / 2)[:, None]
    jerk = np.diff(acceleration, axis=0) / ((dt[2:] + 2 * dt[1:-1] + dt[:-2]) / 4)[:, None]
    return {'samples': len(rows), 'sample_interval_mean_s': float(dt.mean()),
        'velocity_rms_rad_s': float(np.sqrt(np.mean(velocity**2))),
        'acceleration_rms_rad_s2': float(np.sqrt(np.mean(acceleration**2))),
        'jerk_rms_rad_s3': float(np.sqrt(np.mean(jerk**2))),
        'travel_rad': float(np.abs(np.diff(q, axis=0)).sum()),
        'scope': 'Finite differences of actual measured joint positions at the recorded telemetry timestamps; both arms, entire declared component.'}
