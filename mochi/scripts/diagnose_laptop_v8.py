"""Measure the existing laptop controller without modifying physics or control."""
import json,math
from pathlib import Path
import mujoco,numpy as np
from mochi.curriculum.world import World,PROFILES

class Diagnostic(World):
 def __init__(self,*a,**kw):self.trace=[];self.next_trace=0;super().__init__(*a,**kw)
 def step(self,*a,**kw):
  super().step(*a,**kw)
  if self.task!='laptop' or self.d.time<self.next_trace:return
  self.next_trace=float(self.d.time)+.05;arm=self.arm['left'];obj=self.object_geoms['laptop'];joint=self.joints['laptop'];origin=self.d.xanchor[joint];axis=self.d.xaxis[joint];torque=0;forces=[]
  for i,c in enumerate(self.d.contact):
   g1,g2=int(c.geom1),int(c.geom2)
   if obj not in [g1,g2]:continue
   other=g2 if g1==obj else g1
   if other not in self.hand_geoms['left']:continue
   f=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,f);world=c.frame.reshape(3,3).T@f[:3]*(1 if g2==obj else -1);tau=float(np.dot(np.cross(c.pos-origin,world),axis));torque+=tau;forces.append({'other':mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_GEOM,other),'normal':c.frame[:3].tolist(),'position':c.pos.tolist(),'force_world':world.tolist(),'closing_torque':tau})
  target,normal=self.hand_target('laptop',self.phase);v=self.v['laptop'];self.trace.append({'t':float(self.d.time),'phase':self.phase,'angle':self.value('laptop'),'angle_speed':float(-self.d.qvel[v]),'tip':self.d.site_xpos[arm['tip']].tolist(),'target':target.tolist(),'joint_positions':self.d.qpos[arm['qs']].tolist(),'joint_commands':self.d.ctrl[arm['acts']].tolist(),'joint_actuator_forces':self.d.actuator_force[arm['acts']].tolist(),'joint_constraint_forces':self.d.qfrc_constraint[arm['vs']].tolist(),'gravity_closing_torque':float(-self.d.qfrc_bias[v]),'hand_closing_torque':torque,'friction_loss':float(self.m.dof_frictionloss[v]),'hinge_constraint':float(self.d.qfrc_constraint[v]),'contacts':forces})

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=19000);p.add_argument('--profile',default='B');a=p.parse_args();w=Diagnostic(a.seed,start_task='laptop');result=w.do_task('laptop',next(p for p in PROFILES if p.code==a.profile));out=Path('mochi/artifacts/control-v8');out.mkdir(parents=True,exist_ok=True);(out/f'diagnosis-{a.seed}-{a.profile}.json').write_text(json.dumps({'result':result,'trace':w.trace},indent=2));rows=[x for x in w.trace if x['phase']=='push'];print(json.dumps({'result':result,'push_mean_gravity_torque':np.mean([x['gravity_closing_torque'] for x in rows]),'push_mean_contact_torque':np.mean([x['hand_closing_torque'] for x in rows]),'push_mean_force_world':np.mean([c['force_world'] for x in rows for c in x['contacts']],axis=0).tolist(),'end':w.trace[-1]},indent=2),flush=True)
