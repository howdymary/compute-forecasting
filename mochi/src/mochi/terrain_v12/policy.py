"""Trainable categorical interface; no seed, teacher label or future result."""
import json,math
import numpy as np
from .legs import WALKS,execute_selected_leg
from .tasks import press_alarm
from ..balanced.recovery import RECOVERIES,recover,observation as recovery_observation
from ..curriculum.world import PROFILES
from ..control_v8.manipulation import PRESSES

GOALS={'alarm':(-.375,.04),'drawer':(-.13,.02),'laptop':(.30,.16),'globe':(.35,-.145)}

def fixed(w,domain,task,default,choices):
    action='W0' if domain=='walk' else ('R1' if task=='alarm' else 'R0') if domain=='recovery' else {'alarm':'F','drawer':'B','laptop':'P0','globe':'A'}[task]
    assert action in choices
    w.decisions.append({'t':float(w.d.time),'observation':observation(w,domain,task),'action':action,'source':'fixed heuristic'})
    return action

def observation(w,domain,task):
    if domain=='walk':
        return {'domain':'walk','station':task,'terrain':'book_ascent' if task=='alarm' else 'book_descent_and_flat' if task=='drawer' else 'flat',
                'goal_offset_mm':(np.round((np.array(GOALS[task])-w.d.qpos[:2])*1000/5)*5).tolist(),
                'body_tilt_degrees':round(math.degrees(math.acos(float(np.clip(w.d.xmat[1,8],-1,1))))),
                'root_height_mm':round(w.d.qpos[2]*1000/2)*2,
                'loaded_feet':{k:round(v,1) for k,v in w.loads().items()}}
    if domain=='recovery':
        o=recovery_observation(w,task)
        return {**o,'joint_error_degrees':[round(x/5)*5 for x in o['joint_error_degrees']],
                'joint_speed_degrees_s':[round(x/10)*10 for x in o['joint_speed_degrees_s']],
                'hand_body_offset_mm':[round(x/5)*5 for x in o['hand_body_offset_mm']],
                'body_tilt_degrees':round(o['body_tilt_degrees'])}
    o=w.task_observation(task)
    o['relative_position_mm']=(np.round((np.array(GOALS[task])-w.d.qpos[:2])*1000/2)*2).tolist()
    o['body_tilt_degrees']=round(o['body_tilt_degrees']);o['object_state']=round(o['object_state'],3)
    return o

def decision(obs):
    from tinker_cookbook.recipes.decisions import Decision
    domain=obs['domain']
    if domain=='walk':
        goal='Select a walking strategy that completes the terrain and reaches a supported manipulation stance. The low-level gait, path and verifiers are fixed. Prefer safe completion, balance, smoothness, then time.'
        choices=[(k,f"stance width {p['width']*1000:.0f} mm; support transfer {p['shift_seconds']:.2f} s; swing time multiplier {p['swing_scale']:.2f}; flat velocity {p['flat_speed']*1000:.0f} mm/s") for k,p in WALKS.items()]
    elif domain=='recovery':
        goal='Choose safe active-arm withdrawal with little unnecessary travel. Require no fixture collisions and a stable recovered arm.'
        choices=[(r.code,f'{r.waypoint} withdrawal; joint slew {r.slew:.3f} rad / 20 ms; pause {r.pause:.2f} s') for r in RECOVERIES if r.code in ['R0','R1','R3']]
    elif domain=='laptop':
        goal='Close the laptop through upper-edge contact with safe force, then release.'
        choices=[(p.code,f'press {p.force:.2f} N; slew {p.slew:.3f} rad / 20 ms') for p in PRESSES[:3]]
    else:
        goal='Complete '+domain+' through verified hand contact, safe force, release and dwell.'
        choices=[(p.code,f'speed {p.speed*1000:.0f} mm/s; depth {p.depth*1000:.1f} mm; force backoff {p.force:.3f} N; brake {p.brake*1000:.1f} mm; hold {p.hold:.2f} s') for p in ([PROFILES[i] for i in [1,2,5]] if domain=='alarm' else PROFILES[:3])]
    return Decision(goal+'\nObserved: '+json.dumps(obs,sort_keys=True),choices)

def execute(w,domain,task,action):
    if domain=='walk':
        return execute_selected_leg(w,task,action)
    if domain=='recovery':return recover(w,task,next(p for p in RECOVERIES if p.code==action))
    p=next(p for p in (PRESSES if task=='laptop' else PROFILES) if p.code==action)
    return press_alarm(w,p) if task=='alarm' else w.do_task(task,p)
