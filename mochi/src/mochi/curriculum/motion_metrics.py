"""Read-only measurements from recorded physical trajectories.

These are replay diagnostics, never rewards retroactively used in the frozen
V6/V7 studies. Contact slip is measured by World; foot clearance and motor work
cannot be reconstructed reliably from 25 Hz body transforms and stay unavailable.
"""
import math
import numpy as np
from .world import MOVES


def _yaw(q):
    w, x, y, z = q
    return math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))


def episode_motion(episode, maximum_time=None):
    frames = episode.get('trajectory', {}).get('frames', [])
    if maximum_time is not None:
        frames = [f for f in frames if f['t'] <= maximum_time]
    path = 0.0
    angular_path = 0.0
    intervals = []
    tilt = []
    for a, b in zip(frames, frames[1:]):
        dt = b['t']-a['t']
        if a.get('phase') != 'walk' or b.get('phase') != 'walk' or not 0 < dt < .09:
            continue
        path += float(np.linalg.norm(np.array(b['positions'][1][:2])-a['positions'][1][:2]))
        angular_path += abs((_yaw(b['quaternions'][1])-_yaw(a['quaternions'][1])+math.pi) % (2*math.pi)-math.pi)
        intervals.append(dt)
        tilt.append(float(b['base_tilt_degrees']))
    walk_seconds = sum(intervals)
    decisions = [d for d in episode.get('decisions', [])
                 if d['observation']['domain'] == 'walk'
                 and (maximum_time is None or d['t'] <= maximum_time)]
    acceleration = []
    yaw_acceleration = []
    direction_reversals = 0
    for a, b in zip(decisions, decisions[1:]):
        dt = b['t']-a['t']
        # Exclude task gaps. These are requested-command changes, not measured
        # body acceleration or motor jerk.
        if not 0 < dt < .8:
            continue
        av, bv = np.array(MOVES[a['action']]), np.array(MOVES[b['action']])
        acceleration.append(float(np.linalg.norm(bv[:2]-av[:2])/dt))
        yaw_acceleration.append(float(abs(bv[2]-av[2])/dt))
        direction_reversals += int(av[2]*bv[2] < 0)
    slip = episode.get('foot_slip_estimate_m', {})
    duration = float(episode.get('duration', 0))
    return {
        'trajectory_sample_hz': episode.get('trajectory', {}).get('sample_hz'),
        'frames_analyzed': len(frames),
        'maximum_time_s': maximum_time,
        'walking_duration_s': walk_seconds,
        'walking_path_m': path,
        'walking_yaw_travel_degrees': math.degrees(angular_path),
        'walking_torso_tilt_rms_degrees': float(np.sqrt(np.mean(np.square(tilt)))) if tilt else None,
        'walking_torso_peak_tilt_degrees': max(tilt) if tilt else None,
        'command_change_rms_m_s2': float(np.sqrt(np.mean(np.square(acceleration)))) if acceleration else None,
        'yaw_command_change_rms_rad_s2': float(np.sqrt(np.mean(np.square(yaw_acceleration)))) if yaw_acceleration else None,
        'turn_direction_reversals': direction_reversals,
        'loaded_foot_slip_entire_episode_m': sum(slip.values()) if slip and maximum_time is None else None,
        'loaded_foot_slip_entire_episode_m_per_s': sum(slip.values())/duration if slip and duration and maximum_time is None else None,
        'foot_clearance_m': None,
        'motor_work_j': None,
        'limits': [
            '25 Hz replay diagnostics; not high-frequency actuator telemetry.',
            'Command changes describe requested velocity, not actual body jerk.',
            'Recorded foot slip covers walking and manipulation; it is not a walking-only metric.',
            'Episode durations and paths differ; compare matched initial intervals as well as whole episodes.',
            'No aggregate naturalness score or causal gait-training claim.'
        ]
    }
