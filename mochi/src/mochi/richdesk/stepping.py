"""Contact-gated, quasistatic biped references tracked by joint torques.

World-space foot targets are references only. The floating base and physical
feet are never repositioned; gravity, contact, friction and actuator limits
determine whether the plan works.
"""
from dataclasses import dataclass,asdict
import math
import mujoco
import numpy as np

from ..curriculum.locomotion import KP,KD,DEFAULT


@dataclass(frozen=True)
class StepParameters:
    stride:float=.034
    lift:float=.014
    shift_seconds:float=.65
    swing_seconds:float=.52
    landing_seconds:float=.18
    kp_multiplier:float=6.
    kd_multiplier:float=6.
    com_margin:float=.004
    shift_fraction:float=1.
    com_tracking:float=.5
    velocity_damping:float=.08
    torso_gain:float=.1
    angular_damping:float=.008
    crouch:float=.006
    ground_force_gain:float=1.
    stance_gain:float=.5
    attitude_gain:float=.06
    support_forward:float=.004


def ease(t):
    t=float(np.clip(t,0,1));return t*t*t*(10+t*(-15+6*t))


class FootstepController:
    label='contact-gated-biped-reference-controller'

    def __init__(self,world,parameters=None):
        w=world;old=w.walker;self.w=w;self.m=w.m;self.d=w.d;self.p=parameters or StepParameters()
        for name in ['qids','vids','aids','offsets','scale','time_scale']:setattr(self,name,getattr(old,name))
        self.last=-1.;self.action=np.zeros(12);self.velocity_integral=np.zeros(2);self.yaw_integral=0.
        self.scratch=mujoco.MjData(self.m);self.feet=[w.id('body',s+'_ankle_roll_link') for s in ['left','right']]
        self.local=np.array([.005,0,-.00585]);self.anchors=None;self.stage='initialize';self.stage_t=0.
        self.swing=0;self.steps=0;self.target=self.d.qpos[self.qids].copy();self.joint_target=self.target.copy()
        self.phase_log=[];self.last_velocity=np.zeros(3);self.failed_reason=None
        self.previous_com=None;self.previous_com_time=None;self.com_velocity=np.zeros(3)
        self.limits=self.m.jnt_range[[w.id('joint',n) for n in __import__('mochi.curriculum.locomotion',fromlist=['LEGS']).LEGS]]

    def foot(self,i):
        b=self.feet[i];return self.d.xpos[b]+self.d.xmat[b].reshape(3,3)@self.local

    def begin(self,velocity):
        self.anchors=[self.foot(i).copy() for i in [0,1]]
        self.yaw=self.w.yaw();self.body_z=float(self.d.qpos[2]);self.root_start=self.d.qpos[:3].copy()
        self.com_offset=self.d.xmat[1].reshape(3,3).T@(self.d.subtree_com[1]-self.d.qpos[:3])
        self.com_target=self.d.subtree_com[1].copy()
        self.base_clearance=self.body_z-float(np.mean([p[2] for p in self.anchors]))-self.p.crouch
        self.swing=0;self.start_shift(velocity)

    def start_shift(self,velocity):
        self.stage='shift';self.stage_t=float(self.d.time);self.root_start=self.d.qpos[:3].copy()
        self.com_start=self.d.subtree_com[1].copy()
        self.yaw_start=self.w.yaw();self.yaw_goal=self.yaw_start+float(np.clip(velocity[2]*.5,-.18,.18))
        c,s=math.cos(self.yaw_goal),math.sin(self.yaw_goal);self.rotation=np.array([[c,-s,0],[s,c,0],[0,0,1]])
        stance=1-self.swing;center=np.mean(self.anchors,axis=0)*(1-self.p.shift_fraction)+self.anchors[stance]*self.p.shift_fraction
        center[:2]+=self.rotation[:2,:2]@np.array([self.p.support_forward,0.])
        self.root_goal=center-self.rotation@self.com_offset
        self.root_goal[2]=self.base_clearance+self.anchors[stance][2]
        # Account for the leg mass moving during crouch, rather than treating
        # the center of mass as a fixed offset from the pelvis.
        for _ in range(3):
            self.solve(self.root_goal,self.anchors,self.yaw_goal)
            mujoco.mj_forward(self.m,self.scratch)
            self.root_goal[:2]+=np.clip(center[:2]-self.scratch.subtree_com[1,:2],-.005,.005)
        self.com_goal=self.scratch.subtree_com[1].copy();self.com_goal[:2]=center[:2]
        self.swing_start=self.anchors[self.swing].copy()
        centerfeet=np.mean(self.anchors,axis=0)
        direction=np.asarray(velocity[:2]);norm=float(np.linalg.norm(direction))
        direction=direction/max(norm,1e-8)
        stride=self.p.stride*min(1.,norm/.025)
        lateral=np.array([0,.0198 if self.swing==0 else -.0198,0.])
        self.swing_goal=centerfeet+self.rotation@lateral+self.rotation@np.r_[direction*stride,0.]
        self.swing_goal[2]=self.w.terrain_height(*self.swing_goal[:2],margin=.001)-.00015
        self.phase_log.append({'t':float(self.d.time),'phase':self.stage,'swing':['left','right'][self.swing],'target':self.swing_goal.tolist()})

    def solve(self,root,feet,yaw):
        m=self.m;d=self.scratch;d.qpos[:]=self.d.qpos
        d.qpos[:3]=root;d.qpos[3:7]=[math.cos(yaw/2),0,0,math.sin(yaw/2)]
        d.qpos[self.qids]=self.joint_target
        c,s=math.cos(yaw),math.sin(yaw);orientation=np.array([[c,-s,0],[s,c,0],[0,0,1]])
        for _ in range(7):
            mujoco.mj_forward(m,d)
            for i,b in enumerate(self.feet):
                R=d.xmat[b].reshape(3,3);point=d.xpos[b]+R@self.local
                error=feet[i]-point;rot=.5*sum((np.cross(R[:,j],orientation[:,j]) for j in range(3)),np.zeros(3))
                J=np.zeros((3,m.nv));Jr=np.zeros_like(J);mujoco.mj_jac(m,d,J,Jr,point,b)
                ids=np.arange(i*6,(i+1)*6);qs=self.qids[ids];vs=self.vids[ids]
                A=np.vstack([J[:,vs],Jr[:,vs]*.03]);e=np.r_[error,rot*.03]
                dq=A.T@np.linalg.solve(A@A.T+np.eye(6)*2e-8,e)
                d.qpos[qs]=np.clip(d.qpos[qs]+np.clip(dq,-.12,.12),self.limits[ids,0]+.002,self.limits[ids,1]-.002)
        return d.qpos[self.qids].copy()

    def command(self,velocity):
        d=self.d;p=self.p;v=np.array(velocity,dtype=float)
        if self.anchors is None:self.begin(v)
        if d.time-self.last>=.008:
            self.last=float(d.time);age=float(d.time)-self.stage_t;stance=1-self.swing
            feet=[x.copy() for x in self.anchors];yaw=self.yaw_goal
            if self.stage=='shift':
                u=ease(age/p.shift_seconds);root=(1-u)*self.root_start+u*self.root_goal;yaw=(1-u)*self.yaw_start+u*self.yaw_goal
                self.com_target=(1-u)*self.com_start+u*self.com_goal
                actual=self.d.subtree_com[1][:2]+self.d.qvel[:2]*math.sqrt(max(.05,float(self.d.subtree_com[1,2]))/9.81)
                inside=(np.max(np.abs((actual-self.com_goal[:2])))<p.com_margin
                        and np.linalg.norm(self.d.qvel[3:5])<.25
                        and np.linalg.norm(self.com_velocity[:2])<.008)
                if age>p.shift_seconds and inside:
                    self.stage='swing';self.stage_t=float(d.time)
                    self.phase_log.append({'t':float(d.time),'phase':'swing','swing':['left','right'][self.swing]})
                elif age>2.5:self.failed_reason='support_transfer_not_stable'
            elif self.stage=='swing':
                self.com_target=self.com_goal.copy()
                u=float(np.clip(age/p.swing_seconds,0,1));a=ease(u);root=self.root_goal.copy()
                feet[self.swing]=(1-a)*self.swing_start+a*self.swing_goal
                clearance=max(self.swing_start[2],self.swing_goal[2])+p.lift
                feet[self.swing][2]=(1-a)*self.swing_start[2]+a*self.swing_goal[2]+(clearance-max(self.swing_start[2],self.swing_goal[2]))*math.sin(math.pi*u)**2
                if u>=1:
                    self.stage='land';self.stage_t=float(d.time)
                    self.phase_log.append({'t':float(d.time),'phase':'land','swing':['left','right'][self.swing]})
            else:
                self.com_target=self.com_goal.copy()
                root=self.root_goal.copy();feet[self.swing]=self.swing_goal.copy()
                contact=self.w.foot_touching(['left','right'][self.swing])
                if age>p.landing_seconds and contact and np.linalg.norm(self.foot(self.swing)-self.swing_goal)<.007:
                    self.anchors[self.swing]=self.foot(self.swing).copy();self.steps+=1;self.swing=1-self.swing;self.start_shift(v)
                elif age>1.2:self.failed_reason='touchdown_not_confirmed'
            # Measured velocity damps the support transfer; the reference itself
            # acts only by changing the leg joint targets.
            if self.previous_com is not None:
                measured=(d.subtree_com[1]-self.previous_com)/max(float(d.time)-self.previous_com_time,.001)
                self.com_velocity=.6*self.com_velocity+.4*measured
            self.previous_com=d.subtree_com[1].copy();self.previous_com_time=float(d.time)
            root[:2]+=np.clip(p.com_tracking*(self.com_target[:2]-self.d.subtree_com[1,:2])-self.d.qvel[:2]*p.velocity_damping,-.012,.012)
            self.joint_target=self.solve(root,feet,yaw)
            self.target=self.joint_target.copy()
        position_gain=np.full(12,p.stance_gain);damping_gain=np.ones(12)
        if self.stage in ['swing','land']:
            position_gain[self.swing*6:(self.swing+1)*6]=p.kp_multiplier
            damping_gain[self.swing*6:(self.swing+1)*6]=p.kd_multiplier
        tau=(self.target-d.qpos[self.qids])*KP*self.scale**4*position_gain-d.qvel[self.vids]*KD*self.scale**4.5*damping_gain+d.qfrc_bias[self.vids]
        R=d.xmat[1].reshape(3,3);pitch=math.asin(float(np.clip(-R[2,0],-1,1)));roll=math.atan2(R[2,1],R[2,2])
        error=R.T@(d.subtree_com[1]-self.com_target);mass=float(self.m.body_subtreemass[1]);omega=d.qvel[3:6]
        for i in [4,10]:tau[i]+=mass*9.81*error[0]/2+p.torso_gain*pitch+p.angular_damping*omega[1]
        for i in [5,11]:tau[i]+=-mass*9.81*error[1]/2+p.torso_gain*roll+p.angular_damping*omega[0]
        force=mass*(np.array([0.,0.,9.81])+80*(self.com_target-d.subtree_com[1])-15*self.com_velocity)
        force[2]=np.clip(force[2],mass*9.81*.3,mass*9.81*1.7)
        force[:2]=np.clip(force[:2],-force[2]*.6,force[2]*.6)
        if self.stage in ['swing','land']:weights=[float(i!=self.swing) for i in range(2)]
        else:
            axis=self.anchors[1][:2]-self.anchors[0][:2]
            cop=d.subtree_com[1,:2]-(d.subtree_com[1,2]-np.mean(self.anchors,axis=0)[2])*force[:2]/force[2]
            right=float(np.clip(np.dot(cop-self.anchors[0][:2],axis)/max(np.dot(axis,axis),1e-8),.03,.97))
            weights=[1-right,right]
        desiredR=self.rotation
        orient=.5*sum((np.cross(R[:,j],desiredR[:,j]) for j in range(3)),np.zeros(3))
        moment=p.attitude_gain*orient-.008*(R@d.qvel[3:6])
        for i in range(2):moment-=np.cross(self.foot(i)-d.subtree_com[1],force*weights[i])
        for i,b in enumerate(self.feet):
            J=np.zeros((3,self.m.nv));Jr=np.zeros_like(J);mujoco.mj_jac(self.m,d,J,Jr,self.foot(i),b)
            ids=np.arange(i*6,(i+1)*6)
            tau[ids]-=p.ground_force_gain*J[:,self.vids[ids]].T@(force*weights[i])
            bounds=np.array([.0045,.013,.009])*force[2]*weights[i]
            localmoment=np.clip(self.rotation.T@(moment*weights[i]),-bounds,bounds)
            tau[ids]-=Jr[:,self.vids[ids]].T@(self.rotation@localmoment)
        d.ctrl[self.aids]=tau

    def description(self):
        return {'controller':self.label,'parameters':asdict(self.p),'steps':self.steps,
                'phase_log':self.phase_log,'failure':self.failed_reason,'neural_training':False}
