"""One learned interface for walking, task profiles and active-arm recovery."""
import asyncio,json
from ..curriculum.world import MOVES,PROFILES
from .manipulation import PRESSES
from .recovery import RECOVERIES

def band(x,a,b):return 'within_'+str(a) if abs(x)<=a else ('positive_' if x>0 else 'negative_')+('small' if abs(x)<b else 'large')
def encode(obs):
 domain=obs['domain']
 if domain=='walk':
  f,l=obs['target_forward_mm'],obs['target_left_mm'];d=obs['distance_mm']
  return {'domain':'walk','phase':obs['phase'],'distance_mm':'below_6' if d<6 else '6_through_60' if d<=60 else 'above_60','heading_error_degrees':band(obs['heading_error_degrees'],7,25),'forward_offset_mm':band(f,4,25),'left_offset_mm':band(l,4,25),'larger_offset_axis':'left' if abs(l)>abs(f) else 'forward','cross_track_mm':band(obs['cross_track_mm'],5,15),'forward_velocity_mm_s':band(obs['velocity_forward_mm_s'],10,40),'left_velocity_mm_s':band(obs['velocity_left_mm_s'],10,40),'yaw_rate_degrees_s':band(obs['yaw_rate_degrees_s'],10,40),'foot_contacts':obs['foot_contacts'],'previous_command':(obs.get('recent_commands') or ['none'])[-1],'body_tilt':'below_5' if obs['body_tilt_degrees']<5 else 'at_least_5'}
 if domain=='recovery':
  return {**obs,'joint_error_degrees':[round(x/5)*5 for x in obs['joint_error_degrees']],'joint_speed_degrees_s':[round(x/10)*10 for x in obs['joint_speed_degrees_s']],'hand_body_offset_mm':[round(x/5)*5 for x in obs['hand_body_offset_mm']],'body_tilt_degrees':round(obs['body_tilt_degrees']),'maximum_joint_error_degrees':round(obs['maximum_joint_error_degrees']/5)*5}
 return {**obs,'object_state':round(obs['object_state'],3),'relative_position_mm':[round(x/2)*2 for x in obs['relative_position_mm']],'body_tilt_degrees':round(obs['body_tilt_degrees'])}
def decision(obs):
 from tinker_cookbook.recipes.decisions import Decision
 if obs['domain']=='walk':
  goal='Track the local reference, then align and settle precisely. Heading error is the current desired travel heading during track, final orientation during align. Positive heading/left offset means left. Only stop when close and aligned. The native motor gait is fixed.';choices=[(k,f'forward {v[0]*1000:.0f} mm/s, left {v[1]*1000:.0f} mm/s, yaw left {v[2]:.2f} rad/s') for k,v in MOVES.items()]
 elif obs['domain']=='recovery':
  goal='Select a collision-free active-arm withdrawal to its stable transit pose. Avoid redundant parking or pauses when direct folding is safe. Joint/hand motion, contact and balance are measured; the inactive arm stays commanded at rest.';choices=[(r.code,f'{r.waypoint} withdrawal (alarm: outward shoulder clearance before lowering; other tasks: normal withdrawal) then fold; joint increment {r.slew:.3f} rad per 20 ms; pause {r.pause:.2f} s') for r in RECOVERIES]
 elif obs['domain']=='laptop':
  goal='Close the laptop through physical hand contact, withdraw, and allow it to settle. Select the upper-edge press strength and cadence. Require safe force and an upright robot.';choices=[(p.code,f'edge press magnitude {p.force:.2f} N; active {p.pulse_on:.2f} s / pause {p.pulse_off:.2f} s; bounded joint slew {p.slew:.3f}') for p in PRESSES]
 else:
  goal='Select a reliable, efficient contact profile for '+obs['domain']+'. Require the measured dwell, hand contact, safe force and upright robot.';choices=[(p.code,f'speed {p.speed*1000:.0f} mm/s, depth {p.depth*1000:.1f} mm, force backoff {p.force:.3f} N, brake {p.brake*1000:.1f} mm, hold {p.hold:.2f} s') for p in PROFILES]
 return Decision(goal+'\nObserved state: '+json.dumps(obs,sort_keys=True),choices)
class Selector:
 def __init__(self):self.cache={};self.calls=0;self.hits=0
 async def __call__(self,sampler,renderer,obs):
  from tinker_cookbook.recipes.decisions import sample_decision
  observed=encode(obs);key=json.dumps(observed,sort_keys=True)
  if key in self.cache:self.hits+=1;return self.cache[key]
  distribution=await sample_decision(sampler,renderer.render(decision(observed)));self.calls+=1;answer=(max(distribution,key=distribution.get),distribution);self.cache[key]=answer;return answer
 def receipt(self):return {'actual_tinker_inference_calls':self.calls,'identical_observation_cache_hits':self.hits,'distributions':[{'model_observation':json.loads(k),'action':v[0],'distribution':v[1]} for k,v in self.cache.items()]}
