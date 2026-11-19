"""Bounded choices with unchanged legacy IDs and explicit efficient commands."""
import json
import math

from ..terrain_v12.legs import WALKS as LEGACY_WALKS
from ..terrain_v12.policy import observation as prior_observation, decision as prior_decision
from ..curriculum.world import Profile, PROFILES
from .navigation import NavigationParameters

WALKS = {k: dict(v) for k,v in LEGACY_WALKS.items()}
WALKS.update(W3={**WALKS['W0'], 'flat_speed': .080},
             W4={**WALKS['W0'], 'flat_speed': .095})
NAVIGATION = {k: NavigationParameters() for k in LEGACY_WALKS}
NAVIGATION.update(W3=NavigationParameters(yaw_gain=2., max_yaw_rate=.7, forward_gain=.95, alignment_gain=.8),
                  W4=NavigationParameters(yaw_gain=2.2, max_yaw_rate=.8, forward_gain=1.2, alignment_gain=1.))
GLOBES={'A':PROFILES[0], 'G0':Profile('G0',.012,.0002,.055,.003,.25),
        'G1':Profile('G1',.010,.0002,.050,.003,.20)}


def choices(domain, task):
    if domain == 'walk':
        return ['W0','W1','W2'] if task == 'alarm' else ['W0','W3','W4']
    if domain == 'recovery':
        return ['R0','R1','R3']
    if domain == 'globe':
        return ['A','G0','G1']
    return ['P0','P1','P2'] if task == 'laptop' else ['B','C','F'] if task == 'alarm' else ['A','B','C']


def observation(w, domain, task):
    obs = prior_observation(w, domain, task)
    obs['available_actions'] = choices(domain, task)
    if domain == 'walk':
        obs['heading_degrees'] = round(math.degrees(w.yaw())/5)*5
        obs['steps_so_far'] = w.step_counter.summary()['attempts']
        obs['navigation'] = 'turn toward travel, walk forward, align before task'
    return obs


def decision(obs):
    if obs['domain']=='globe':
        from tinker_cookbook.recipes.decisions import Decision
        return Decision('Rotate the globe through actual hand contact and stop within the fixed target tolerance. Prefer valid completion, low force and safe withdrawal.\nObserved: '+json.dumps(obs,sort_keys=True),
            [(code,f'speed {p.speed*1000:.0f} mm/s; force backoff {p.force:.3f} N; braking offset {p.brake*12:.3f} rad; hold {p.hold:.2f} s') for code,p in GLOBES.items()])
    if obs['domain'] != 'walk':
        return prior_decision({k:v for k,v in obs.items() if k!='available_actions'})
    from tinker_cookbook.recipes.decisions import Decision
    options=[]
    for code in obs['available_actions']:
        p=WALKS[code];n=NAVIGATION[code]
        options.append((code, f"stance {p['width']*1000:.0f} mm; support transfer {p['shift_seconds']:.2f} s; swing multiplier {p['swing_scale']:.2f}; flat speed cap {p['flat_speed']*1000:.0f} mm/s; turn cap {n.max_yaw_rate:.2f} rad/s; approach gain {n.forward_gain:.2f}; alignment gain {n.alignment_gain:.2f}"))
    return Decision('Complete the walking leg with valid support and no collisions. Within safe balance limits prefer fewer measured footstep attempts, then less physical time. Turns and corrections count. Never trade completion for fewer steps. Native gait weights and route are fixed.\nObserved: '+json.dumps(obs,sort_keys=True),options)


def fixed(w, domain, task, default, available):
    action = 'W0' if domain=='walk' else ('R1' if task=='alarm' else 'R0') if domain=='recovery' else {'alarm':'F','drawer':'B','laptop':'P0','globe':'A'}[task]
    assert action in available
    w.decisions.append({'t':float(w.d.time),'observation':observation(w,domain,task),
                        'action':action,'source':'competent fixed directional controller'})
    return action


def execute(w, domain, task, action):
    if action not in choices(domain,task):
        raise ValueError('Unavailable action')
    if domain=='walk':
        from .sequence import leg
        return leg(w,task,action)
    from ..terrain_v12.policy import execute as prior_execute
    w.efficiency_segment='arm_recovery' if domain=='recovery' else 'manipulation'
    if domain=='globe':
        return w.do_task(task,GLOBES[action])
    return prior_execute(w,domain,task,action)
