"""Force-limited absolute-IK contact references; unchanged robot and physics."""
from dataclasses import dataclass,asdict
import math
import mujoco,numpy as np
from ..curriculum.world import World,DT,PAD_RADIUS,PROFILES
from .verification import laptop_good,task_valid

@dataclass(frozen=True)
class Press:
 code:str;force:float;radius:float;contact_x:float;pulse_on:float;pulse_off:float;slew:float
 release_degrees:float=56.
PRESSES=[Press('P0',.45,.15,.263,10,0,.012),Press('P1',.50,.15,.263,10,0,.012),Press('P2',.55,.15,.263,10,0,.012),Press('P3',.50,.15,.263,.30,.15,.012)]

def lid_target(angle,radius,x,offset):
 # Contact the actual upper edge, rather than sliding down the rear face.
 normal=np.array([0.,-math.cos(angle),math.sin(angle)]);return np.array([x,.249-radius*math.cos(angle),.0185+radius*math.sin(angle)])+normal*(PAD_RADIUS+offset),normal

def approach_points(world,p,angle):
 hover,normal=lid_target(angle,p.radius,p.contact_x,.014);rotation=world.d.xmat[1].reshape(3,3);outside=world.d.qpos[:3]+rotation@np.array([.03,.035,0.]);outside[2]=.19
 return [outside,hover],normal

