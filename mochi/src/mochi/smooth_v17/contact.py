"""Experimental edge-normal preload plus hinge-closing tangential force.

Same force cap, contact geometry, dwell and object-success verifier as V16.
This is controller engineering, not a trained native manipulation network.
"""
import math
from dataclasses import asdict
import mujoco
import numpy as np
from ..curriculum.world import DT
from ..control_v8.manipulation import approach_points,lid_target
from ..control_v8.verification import laptop_good,task_valid

def directed_laptop(self,p,horizon,radial=.8,tangential=.6):
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
   surface,normal=lid_target(a,p.radius,p.contact_x,0.);J=np.zeros((3,self.m.nv));mujoco.mj_jacSite(self.m,self.d,J,None,arm['tip']);velocity=J@self.d.qvel;tangent=np.eye(3)-np.outer(normal,normal);error=tangent@(surface-self.d.site_xpos[arm['tip']]);active=(float(self.d.time)-push_start)%(p.pulse_on+p.pulse_off)<p.pulse_on;ramp=min(1.,(float(self.d.time)-push_start)/.3);press=p.force*ramp if active else .04;feet=np.mean([self.d.xpos[self.id('body',s+'_ankle_roll_link')] for s in ['left','right']],axis=0);horizontal=float(np.clip((surface[1]-feet[1])/max(surface[2],.06),-.1,.4));edge=np.array([0.,-math.cos(a),math.sin(a)]);closing=np.array([0.,-math.sin(a),-math.cos(a)]);F=(-radial*edge+tangential*closing)*press+8*error-.5*velocity;Ja=J[:,arm['vs']];inverse=Ja.T@np.linalg.inv(Ja@Ja.T+np.eye(3)*8e-8);N=np.eye(7)-inverse@Ja;tau=Ja.T@F+N.T@(.15*(posture-self.d.qpos[arm['qs']])-.01*self.d.qvel[arm['vs']]);kp=self.m.actuator_gainprm[arm['acts'],0];kv=-self.m.actuator_biasprm[arm['acts'],2];self.d.ctrl[arm['acts']]=np.clip(self.d.qpos[arm['qs']]+(tau+kv*self.d.qvel[arm['vs']])/kp,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
  # Actuator feedback at the physics rate; never clamps contact forces or
  # changes object state. It releases elastic preload when measured force rises.
  if force>.65:
   _,outward=lid_target(a,p.radius,p.contact_x,0);J=np.zeros((3,self.m.nv));mujoco.mj_jacSite(self.m,self.d,J,None,arm['tip']);J=J[:,arm['vs']];dq=J.T@np.linalg.solve(J@J.T+np.eye(3)*8e-8,outward*.00015);self.d.ctrl[arm['acts']]=np.clip(self.d.qpos[arm['qs']]+dq,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
  self.step(standing=True)
  speed=float(self.d.qvel[self.v['laptop']]);good=laptop_good(self.value('laptop'),speed,self.progress_contact);dwell=dwell+DT if self.phase=='release' and good else 0.
  if dwell>.35:break
  if self.max_force>.8:abort='force_limit';break
 result={'task':'laptop','success':task_valid(dwell,self.hand_contacts,self.bad_contacts,self.fall,self.max_force),'value':self.value('laptop'),'duration':float(self.d.time)-self.t0,'contacts':self.hand_contacts,'non_hand_contact_steps':self.bad_contacts,'max_force_n':self.max_force,'fall':self.fall,'max_tilt_deg':math.degrees(self.max_tilt),'profile':asdict(p),'phase':self.phase,'contact_progress':self.progress_contact,'abort':abort,'approach_stage':approach_stage,'final_tip':self.d.site_xpos[arm['tip']].tolist(),'final_target':target.tolist()};self.results['laptop']=result;self.events.append({**result,'t':float(self.d.time)});return result
