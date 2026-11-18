"""One continuous physical world with model-owned recovery choices."""
import math,time
from ..planning.follower import PathRunner,teacher
from ..curriculum.world import PROFILES
from .manipulation import ControlWorld,PRESSES
from .recovery import RECOVERIES,recover,observation as recovery_observation

class ControlRunner(PathRunner):
 def __init__(self,route):super().__init__(route,ControlWorld);self.recovery_snapshots=[]
 def status(self):
  if self.w.fall or self.index>=len(self.route['legs']) or self.mode=='walk' and self.w.d.time-self.leg_start>35:
   self.failure='fall' if self.w.fall else 'leg_timeout' if self.index<len(self.route['legs']) else None;self.mode='done';return {'mode':'done','failure':self.failure}
  task=self.route['legs'][self.index]['task'];obs=self.observation() if self.mode=='walk' else self.w.task_observation(task) if self.mode=='task' else recovery_observation(self.w,task)
  return {'mode':self.mode,'station':task,'observation':obs}
 def advance(self,action):
  if self.mode=='walk':return super().advance(action)
  w=self.w;task=self.route['legs'][self.index]['task'];self.calls+=1
  if self.mode=='task':
   obs=w.task_observation(task);w.decisions.append({'t':float(w.d.time),'observation':obs,'action':action});p=next(p for p in (PRESSES if task=='laptop' else PROFILES) if p.code==action);w.do_task(task,p);self.mode='recovery'
  else:
   obs=recovery_observation(w,task);w.decisions.append({'t':float(w.d.time),'observation':obs,'action':action});result=recover(w,task,next(p for p in RECOVERIES if p.code==action))
   if not result['success']:self.mode='done';self.failure='recovery_invalid';return {'mode':'done','failure':self.failure}
   self.index+=1;self.segment=0;self.aligning=False;self.mode='walk';self.leg_start=float(w.d.time);self.settle=0.;w.walker.last=-1.;w.walker.action[:]=0;w.walker.velocity_integral[:]=0;w.walker.yaw_integral=0
  return self.status()

def fixed_sequence(route,seed,record=True,profiles=None,recoveries=None):
 profiles=profiles or {'alarm':'B','drawer':'A','laptop':'P1','globe':'A'};recoveries=recoveries or {t:('R1' if t=='alarm' else 'R0') for t in profiles};r=ControlRunner(route);s=r.reset(seed,record)
 for _ in range(1400):
  if s['mode']=='done':break
  obs=s['observation'];action=teacher(obs) if s['mode']=='walk' else profiles[s['station']] if s['mode']=='task' else recoveries[s['station']];s=r.advance(action)
 return r.result()