class ControlWorld(World):
 def __init__(self,*a,**kw):
  self.approach_side='right';self.control_telemetry=[];self.next_telemetry=0.;self.recoveries=[];super().__init__(*a,**kw)
 def step(self,*a,**kw):
  super().step(*a,**kw)
  if self.d.time>=self.next_telemetry:
   self.next_telemetry=float(self.d.time)+.02
   self.control_telemetry.append({'t':float(self.d.time),'phase':self.phase,'task':self.task,'q':{s:self.d.qpos[a['qs']].tolist() for s,a in self.arm.items()},'qd':{s:self.d.qvel[a['vs']].tolist() for s,a in self.arm.items()},'ctrl':{s:self.d.ctrl[a['acts']].tolist() for s,a in self.arm.items()},'tips':{s:self.d.site_xpos[a['tip']].tolist() for s,a in self.arm.items()},'contact_force':self.contacts(self.task)[1] if self.task else 0.})
 def do_task(self,t,profile=None,max_seconds=None):
  if t!='laptop':return super().do_task(t,profile,max_seconds)
  p=profile or PRESSES[0];return self.laptop(p,max_seconds or 12.)
 def laptop(self,p,horizon):
  self.task='laptop';self.approach_side='left';self.approach_path=[];self.phase='approach';self.t0=float(self.d.time);self.hand_contacts=0;self.max_force=0.;self.bad_contacts=0;self.progress_contact=0.;first_angle=None;arm=self.arm['left'];qtarget=self.d.qpos[arm['qs']].copy();next_control=-1.;next_ik=-1.;dwell=0.;push_start=None;release_point=None;release_normal=None;abort=None;approach_stage=0;posture=None
  while self.d.time-self.t0<horizon and not self.fall:
   elapsed=float(self.d.time)-self.t0;contact,force,bad=self.contacts('laptop');self.hand_contacts+=int(contact);self.max_force=max(self.max_force,force);self.bad_contacts+=int(bad);a=self.value('laptop')
   if contact and first_angle is None:first_angle=a
   self.progress_contact=0. if first_angle is None else max(0.,first_angle-a)
   if self.phase=='approach':
    waypoints,normal=approach_points(self,p,a);target=waypoints[min(approach_stage,1)]
    if np.linalg.norm(self.d.site_xpos[arm['tip']]-target)<.010:
     if approach_stage<1:approach_stage+=1
     else:self.phase='push';push_start=float(self.d.time);posture=self.d.qpos[arm['qs']].copy()
   if self.phase=='push' and a<math.radians(p.release_degrees):
    self.phase='release';release_point=self.d.site_xpos[arm['tip']].copy();_,release_normal=lid_target(a,p.radius,p.contact_x,0)
   if self.d.time>=next_control:
    if self.phase=='push':target,normal=lid_target(a,p.radius,p.contact_x,0.)
    elif self.phase=='release':target=release_point+release_normal*.018;normal=release_normal
    else:
     waypoints,normal=approach_points(self,p,a);target=waypoints[min(approach_stage,1)]
    if self.phase!='push':
     if self.d.time>=next_ik:qtarget=self.ik('left',target,normal,from_home=True);next_ik=float(self.d.time)+.06
     change=qtarget-self.d.ctrl[arm['acts']];change*=min(1.,p.slew/max(float(np.max(np.abs(change))),1e-8));self.d.ctrl[arm['acts']]=np.clip(self.d.ctrl[arm['acts']]+change,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
    elif not contact:
     seek,normal=lid_target(a,p.radius,p.contact_x,-.0003);delta=seek-self.d.site_xpos[arm['tip']];delta*=min(1.,.0004/max(float(np.linalg.norm(delta)),1e-9));J=np.zeros((3,self.m.nv));mujoco.mj_jacSite(self.m,self.d,J,None,arm['tip']);J=J[:,arm['vs']];dq=J.T@np.linalg.solve(J@J.T+np.eye(3)*8e-8,delta);self.d.ctrl[arm['acts']]=np.clip(self.d.qpos[arm['qs']]+dq,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
    next_control=float(self.d.time)+.02
   if self.phase=='push' and contact:
    surface,normal=lid_target(a,p.radius,p.contact_x,0.);J=np.zeros((3,self.m.nv));mujoco.mj_jacSite(self.m,self.d,J,None,arm['tip']);velocity=J@self.d.qvel;tangent=np.eye(3)-np.outer(normal,normal);error=tangent@(surface-self.d.site_xpos[arm['tip']]);active=(float(self.d.time)-push_start)%(p.pulse_on+p.pulse_off)<p.pulse_on;ramp=min(1.,(float(self.d.time)-push_start)/.3);press=p.force*ramp if active else .04;feet=np.mean([self.d.xpos[self.id('body',s+'_ankle_roll_link')] for s in ['left','right']],axis=0);horizontal=float(np.clip((surface[1]-feet[1])/max(surface[2],.06),-.1,.4));F=np.array([0.,-horizontal,-1.])*press+8*error-.5*velocity;Ja=J[:,arm['vs']];inverse=Ja.T@np.linalg.inv(Ja@Ja.T+np.eye(3)*8e-8);N=np.eye(7)-inverse@Ja;tau=Ja.T@F+N.T@(.15*(posture-self.d.qpos[arm['qs']])-.01*self.d.qvel[arm['vs']]);kp=self.m.actuator_gainprm[arm['acts'],0];kv=-self.m.actuator_biasprm[arm['acts'],2];self.d.ctrl[arm['acts']]=np.clip(self.d.qpos[arm['qs']]+(tau+kv*self.d.qvel[arm['vs']])/kp,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
   # Actuator feedback at the physics rate; never clamps contact forces or
   # changes object state. It releases elastic preload when measured force rises.
   if force>.65:
    _,outward=lid_target(a,p.radius,p.contact_x,0);J=np.zeros((3,self.m.nv));mujoco.mj_jacSite(self.m,self.d,J,None,arm['tip']);J=J[:,arm['vs']];dq=J.T@np.linalg.solve(J@J.T+np.eye(3)*8e-8,outward*.00015);self.d.ctrl[arm['acts']]=np.clip(self.d.qpos[arm['qs']]+dq,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
   self.step(standing=True)
   speed=float(self.d.qvel[self.v['laptop']]);good=laptop_good(self.value('laptop'),speed,self.progress_contact);dwell=dwell+DT if self.phase=='release' and good else 0.
   if dwell>.35:break
   if self.max_force>.8:abort='force_limit';break
  result={'task':'laptop','success':task_valid(dwell,self.hand_contacts,self.bad_contacts,self.fall,self.max_force),'value':self.value('laptop'),'duration':float(self.d.time)-self.t0,'contacts':self.hand_contacts,'non_hand_contact_steps':self.bad_contacts,'max_force_n':self.max_force,'fall':self.fall,'max_tilt_deg':math.degrees(self.max_tilt),'profile':asdict(p),'phase':self.phase,'contact_progress':self.progress_contact,'abort':abort,'approach_stage':approach_stage,'final_tip':self.d.site_xpos[arm['tip']].tolist(),'final_target':target.tolist()};self.results['laptop']=result;self.events.append({**result,'t':float(self.d.time)});return result
 def episode(self):
  return {**super().episode(),'control_telemetry':self.control_telemetry,'recoveries':self.recoveries}
