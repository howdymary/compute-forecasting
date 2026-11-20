"""Bounded contact and swing-clearance options; native weights stay fixed."""
import json
import math
from dataclasses import replace
from ..smooth_v17 import policy as previous

PRESSES={
 'P5':replace(previous.LAPTOP,code='P5',force=.65),
 'P6':replace(previous.LAPTOP,code='P6',force=.60,pulse_on=.30,pulse_off=.15),
}
CLOSING_SPEED={'P5':.40}

def choices(domain,task):
 return previous.choices(domain,task)+(['P5','P6'] if domain=='laptop' else ['W8'] if domain=='walk' and task!='alarm' else [])

def observation(w,domain,task):
 obs=previous.observation(w,domain,task);obs['available_actions']=choices(domain,task)
 if domain=='laptop':
  obs['loaded_feet_n']={k:round(v,2) for k,v in w.loads().items()}
  obs['heading_degrees']=round(math.degrees(w.yaw()))
 return obs

def decision(obs):
 from tinker_cookbook.recipes.decisions import Decision
 prior_obs={**obs,'available_actions':previous.choices(obs['domain'],obs.get('station',obs['domain']))}
 prior=previous.decision(prior_obs)
 text=prior.text.replace(json.dumps(prior_obs,sort_keys=True),json.dumps(obs,sort_keys=True))
 if obs['domain']=='laptop':
  return Decision(text+' Prefer valid support and successful contact with safe recovery.',
       list(prior.choices)+[
        ('P5','Angle/speed force feedback, target 0.40 rad/s, command cap 0.65 N, measured foot-load guard and bounded pulse finish on a stall; 32 s horizon.'),
        ('P6','Upper-edge 0.60 N press, 0.30 s active / 0.15 s recovery pulses; 24 s horizon. Same global force, release and dwell checks.')])
 if obs['domain']=='walk' and obs.get('station')!='alarm':
  return Decision(text+' Prefer physically verified foot clearance while travelling, then fewer steps and time. Station alignment is measured separately.',
       list(prior.choices)+[('W8','W5 directional walking (W6 on globe leg) plus a 6 mm lift / 2 mm forward swing reference, clipped to 0.10 rad and rate-limited to 2 rad/s. Enabled only with loaded support on flat transit. No arm parking; native weights and all safety checks fixed.')])
 return Decision(text,prior.choices)

def execute(w,domain,task,action):
 if action not in choices(domain,task):raise ValueError('Unavailable action')
 if domain=='laptop' and action in PRESSES:
  w.contact_force_schedule=action=='P5';w.contact_closing_speed=CLOSING_SPEED.get(action,.40)
  try:return w.do_task(task,PRESSES[action],max_seconds=32. if action=='P5' else 24.)
  finally:w.contact_force_schedule=False
 if domain=='walk' and action=='W8':
  from .walking import lifted_leg
  w.raised_native_swing=True
  w.swing_lift_reference=.006;w.swing_forward_reference=.002;w.swing_joint_residual_limit=.10
  try:return lifted_leg(w,task)
  finally:w.raised_native_swing=False
 if domain not in ['walk','recovery']:w.efficiency_segment='manipulation'
 return previous.execute(w,domain,task,action)

def fixed(w,domain,task,default,available):
 action=('W2' if task=='alarm' else 'W8') if domain=='walk' else (
    'R4' if domain=='recovery' else {'alarm':'H0','drawer':'B','laptop':'P5' if w.value('laptop')>=1.22 else 'P6','globe':'G0'}[task])
 w.decisions.append({'t':float(w.d.time),'observation':observation(w,domain,task),
                    'action':action,'source':'fixed contact-repair reference'})
 return action
