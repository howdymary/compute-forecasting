"""Interpret bounded numeric proposals without executing generated source."""
from contextlib import contextmanager
from contextvars import ContextVar
import copy
from dataclasses import replace
import math
import re

_POSITION_TOLERANCE = ContextVar('inkling_position_tolerance', default=.012)

LIMITS = {
    'navigation': {'yaw_gain': (1.8, 3.2), 'max_yaw_rate': (.6, 1.2),
        'forward_gain': (1., 2.2), 'alignment_gain': (.6, 1.5),
        'near_distance': (.015, .045), 'speed_m_s': (.105, .14),
        'terminal_translation_deadband': bool, 'terminal_yaw_deadband': bool,
        'globe_clearance_x_m': (.295, .32), 'globe_clearance_y_m': (.055, .105),
        'globe_corridor_x_m': (.295, .32), 'parked_arms': bool},
    'laptop': {'station_x_m': (.300, .318), 'station_y_m': (.148, .165),
        'force_n': (.45, .65), 'radius_m': (.145, .15), 'contact_x_m': (.257, .263),
        'closing_speed_rad_s': (.12, .45), 'release_degrees': (42., 56.),
        'station_position_tolerance_m': (.008, .012)},
    'recovery': {'duration_scale': (.8, 1.4)},
}


def validate(candidate):
    if not isinstance(candidate, dict) or not re.fullmatch(r'[a-z0-9-]{1,48}', str(candidate.get('id', ''))):
        raise ValueError('Invalid candidate identity')
    domain = candidate.get('domain')
    if domain not in LIMITS or not isinstance(candidate.get('changes'), dict) or not candidate['changes']:
        raise ValueError('Invalid candidate domain or empty changes')
    for name, value in candidate['changes'].items():
        if name not in LIMITS[domain]:
            raise ValueError('Unsupported controller field: ' + name)
        bound = LIMITS[domain][name]
        if bound is bool:
            if type(value) is not bool:
                raise ValueError('Expected a boolean')
        elif (type(value) not in [int, float] or not math.isfinite(value)
                or not bound[0] <= value <= bound[1]):
            raise ValueError('Out-of-bounds controller parameter: ' + name)
    return copy.deepcopy(candidate)


@contextmanager
def apply(candidate=None):
    """Process-local controller adapter. Archived source and verifiers are intact."""
    if candidate is None:
        yield
        return
    c = validate(candidate)
    from mochi.paperfree_v19 import policy
    from mochi.contact_v18 import policy as contact
    from mochi.smooth_v16 import navigation, recovery
    original = (policy.config, policy.clearance_move, navigation.command,
        contact.PRESSES, contact.CLOSING_SPEED, recovery.SmoothRecovery, policy.navigate)
    cfg = copy.deepcopy(original[0]())
    changes = c['changes']
    try:
        if c['domain'] == 'navigation':
            p = cfg['walking']['W10']
            if 'speed_m_s' in changes:
                p['speed_m_s'] = changes['speed_m_s']
            for key in ['yaw_gain', 'max_yaw_rate', 'forward_gain', 'alignment_gain', 'near_distance', 'parked_arms']:
                if key in changes:
                    p['navigation'][key] = changes[key]
            if 'globe_corridor_x_m' in changes:
                for i in [0, 1]:
                    cfg['routes']['globe'][i][0] = changes['globe_corridor_x_m']

            def clearance(w, goal, **kwargs):
                if kwargs.get('label') == 'laptop-clearance':
                    goal = (changes.get('globe_clearance_x_m', goal[0]), changes.get('globe_clearance_y_m', goal[1]), goal[2])
                return original[1](w, goal, **kwargs)

            policy.clearance_move = clearance

            def command(position, yaw, goal, line_heading, speed, parameters, aligning=False):
                velocity, phase, desired = original[2](position, yaw, goal, line_heading, speed, parameters, aligning)
                error = (goal[2] - yaw + math.pi) % (2 * math.pi) - math.pi
                if aligning and math.dist(position, goal[:2]) < _POSITION_TOLERANCE.get() and abs(error) < math.radians(9):
                    velocity = (0. if changes.get('terminal_translation_deadband', False) else velocity[0],
                        0. if changes.get('terminal_translation_deadband', False) else velocity[1],
                        0. if changes.get('terminal_yaw_deadband', False) else velocity[2])
                return velocity, phase, desired

            navigation.command = command
        elif c['domain'] == 'laptop':
            goal = cfg['routes']['laptop'][-1]
            goal[0], goal[1] = changes.get('station_x_m', goal[0]), changes.get('station_y_m', goal[1])
            mapping = {'force_n': 'force', 'radius_m': 'radius', 'contact_x_m': 'contact_x', 'release_degrees': 'release_degrees'}
            contact.PRESSES = dict(original[3])
            contact.PRESSES['P5'] = replace(original[3]['P5'], **{mapping[k]: v for k, v in changes.items() if k in mapping})
            contact.CLOSING_SPEED = {**original[4], 'P5': changes.get('closing_speed_rad_s', original[4]['P5'])}

            def precise_arrival(w, goal, **kwargs):
                # A proposed base pose must actually be reached through walking.
                # This is declared candidate implementation, not a looser verifier.
                if kwargs.get('label') == 'laptop-station' and any(k in changes for k in ['station_x_m', 'station_y_m']):
                    kwargs['position_tolerance'] = changes.get('station_position_tolerance_m', .012)
                token = _POSITION_TOLERANCE.set(kwargs.get('position_tolerance', .012))
                try:
                    return original[6](w, goal, **kwargs)
                finally:
                    _POSITION_TOLERANCE.reset(token)

            policy.navigate = precise_arrival
        else:
            recovery.SmoothRecovery = lambda: original[5](duration=1.2 * changes['duration_scale'])
        policy.config = lambda: copy.deepcopy(cfg)
        yield
    finally:
        (policy.config, policy.clearance_move, navigation.command,
            contact.PRESSES, contact.CLOSING_SPEED, recovery.SmoothRecovery, policy.navigate) = original
