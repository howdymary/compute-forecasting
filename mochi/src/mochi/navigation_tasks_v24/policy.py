"""Small task action sets with measured, object-relative observations."""
from dataclasses import asdict, replace
import json
import math
import numpy as np

from mochi.contact_v18.policy import PRESSES
from mochi.paperfree_v19 import policy as existing

ACTIONS = {'alarm': ['H0', 'F'], 'drawer': ['B', 'C'], 'laptop': ['P5', 'L0'],
    'globe': ['G0', 'G1'], 'recovery': ['R0', 'R4']}


def observation(w, domain, task):
    side = w.approach_side if domain == 'recovery' else 'left' if task == 'laptop' else 'right'
    arm = w.arm[side]
    rotation = w.d.xmat[1].reshape(3, 3)
    goal = w.station_goal(task)
    return {'domain': domain, 'task': task, 'available_actions': ACTIONS[domain],
        'state_information': 'privileged exact object geometry and measured robot state',
        'goal_offset_world_m': np.round(np.asarray(goal[:2]) - w.d.qpos[:2], 4).tolist(),
        'goal_heading_error_rad': round((goal[2] - w.yaw() + math.pi) % (2 * math.pi) - math.pi, 4),
        'object_joint_position': round(w.value(task), 5),
        'object_joint_velocity': round(float(w.d.qvel[w.v[task]]), 5),
        'active_arm': side, 'joint_error_rad': np.round(w.d.qpos[arm['qs']] - arm['rest'], 4).tolist(),
        'joint_velocity_rad_s': np.round(w.d.qvel[arm['vs']], 4).tolist(),
        'hand_body_offset_m': np.round(rotation.T @ (w.d.site_xpos[arm['tip']] - w.d.qpos[:3]), 4).tolist(),
        'foot_loads_n': {k: round(v, 4) for k, v in w.loads().items()},
        'body_tilt_degrees': round(math.degrees(math.acos(float(np.clip(rotation[2, 2], -1, 1)))), 3),
        'hand_contact': bool(w.contacts(task)[0])}


def decision(obs):
    from tinker_cookbook.recipes.decisions import Decision
    descriptions = {
        'H0': 'Clock contact with rest-posture-regularized IK; same force, stroke, release and dwell checks.',
        'F': 'Clock staged contact controller with collision-aware IK; same success checks.',
        'B': 'Drawer B contact profile; existing bounded speed, force backoff and braking.',
        'C': 'Drawer C contact profile; existing bounded speed, force backoff and braking.',
        'P5': 'Object-relative upper-edge contact; adaptive closing-speed target 0.40 rad/s and force cap 0.65 N; 32 second horizon.',
        'L0': 'Same adaptive contact law; closing-speed target 0.30 rad/s and force cap 0.55 N; 32 second horizon.',
        'G0': 'Globe contact: 0.012 m/s, 0.055 N force backoff, 0.003 braking parameter and 0.25 s hold.',
        'G1': 'Globe contact: 0.010 m/s, 0.050 N force backoff, 0.003 braking parameter and 0.20 s hold.',
        'R0': 'Direct bounded joint withdrawal to the safe rest posture; requires release, no fixture contacts and stable support.',
        'R4': 'Minimum-jerk recovery with clock clearance; requires release, no fixture contacts and stable support.'}
    return Decision('Select a physical ' + obs['domain'] + ' controller. Valid completion, stable support and no unintended contact come first. '
        'Among valid recoveries prefer less measured arm travel, then less time. Among valid tasks prefer less time and lower force. '
        'Native gait weights are fixed.\nObserved: ' + json.dumps(obs, sort_keys=True),
        [(a, descriptions[a]) for a in obs['available_actions']])


def execute(w, domain, task, action):
    assert action in ACTIONS[domain]
    if domain != 'laptop':
        return existing.execute(w, domain, task, action)
    p = PRESSES['P5'] if action == 'P5' else replace(PRESSES['P5'], code='L0', force=.55)
    w.contact_closing_speed = .4 if action == 'P5' else .3
    w.efficiency_segment = 'manipulation'
    return w.do_task('laptop', p, max_seconds=32.)
