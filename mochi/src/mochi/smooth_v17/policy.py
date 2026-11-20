"""Extended fixed controller library. Only outer decision weights are trained."""
import json
from dataclasses import replace
from ..curriculum.world import PROFILES
from ..control_v8.manipulation import PRESSES
from ..smooth_v16.policy import (choices as old_choices,observation as old_observation,
    decision as old_decision,execute as old_execute)
from .home_clock import home_press
from .gait import globe_leg,PARAMETERS as GLOBE_PARAMETERS
from ..smooth_v16.policy import WALKS,NAVIGATION

HOME=replace(next(p for p in PROFILES if p.code=='F'),code='H0')
LAPTOP=replace(next(p for p in PRESSES if p.code=='P2'),code='P4',force=.60,release_degrees=42.)


def choices(domain,task):
    return old_choices(domain,task)+(['W6'] if domain=='walk' and task=='globe' else ['H0'] if domain=='alarm' else ['P4'] if domain=='laptop' else [])


def observation(w,domain,task):
    obs=old_observation(w,domain,task);obs['available_actions']=choices(domain,task);return obs


def decision(obs):
    if obs['domain']=='walk' and obs.get('station')=='globe':
        from tinker_cookbook.recipes.decisions import Decision
        options=[]
        for code in obs['available_actions']:
            p=WALKS['W5'] if code=='W6' else WALKS[code]
            n=GLOBE_PARAMETERS if code=='W6' else NAVIGATION[code]
            speed=.12 if code=='W6' else p['flat_speed']
            options.append((code,f"stance {p['width']*1000:.0f} mm; support transfer {p['shift_seconds']:.2f} s; swing multiplier {p['swing_scale']:.2f}; flat speed cap {speed*1000:.0f} mm/s; turn cap {n.max_yaw_rate:.2f} rad/s; approach gain {n.forward_gain:.2f}; alignment gain {n.alignment_gain:.2f}"))
        return Decision('Complete the walking leg with valid support and no collisions. Within safe balance limits prefer fewer measured footstep attempts, then less physical time. Turns and corrections count. Never trade completion for fewer steps. Native gait weights and route are fixed.\nObserved: '+json.dumps(obs,sort_keys=True),options)
    if obs['domain'] not in ['alarm','laptop']:return old_decision(obs)
    from tinker_cookbook.recipes.decisions import Decision
    if obs['domain']=='alarm':
        goal='Complete the clock task through hand contact, safe force, release and dwell. Prefer a valid reach and recovery with less joint travel.'
        options=[(p.code,f'speed {p.speed*1000:.0f} mm/s; depth {p.depth*1000:.1f} mm; force backoff {p.force:.3f} N; brake {p.brake*1000:.1f} mm; hold {p.hold:.2f} s; IK joint prior 0 m/rad') for p in PROFILES if p.code in ['B','C','F']]
        options.append(('H0','F contact settings; IK joint prior 0.0007 m/rad toward the walking rest posture.'))
    else:
        goal='Close the laptop through upper-edge hand contact, safe force, release and dwell. The global force limit stays 0.8 N.'
        options=[(p.code,f'press {p.force:.2f} N; slew {p.slew:.3f} rad / 20 ms; action horizon 12 s') for p in PRESSES[:3]]
        options.append(('P4','press 0.60 N; slew 0.012 rad / 20 ms; action horizon 16 s; same feedback and release checks.'))
    return Decision(goal+'\nObserved: '+json.dumps(obs,sort_keys=True),options)


def execute(w,domain,task,action):
    if action not in choices(domain,task):raise ValueError('Unavailable action')
    if domain=='walk' and task=='globe' and action=='W6':return globe_leg(w)
    if domain=='alarm' and action=='H0':return home_press(w,HOME)
    if domain=='laptop' and action=='P4':return w.do_task(task,LAPTOP,max_seconds=16.)
    return old_execute(w,domain,task,action)


def fixed(w,domain,task,default,available):
    action=('W2' if task=='alarm' else 'W6' if task=='globe' else 'W4') if domain=='walk' else 'R4' if domain=='recovery' else {'alarm':'H0','drawer':'B','laptop':'P4','globe':'G0'}[task]
    assert action in available
    w.decisions.append({'t':float(w.d.time),'observation':observation(w,domain,task),'action':action,'source':'fixed extended controller reference'})
    return action
