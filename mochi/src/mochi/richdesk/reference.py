"""Terrain-aware foot references through real joint actuators, not render poses.

The pinned gait network stays fixed. Smooth swing references and terrain height
residuals modify its joint targets through numerical IK and measured body state.
"""
from dataclasses import dataclass, asdict
import math

import mujoco
import numpy as np
import torch

from ..curriculum.locomotion import Walker, CFG, DEFAULT, KP, KD, LEGS


@dataclass(frozen=True)
class Parameters:
    lift: float = .008
    terrain_gain: float = 1.
    period: float = 0.
    preview: float = .10
    target_tau: float = .012
    command_acceleration: float = .6


class ReferenceWalker(Walker):
    label = 'native-network-with-actuated-foot-references'

    def __init__(self, m, d, scale, offsets, height, nominal_pelvis, parameters=None):
        super().__init__(m,d,scale,offsets)
        self.parameters = parameters or Parameters()
        self.height = height
        self.nominal_pelvis = nominal_pelvis
        self.scratch = mujoco.MjData(m)
        self.filtered = np.zeros(3)
        self.filtered_target = None
        self.previous_command_time = None
        self.feet = [mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,s+'_ankle_roll_link') for s in ['left','right']]
        self.previous_phase = [None,None]
        self.landing_height = [0.,0.]
        self.sole_local = np.array([.005,0,-.00585])
        self.limits = m.jnt_range[[mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,n) for n in LEGS]]
        self.support_level = 0.

    def command(self, velocity):
        m,d=self.m,self.d;p=self.parameters
        interval=.02*self.time_scale
        if d.time-self.last>=interval-1e-9:
            elapsed=interval if self.previous_command_time is None else float(d.time)-self.previous_command_time
            self.previous_command_time=float(d.time);self.last=float(d.time)
            wanted=np.array(velocity,dtype=float)
            self.filtered[:2]+=np.clip(wanted[:2]-self.filtered[:2],-p.command_acceleration*elapsed,p.command_acceleration*elapsed)
            self.filtered[2]+=float(np.clip(wanted[2]-self.filtered[2],-4*elapsed,4*elapsed))
            rotation=d.xmat[1].reshape(3,3);actual=rotation.T@d.qvel[:3]
            desired=self.filtered.copy();error=desired[:2]-actual[:2]
            self.velocity_integral=np.clip(self.velocity_integral+error*interval,-.025,.025)
            desired[:2]=np.clip(desired[:2]+.7*error+1.4*self.velocity_integral,-.12,.12)
            yaw_error=desired[2]-d.qvel[5];self.yaw_integral=float(np.clip(self.yaw_integral+yaw_error*interval,-.25,.25))
            desired[2]=float(np.clip(desired[2]+.35*yaw_error+.4*self.yaw_integral,-1.8,1.8))
            w,x,y,z=d.qpos[3:7]
            gravity=np.array([2*(-z*x+w*y),-2*(z*y+w*x),1-2*(w*w+z*z)])
            phase=float(d.time/(p.period or .8*self.time_scale)%1.)
            obs=np.r_[d.qvel[3:6]*self.time_scale*.25,gravity,
                desired*np.array([1/self.time_scale,1/self.time_scale,self.time_scale])*np.array(CFG['cmd_scale']),
                d.qpos[self.qids]+self.offsets-DEFAULT,d.qvel[self.vids]*self.time_scale*.05,
                self.action,[math.sin(2*math.pi*phase),math.cos(2*math.pi*phase)]].astype(np.float32)
            with torch.no_grad():self.action=self.policy(torch.from_numpy(obs)[None]).numpy().reshape(12)
            raw=self.action*.25+DEFAULT-self.offsets
            qref=raw.copy();levels=[];weights=[]
            for ci,c in enumerate(d.contact):
                a,b=int(m.geom_bodyid[int(c.geom1)]),int(m.geom_bodyid[int(c.geom2)])
                if (a in self.feet or b in self.feet) and abs(c.frame[2])>.7:
                    force=np.zeros(6);mujoco.mj_contactForce(m,d,ci,force)
                    if force[0]>.05:levels.append(max(0.,float(c.pos[2])));weights.append(force[0])
            if weights:self.support_level=float(np.average(levels,weights=weights))
            base_elevation=self.support_level
            moving=min(1.,float(np.linalg.norm(self.filtered[:2]))/.025+abs(self.filtered[2])/.4)
            for side,body in enumerate(self.feet):
                # Measured native gait: right swing in phase0..0.5, left in0.5..1.
                u=(phase-(.5 if side==0 else 0))%1.;swing=u<.5;progress=u/.5
                self.scratch.qpos[:]=d.qpos;self.scratch.qpos[self.qids]=raw
                mujoco.mj_forward(m,self.scratch)
                point=self.scratch.xpos[body]+self.scratch.xmat[body].reshape(3,3)@self.sole_local
                look=(rotation@np.r_[self.filtered[:2]*p.preview,0])[:2]
                ground=self.height(point[0]+look[0],point[1]+look[1],margin=.012)
                if swing:self.landing_height[side]=ground
                else:ground=self.landing_height[side]
                bump=p.lift*math.sin(math.pi*progress)**2 if swing else 0.
                dz=(p.terrain_gain*(ground-base_elevation)+bump)*moving
                dz=float(np.clip(dz,-.028,.035))
                if abs(dz)<1e-7:continue
                target=point+np.array([0,0,dz]);native_rotation=self.scratch.xmat[body].reshape(3,3).copy()
                ids=np.arange(side*6,(side+1)*6);qs=self.qids[ids];vs=self.vids[ids]
                for _ in range(4):
                    mujoco.mj_forward(m,self.scratch)
                    R=self.scratch.xmat[body].reshape(3,3)
                    point=self.scratch.xpos[body]+R@self.sole_local
                    orient=.5*sum((np.cross(R[:,j],native_rotation[:,j]) for j in range(3)),np.zeros(3))
                    J=np.zeros((3,m.nv));Jr=np.zeros_like(J);mujoco.mj_jac(m,self.scratch,J,Jr,point,body)
                    A=np.vstack([J[2,vs][None,:],Jr[:,vs]*.025]);e=np.r_[target[2]-point[2],orient*.025]
                    dq=A.T@np.linalg.solve(A@A.T+np.eye(4)*1e-7,e)
                    self.scratch.qpos[qs]+=np.clip(dq,-.12,.12)
                    self.scratch.qpos[qs]=np.clip(self.scratch.qpos[qs],raw[ids]-.55,raw[ids]+.55)
                qref[ids]=self.scratch.qpos[qs]
            if self.filtered_target is None:self.filtered_target=qref.copy()
            self.filtered_target+=(1-math.exp(-elapsed/max(p.target_tau,.0001)))*(qref-self.filtered_target)
            self.target=self.filtered_target.copy()
        self.d.ctrl[self.aids]=(self.target-d.qpos[self.qids])*KP*self.scale**4-d.qvel[self.vids]*KD*self.scale**4.5

    def description(self):
        return {'controller':self.label,'parameters':asdict(self.parameters),
            'native_weights_trained':False,'actuation':'Bounded IK residuals, joint PD torques; no base force or physical pose assignment.'}
