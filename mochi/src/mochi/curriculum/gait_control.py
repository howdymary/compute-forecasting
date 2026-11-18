"""Explicit bounded gait modulation; the native neural gait weights stay fixed.

Profiles change the phase clock supplied to the native policy and slew-limit
its requested velocity. Only actuator torques move the robot. All values must
be frozen before any model is trained to select these profiles.
"""
from dataclasses import dataclass,asdict
import math
import numpy as np
import torch
from .locomotion import Walker,DEFAULT,KP,KD,CFG

@dataclass(frozen=True)
class GaitProfile:
    name: str
    cadence: float
    linear_acceleration: float
    angular_acceleration: float

GAITS={p.name:p for p in [
    GaitProfile('native',1.,1e6,1e6),
    GaitProfile('smooth',.90,.14,1.8),
    GaitProfile('steady',1.,.24,3.0),
    GaitProfile('brisk',1.05,.20,2.4),
    GaitProfile('measured',1.,.30,1.8),
]}

def slew(current,target,limit,dt):
    change=np.asarray(target,dtype=float)-current
    distance=float(np.linalg.norm(change))
    return current+change*(min(1.,limit*dt/distance) if distance else 1.)

class ModulatedWalker(Walker):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.gait=GAITS['native'];self.filtered=np.zeros(3);self.phase_clock=0.;self.clock_time=float(self.d.time)
    def set_gait(self,name):
        self.gait=GAITS[name]
    def command(self,velocity):
        # The native mode is a genuine original-controller ablation.
        if self.gait.name=='native':
            self.phase_clock=(float(self.d.time)/self.time_scale)% .8
            self.clock_time=float(self.d.time);self.filtered[:]=velocity
            return super().command(velocity)
        m,d=self.m,self.d
        if d.time-self.last>=.02*self.time_scale-1e-9:
            elapsed=min(.03*self.time_scale,max(float(d.time)-self.clock_time,float(m.opt.timestep)))
            self.phase_clock=(self.phase_clock+elapsed*self.gait.cadence/self.time_scale)% .8
            self.clock_time=float(d.time);self.last=float(d.time)
            self.filtered[:2]=slew(self.filtered[:2],velocity[:2],self.gait.linear_acceleration,elapsed)
            self.filtered[2]=float(slew(np.array([self.filtered[2]]),[velocity[2]],self.gait.angular_acceleration,elapsed)[0])
            w,x,y,z=d.qpos[3:7]
            gravity=np.array([2*(-z*x+w*y),-2*(z*y+w*x),1-2*(w*w+z*z)])
            desired=self.filtered.copy()
            if self.velocity_feedback:
                actual=d.xmat[1].reshape(3,3).T@d.qvel[:3];error=desired[:2]-actual[:2]
                self.velocity_integral=np.clip(self.velocity_integral+error*.02*self.time_scale,-.025,.025)
                desired[:2]=np.clip(desired[:2]+.7*error+1.4*self.velocity_integral,-.12,.12)
                yaw_error=desired[2]-d.qvel[5]
                self.yaw_integral=float(np.clip(self.yaw_integral+yaw_error*.02*self.time_scale,-.25,.25))
                desired[2]=float(np.clip(desired[2]+.35*yaw_error+.4*self.yaw_integral,-1.8,1.8))
            phase=self.phase_clock/.8
            obs=np.r_[d.qvel[3:6]*self.time_scale*.25,gravity,desired*np.array([1/self.time_scale,1/self.time_scale,self.time_scale])*np.array(CFG['cmd_scale']),d.qpos[self.qids]+self.offsets-DEFAULT,d.qvel[self.vids]*self.time_scale*.05,self.action,[math.sin(2*math.pi*phase),math.cos(2*math.pi*phase)]].astype(np.float32)
            with torch.no_grad():self.action=self.policy(torch.from_numpy(obs)[None]).numpy().reshape(12)
            self.target=self.action*.25+DEFAULT-self.offsets
        self.d.ctrl[self.aids]=(self.target-d.qpos[self.qids])*KP*self.scale**4-d.qvel[self.vids]*KD*self.scale**4.5

def install(world,gait='native'):
    old=world.walker
    world.walker=ModulatedWalker(world.m,world.d,old.scale,old.offsets,old.velocity_feedback)
    world.walker.set_gait(gait)
    return world.walker
