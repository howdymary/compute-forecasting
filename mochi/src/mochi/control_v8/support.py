"""Engineering variant: align laptop press reaction with the foot support center.

The original V8 controller is unchanged. This adds an X-axis actuator torque
component, complementing its existing Y component. No base force is applied.
"""
import math
import mujoco,numpy as np
from .manipulation import ControlWorld,lid_target
from .runner import ControlRunner
def lateral_factor(surface,feet):
 return float(np.clip((feet[0]-surface[0])/max(surface[2],.06),-.5,.5))
class SupportWorld(ControlWorld):
 def __init__(self,*args,**kwargs):
  self.support_press=None;self.support_push_start=None;self.support_peak_x=0.;super().__init__(*args,**kwargs)
 def laptop(self,p,horizon):
  self.support_press=p;self.support_push_start=None;self.support_peak_x=0.
  try:
   result=super().laptop(p,horizon);result['support_x_peak_n']=self.support_peak_x;return result
  finally:self.support_press=None
 def step(self,*args,**kwargs):
  if getattr(self,'support_press',None) is not None and self.task=='laptop' and self.phase=='push':
   if self.support_push_start is None:self.support_push_start=float(self.d.time)
   contact,force,_=self.contacts('laptop')
   if contact and force<.65:
    p=self.support_press;elapsed=float(self.d.time)-self.support_push_start;active=elapsed%(p.pulse_on+p.pulse_off)<p.pulse_on;press=p.force*min(1.,elapsed/.3) if active else .04;surface,_=lid_target(self.value('laptop'),p.radius,p.contact_x,0.);feet=np.mean([self.d.xpos[self.id('body',side+'_ankle_roll_link')] for side in ['left','right']],axis=0);fx=lateral_factor(surface,feet)*press;self.support_peak_x=max(self.support_peak_x,abs(fx));arm=self.arm['left'];J=np.zeros((3,self.m.nv));mujoco.mj_jacSite(self.m,self.d,J,None,arm['tip']);delta=J[0,arm['vs']]*fx/self.m.actuator_gainprm[arm['acts'],0];self.d.ctrl[arm['acts']]=np.clip(self.d.ctrl[arm['acts']]+delta,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
  super().step(*args,**kwargs)
 def episode(self):return {**super().episode(),'controller_revision':'xy-support-v1'}
class SupportRunner(ControlRunner):
 def __init__(self,route):super().__init__(route);self.world_class=SupportWorld
