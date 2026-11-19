"""Floating-base whole-body balance with measured point-contact constraints.

Actuator-only execution; QP contact forces are predictions, never applied
external forces. Arm dynamics are eliminated using their actual servo effort.
"""
import math
import mujoco,numpy as np
from scipy import sparse
from scipy.linalg import qr
import osqp
from .contact import ContactWalker


class QpWalker(ContactWalker):
    label='contact-point-constrained-whole-body-controller'
    def __init__(self,*args,contact_gain=30.,foot_orientation_weight=20.,**kwargs):
        super().__init__(*args,**kwargs)
        self.qp_last=-1.;self.qp_torque=np.zeros(12);self.qp_log=[];self.qp_failures=[]
        self.qp_data=mujoco.MjData(self.m);self.previous_com_jac=None;self.previous_com_target=None;self.contact_gain=contact_gain
        self.previous_qp=None;self.foot_orientation_weight=foot_orientation_weight

    def servo(self):
        d=self.d;m=self.m
        if d.time-self.qp_last<.004:
            d.ctrl[self.aids]=self.qp_torque;return
        dt=max(.004,float(d.time)-self.qp_last);self.qp_last=float(d.time)
        s=self.qp_data;s.qpos[:]=d.qpos;s.qvel[:]=d.qvel;mujoco.mj_forward(m,s)
        M=np.empty((m.nv,m.nv));mujoco.mj_fullM(m,M,s.qM)
        ids=np.r_[np.arange(6),self.vids];arms=np.array(self.w.arm_dofs);h=s.qfrc_bias-s.qfrc_passive
        arm_effort=[]
        for side in ['left','right']:
            arm=self.w.arm[side];a=arm['acts'];v=arm['vs'];q=arm['qs']
            f=m.actuator_gainprm[a,0]*d.ctrl[a]+m.actuator_biasprm[a,0]+m.actuator_biasprm[a,1]*s.qpos[q]+m.actuator_biasprm[a,2]*s.qvel[v]
            arm_effort.extend(np.clip(f,m.actuator_forcerange[a,0],m.actuator_forcerange[a,1])+s.qfrc_bias[v])
        aa=M[np.ix_(arms,arms)];B=np.linalg.solve(aa,M[np.ix_(arms,ids)])
        constant=np.linalg.solve(aa,np.array(arm_effort)-h[arms]);ca=M[np.ix_(ids,arms)]
        mass=M[np.ix_(ids,ids)]-ca@B;bias=h[ids]+ca@constant
        contacts=[]
        exclude=self.swing if self.stage=='swing' and (not self.adaptive_swing or self.arc_start is None or d.time-self.arc_start<.9) else None
        for ci,c in enumerate(s.contact):
            a,b=int(c.geom1),int(c.geom2);other=b if a in self.w.support_geoms else a if b in self.w.support_geoms else -1
            if other<0 or abs(float(c.frame[2]))<.7:continue
            body=int(m.geom_bodyid[other])
            if body not in self.feet:continue
            foot=self.feet.index(body)
            if foot==exclude:continue
            f=np.zeros(6);mujoco.mj_contactForce(m,s,ci,f)
            if f[0]<=.0001:continue
            J=np.zeros((3,m.nv));Jd=np.zeros_like(J);mujoco.mj_jac(m,s,J,None,c.pos,body);mujoco.mj_jacDot(m,s,Jd,None,c.pos,body)
            R=s.xmat[body].reshape(3,3);point=s.xpos[body]+R@self.local
            anchor=self.swing_goal if self.stage=='land' and foot==self.swing else self.anchors[foot]
            # Constrain the loaded material points to stay still. A desired
            # flat-foot transform is a separate objective: imposing it on
            # these hard point constraints prevents rotation about a toe edge.
            acc=-self.contact_gain*(J@s.qvel)-Jd@s.qvel
            contacts.append((J[:,ids],acc,foot))
        if not contacts:
            self.qp_failures.append({'t':float(d.time),'reason':'no_support_contacts'});d.ctrl[self.aids]=self.qp_torque;return
        n=18;total=n+3*len(contacts);E=[];eb=[]
        row=np.zeros((6,total));row[:,:n]=mass[:6]
        for k,(J,_,_) in enumerate(contacts):row[:,n+3*k:n+3*k+3]=-J[:,:6].T
        E.extend(row);eb.extend(-bias[:6])
        # Several corners describe the same rigid foot. Keep independent
        # acceleration rows so small finite-rotation errors do not turn the
        # redundant constraints into an infeasible system.
        C=np.vstack([J for J,_,_ in contacts]);cb=np.concatenate([a for _,a,_ in contacts])
        _,R,pivots=qr(C.T,mode='economic',pivoting=True)
        rank=int(np.sum(abs(np.diag(R))>1e-7))
        for i in pivots[:rank]:
            row=np.zeros(total);row[:n]=C[i];E.append(row);eb.append(cb[i])
        objectives=[];targets=[]
        def task(J,value,weight):
            weights=np.broadcast_to(weight,(len(value),))
            A=np.zeros((len(value),total));A[:,:n]=J*weights[:,None];objectives.append(A);targets.append(np.asarray(value)*weights)
        J=np.zeros((3,m.nv));mujoco.mj_jacSubtreeCom(m,s,J,1)
        Jcom=J[:,ids]-J[:,arms]@B
        derivative=np.zeros_like(J) if self.previous_com_jac is None else (J-self.previous_com_jac)/dt
        self.previous_com_jac=J.copy()
        vref=np.zeros(3) if self.previous_com_target is None else np.clip((self.com_target-self.previous_com_target)/dt,-.06,.06)
        self.previous_com_target=self.com_target.copy()
        task(Jcom,120*(self.com_target-s.subtree_com[1])+22*(vref-J@s.qvel)-derivative@s.qvel-J[:,arms]@constant,35.)
        R=s.xmat[1].reshape(3,3);orient=.5*sum((np.cross(R[:,j],self.rotation[:,j]) for j in range(3)),np.zeros(3))
        Jr=np.zeros((3,m.nv));Jrd=np.zeros_like(Jr);mujoco.mj_jacBody(m,s,None,Jr,1);mujoco.mj_jacDot(m,s,None,Jrd,s.xpos[1],1)
        task(Jr[:,ids],180*orient-26*(Jr@s.qvel)-Jrd@s.qvel,8.)
        for i,body in enumerate(self.feet):
            if i==exclude:continue
            R=s.xmat[body].reshape(3,3);point=s.xpos[body]+R@self.local
            rot=.5*sum((np.cross(R[:,j],self.rotation[:,j]) for j in range(3)),np.zeros(3))
            J=np.zeros((3,m.nv));Jr=np.zeros_like(J);Jd=np.zeros_like(J);Jrd=np.zeros_like(J)
            mujoco.mj_jac(m,s,J,Jr,point,body);mujoco.mj_jacDot(m,s,Jd,Jrd,point,body)
            anchor=self.swing_goal if self.stage=='land' and i==self.swing else self.anchors[i]
            task(np.vstack([J[:,ids],Jr[:,ids]]),np.r_[100*(anchor-point)-25*(J@s.qvel)-Jd@s.qvel,
                 160*rot-28*(Jr@s.qvel)-Jrd@s.qvel],np.array([3,3,3,*([self.foot_orientation_weight]*3)]))
        if self.stage in ['swing','land']:
            i=self.swing;body=self.feet[i];R=s.xmat[body].reshape(3,3);point=s.xpos[body]+R@self.local
            refR=self.scratch.xmat[body].reshape(3,3);goal=self.scratch.xpos[body]+refR@self.local
            rot=.5*sum((np.cross(R[:,j],self.rotation[:,j]) for j in range(3)),np.zeros(3))
            J=np.zeros((3,m.nv));Jr=np.zeros_like(J);Jd=np.zeros_like(J);Jrd=np.zeros_like(J)
            mujoco.mj_jac(m,s,J,Jr,point,body);mujoco.mj_jacDot(m,s,Jd,Jrd,point,body)
            task(np.vstack([J[:,ids],Jr[:,ids]]),np.r_[220*(goal-point)-30*(J@s.qvel)-Jd@s.qvel,
                 120*rot-24*(Jr@s.qvel)-Jrd@s.qvel],np.array([12,12,18,1,1,1]))
        posture=np.c_[np.zeros((12,6)),np.eye(12)]
        task(posture,180*(self.target-s.qpos[self.qids])-26*s.qvel[self.vids],.2)
        regularizer=np.diag(np.r_[np.full(n,.001),np.full(total-n,.05)])
        A=np.vstack([*objectives,regularizer]);target=np.r_[*targets,np.zeros(total)]
        constraints=list(E);lower=list(eb);upper=list(eb)
        def bound(row,lo,hi):constraints.append(row);lower.append(lo);upper.append(hi)
        for k in range(len(contacts)):
            z=np.zeros(total);z[n+3*k+2]=1.;bound(z,0.,3.)
            for axis in [0,1]:
                v=np.zeros(total);v[n+3*k+axis]=1.;bound(v-.7*z,-np.inf,0.);bound(-v-.7*z,-np.inf,0.)
        T=np.zeros((12,total));T[:,:n]=mass[6:]
        for k,(J,_,_) in enumerate(contacts):T[:,n+3*k:n+3*k+3]=-J[:,6:].T
        lim=m.actuator_forcerange[self.aids]
        for i,row in enumerate(T):bound(row,lim[i,0]-bias[6+i],lim[i,1]-bias[6+i])
        units=np.r_[np.ones(3),np.full(15,40.),np.ones(total-n)]
        G=np.array(constraints)*units[None,:];scale=1/np.maximum(np.linalg.norm(G,axis=1),.001)
        As=A*units[None,:];solver=osqp.OSQP()
        solver.setup(P=sparse.csc_matrix(As.T@As),q=-As.T@target,A=sparse.csc_matrix(G*scale[:,None]),
            l=np.array(lower)*scale,u=np.array(upper)*scale,verbose=False,eps_abs=1e-4,eps_rel=1e-4,max_iter=12000,polishing=True)
        if self.previous_qp is not None and len(self.previous_qp)==total:solver.warm_start(x=self.previous_qp/units)
        result=solver.solve(raise_error=False)
        if result.info.status_val not in [1,2]:
            self.qp_failures.append({'t':float(d.time),'reason':result.info.status});d.ctrl[self.aids]=self.qp_torque;return
        x=result.x*units;self.previous_qp=x.copy();self.qp_torque=np.clip(T@x+bias[6:],lim[:,0],lim[:,1]);d.ctrl[self.aids]=self.qp_torque
        if not self.qp_log or d.time-self.qp_log[-1]['t']>.05:
            self.qp_log.append({'t':float(d.time),'contacts':len(contacts),'equality_error':float(np.max(abs(np.array(E)@x-eb))),
                'normal_forces_n':[float(x[n+3*k+2]) for k in range(len(contacts))]})

    def description(self):return {**super().description(),'qp_trace':self.qp_log,'qp_failures':self.qp_failures}
