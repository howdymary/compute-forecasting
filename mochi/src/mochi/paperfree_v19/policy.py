"""Step-efficient flat commands; physical gait and task verifiers stay fixed."""
import json
import math

from ..contact_v18 import policy as prior
from ..curriculum.world import ROOT
from ..smooth_v16.navigation import NavigationParameters, navigate
from ..balanced.sequence import navigate as clearance_move


def config():
    return json.loads((ROOT / 'configs/paperfree-v19-controls.json').read_text())


def choices(domain, task):
    return list(config()['walking']) if domain == 'walk' else prior.choices(domain, task)


def walking_profile(code, task):
    p = dict(config()['walking'][code])
    p.update(p.pop('task_overrides', {}).get(task, {}))
    return p


def observation(w, domain, task):
    obs = prior.observation(w, domain, task)
    obs['available_actions'] = choices(domain, task)
    obs['scene_revision'] = 'richdesk-v19-paperfree'
    obs['support_state'] = {
        'root_xyz_m': [round(float(v), 6) for v in w.d.qpos[:3]],
        'yaw_radians': round(w.yaw(), 5),
        'loads_n': {s: round(v, 4) for s, v in w.loads().items()},
        'leg_positions_rad': [round(float(v), 5) for v in w.d.qpos[w.walker.qids]],
        'foot_xy_m': {s: [round(float(v), 6) for v in w.d.xpos[w.id('body', s + '_ankle_roll_link'), :2]]
                      for s in ['left', 'right']},
    }
    if domain == 'walk':
        obs['required_route'] = 'ordinary flat desk transit; no paper obstacle or crossing task'
        obs['heading_degrees'] = round(math.degrees(w.yaw()), 2)
        obs['root_xy_m'] = [round(float(v), 6) for v in w.d.qpos[:2]]
        obs['loaded_feet'] = {s: round(v, 4) for s, v in w.loads().items()}
        obs['foot_xy_m'] = {
            s: [round(float(v), 6) for v in w.d.xpos[w.id('body', s + '_ankle_roll_link'), :2]]
            for s in ['left', 'right']
        }
    return obs


def decision(obs):
    if obs['domain'] != 'walk':
        return prior.decision(obs)
    from tinker_cookbook.recipes.decisions import Decision
    options = []
    for code in config()['walking']:
        p = walking_profile(code, obs['station'])
        options.append((code, f"flat speed cap {p['speed_m_s']} m/s; forward gain {p['navigation']['forward_gain']}; "
            f"turn cap {p['navigation']['max_yaw_rate']} rad/s; near alignment distance {p['navigation']['near_distance']} m; "
            f"physical swing lift 6 mm; forward residual {p['forward_reference_m'] * 1000:.0f} mm."))
    return Decision(
        'Complete the flat walking leg with supported feet, safe clearance and no collisions. '
        'For valid motion, minimize all measured step attempts, including turns, alignment and corrections. '
        'Time and arm travel only break step-count ties. A failure never earns a low-step bonus. '
        'The paper was removed from the desk and must not be treated as terrain. '
        'The native gait network remains fixed.\nObserved: ' + json.dumps(obs, sort_keys=True), options)


def flat_leg(w, task, action):
    cfg = config()
    p = walking_profile(action, task)
    start = float(w.d.time)
    arrivals = []
    w.raised_native_swing = True
    w.swing_lift_reference = .006
    w.swing_forward_reference = p['forward_reference_m']
    w.swing_joint_residual_limit = .10
    try:
        if task == 'globe':
            w.efficiency_segment = 'fixture_clearance'
            arrivals.append(clearance_move(w, (.32, .105, math.pi / 2), timeout=20., speed=.035,
                position_tolerance=.012, label='laptop-clearance'))
        w.efficiency_segment = 'flat_transit'
        points = cfg['routes'][task]
        for i, point in enumerate(points):
            arrivals.append(navigate(w, point, stop=i == len(points) - 1, speed=p['speed_m_s'],
                label=task + ('-station' if i == len(points) - 1 else '-corridor-' + str(i)),
                parameters=NavigationParameters(**p['navigation'])))
    finally:
        w.raised_native_swing = False
        end = float(w.d.time)
        e = w.episode()
        swings = [s for s in e['flat_foot_clearance']['swings'] if start <= s['start_t'] < end
            and s['category'] in ['flat_transit', 'turning', 'fixture_clearance']]
        from statistics import median
        w.flat_legs.append({
            'task': task, 'controller': action, 'start_t': start, 'end_t': end,
            'steps': w.step_counter.summary(since=start), 'moving_swings': len(swings),
            'moving_minimum_sole_clearance_m': median(s['peak_minimum_sole_clearance_m'] for s in swings) if swings else None,
            'success': bool(arrivals) and len(arrivals) == len(cfg['routes'][task]) + (task == 'globe')
                and all(a['success'] for a in arrivals),
        })
    return arrivals


def execute(w, domain, task, action):
    if action not in choices(domain, task):
        raise ValueError('Unavailable action')
    if domain == 'walk':
        return flat_leg(w, task, action)
    return prior.execute(w, domain, task, action)


def fixed(w, domain, task, default, available):
    action = config()['reference_actions'][domain + ':' + task]
    w.decisions.append({'t': float(w.d.time), 'observation': observation(w, domain, task),
                        'action': action, 'source': 'paper-free fixed engineering reference'})
    return action
