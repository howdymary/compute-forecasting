"""Actuator-only reference tracking. Native gait/balance/IK are unchanged."""
import json,math,time
from pathlib import Path
import numpy as np
from ..curriculum.world import World,MOVES,PROFILES,DT,wrap

def projection(point,a,b):
 p,a,b=map(np.asarray,[point,a,b]);v=b-a;u=float(np.clip(np.dot(p-a,v)/max(np.dot(v,v),1e-12),0,1));return a+u*v,u,float(np.linalg.norm(p-(a+u*v)))

def teacher(obs):
 """Visible-state reference follower; used only by the explicitly fixed baseline."""
 angle=obs['heading_error_degrees']
 if abs(angle)>7:return ('left' if angle>0 else 'right')+('_slow' if abs(angle)<25 else '')
 if obs['distance_mm']<6:return 'stop'
 f,l=obs['target_forward_mm'],obs['target_left_mm']
 if abs(l)>4 and abs(l)>abs(f):return 'side_left' if l>0 else 'side_right'
 if f< -4:return 'back'
 if f>4:return 'forward' if obs['distance_mm']>60 else 'slow'
 return 'side_left' if l>0 else 'side_right'

class PathRunner:
 def __init__(self,route,world_class=World):self.route=route;self.world_class=world_class
 def reset(self,seed,record=True):
  self.w=self.world_class(seed,record);self.index=0;self.segment=0;self.mode='walk';self.arrivals=[];self.leg_start=0.;self.settle=0.;self.start=time.perf_counter();self.path_trace=[];self.calls=0;self.failure=None;self.aligning=False;self.stop_bias=np.array([.010,.003]);self.stop_trials=[];return self.status()
 def observation(self):
  w=self.w;leg=self.route['legs'][self.index];segments=leg['segments'];s=segments[self.segment];p=w.d.qpos[:2];distance=float(np.linalg.norm(p-np.array(s['to'])))
  if distance<.012 and self.segment<len(segments)-1:self.segment+=1;s=segments[self.segment];distance=float(np.linalg.norm(p-np.array(s['to'])))
  close,u,error=projection(p,s['from'],s['to']);length=max(s['length_m'],1e-6);look=min(1.,u+.08/length);local=np.array(s['from'])+(np.array(s['to'])-s['from'])*look
  final_segment=self.segment==len(segments)-1
  if final_segment and distance<.022:self.aligning=True
  phase='align' if self.aligning else 'track'
  if phase=='align':
   h=leg['goal'][2];R=np.array([[math.cos(h),-math.sin(h)],[math.sin(h),math.cos(h)]]);local=np.array(leg['goal'][:2])-R@self.stop_bias;desired=h;distance=float(np.linalg.norm(p-local))
  elif math.dist(local,p)>.001:
   bearing=math.atan2(local[1]-p[1],local[0]-p[0]);offset={'forward':0,'back':math.pi,'side_left':-math.pi/2,'side_right':math.pi/2}[s['command']];desired=wrap(bearing+offset)
  else:desired=s['heading']
  # Waypoint geometry is observable; no teacher action, seed, latent parameter
  # or future result is included. All fields go into the inference cache key.
  obs=w.walk_observation([*local,desired]);obs.update({'phase':phase,'distance_mm':round(distance*1000,1),'cross_track_mm':round(error*1000,1),'remaining_leg_mm':round((distance+sum(x['length_m'] for x in segments[self.segment+1:]))*1000,1),'path_tangent_error_degrees':round(math.degrees(wrap(s['heading']-w.yaw())),1),'final_heading_error_degrees':round(math.degrees(wrap(leg['goal'][2]-w.yaw())),1),'velocity_forward_mm_s':round(float(np.dot(w.d.qvel[:2],[math.cos(w.yaw()),math.sin(w.yaw())]))*1000,1),'velocity_left_mm_s':round(float(np.dot(w.d.qvel[:2],[-math.sin(w.yaw()),math.cos(w.yaw())]))*1000,1),'yaw_rate_degrees_s':round(math.degrees(float(w.d.qvel[5])),1)})
  self.local_target=local.tolist();return obs
 def status(self):
  if self.w.fall or self.index>=len(self.route['legs']) or self.w.d.time-self.leg_start>35:
   self.failure='fall' if self.w.fall else 'leg_timeout' if self.index<len(self.route['legs']) else None;self.mode='done';return {'mode':'done','failure':self.failure}
  return {'mode':self.mode,'station':self.route['legs'][self.index]['task'],'observation':self.observation() if self.mode=='walk' else self.w.task_observation(self.route['legs'][self.index]['task'])}
 def advance(self,action):
  w=self.w;leg=self.route['legs'][self.index];self.calls+=1
  if self.mode=='walk':
   w.task=None;w.phase='walk';obs=self.observation();w.decisions.append({'t':float(w.d.time),'observation':obs,'action':action});self.path_trace.append({'t':float(w.d.time),'leg':self.index,'segment':self.segment,'local_target':self.local_target,'cross_track_mm':obs['cross_track_mm'],'reference_heading':w.yaw()+math.radians(obs['heading_error_degrees']),'route_version':self.route['version']})
   hold=.60 if action=='stop' else .32 if obs['distance_mm']>70 else .16
   stop_start=w.d.qpos[:2].copy()
   end=float(w.d.time)+hold
   while w.d.time<end and not w.fall:
    distance=math.dist(w.d.qpos[:2],leg['goal'][:2]);heading=abs(wrap(leg['goal'][2]-w.yaw()))
    arrived=self.segment==len(leg['segments'])-1 and distance<.030 and heading<math.radians(10)
    if action=='stop' and arrived:
     w.step(standing=True);self.settle+=DT
     if self.settle>.55:
      distance=math.dist(w.d.qpos[:2],leg['goal'][:2]);heading=abs(wrap(leg['goal'][2]-w.yaw()))
      h=leg['goal'][2];R=np.array([[math.cos(h),math.sin(h)],[-math.sin(h),math.cos(h)]]);drift=R@(w.d.qpos[:2]-stop_start);self.stop_trials.append({'t':float(w.d.time),'drift_body_m':drift.tolist(),'end_error_mm':distance*1000});self.stop_bias=np.clip(.5*self.stop_bias+.5*drift,[-.015,-.015],[.025,.025])
      if distance>(.004 if leg['task']=='alarm' else .010) or heading>math.radians(10):self.settle=0.;break
      self.arrivals.append({'station':leg['task'],'arrived':True,'t':float(w.d.time),'position_error_mm':distance*1000,'heading_error_degrees':math.degrees(heading),'travel_time_s':float(w.d.time)-self.leg_start});self.mode='task';break
    else:self.settle=0.;w.step(MOVES[action])
  else:
   task=leg['task'];w.decisions.append({'t':float(w.d.time),'observation':w.task_observation(task),'action':action});w.do_task(task,next(p for p in PROFILES if p.code==action));w.rest_arms();self.index+=1;self.segment=0;self.aligning=False;self.mode='walk';self.leg_start=float(w.d.time);self.settle=0.;w.walker.last=-1.;w.walker.action[:]=0;w.walker.velocity_integral[:]=0;w.walker.yaw_integral=0
  return self.status()
 def result(self):
  return {'seed':self.w.s['seed'],'mode':self.mode,'failure':self.failure,'arrivals':self.arrivals,'episode':self.w.episode(),'route_version':self.route['version'],'path_trace':self.path_trace,'stop_trials':self.stop_trials,'physics_calls':self.calls,'duration_wall_s':time.perf_counter()-self.start}

def fixed_sequence(route,seed,record=True,profiles=None):
 profiles=profiles or {'alarm':'B','drawer':'A','laptop':'B','globe':'A'}
 r=PathRunner(route);status=r.reset(seed,record)
 for _ in range(1200):
  if status['mode']=='done':break
  obs=status['observation'];action=teacher(obs) if obs['domain']=='walk' else profiles[obs['domain']];status=r.advance(action)
 return r.result()

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=19000);p.add_argument('--route',default='mochi/configs/desk-route-v1.json');a=p.parse_args();r=fixed_sequence(json.loads(Path(a.route).read_text()),a.seed);out=Path('mochi/artifacts/planning');out.mkdir(parents=True,exist_ok=True);(out/f'fixed-{a.seed}.json').write_text(json.dumps(r,separators=(',',':')));print(json.dumps({'arrivals':r['arrivals'],'failure':r['failure'],'tasks':{k:v['success'] for k,v in r['episode']['results'].items()},'duration':r['episode']['duration'],'fall':r['episode']['fall']},indent=2))
