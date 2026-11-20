"""Contact-aware floating-base stance control through bounded leg torques.

Adapted from the repository's measured-contact inverse-dynamics controller.
The optimization predicts support wrenches; it never applies a root wrench,
sets a physical pose, locks a foot or changes collision geometry.
"""
import math
import mujoco
import numpy as np
import osqp
from scipy import sparse
from ..balanced.onnx_walk import HoldWalker


class ContactHold(HoldWalker):
    label='contact-aware-two-foot-inverse-dynamics'

    def __init__(self,w):
        super().__init__(w)
        self.stage='contact-supported-hold'
        self.last_inverse=-1.
        self.torque=np.zeros(12)
        self.feet=[w.id('body',s+'_ankle_roll_link') for s in ['left','right']]
        self.local=np.array([.0058,0.,-.00585])
        self.anchors=[self.point(b).copy() for b in self.feet]
        self.rotations=[self.d.xmat[b].reshape(3,3).copy() for b in self.feet]
        yaw=w.yaw();c,s=math.cos(yaw),math.sin(yaw)
        self.rotation=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])
        self.com_target=self.d.subtree_com[1].copy()
        self.com_target[:2]=np.mean(self.anchors,axis=0)[:2]
        self.inverse_log=[]
        self.failures=[]

    def point(self,b):
        return self.d.xpos[b]+self.d.xmat[b].reshape(3,3)@self.local

    def hand_reaction(self):
        """Generalized reaction reconstructed from measured robot/object contacts."""
        value=np.zeros(self.m.nv)
        for i,c in enumerate(self.d.contact):
            a,b=int(c.geom1),int(c.geom2)
            ra=int(self.m.geom_bodyid[a]) in self.w.robot_bodies
            rb=int(self.m.geom_bodyid[b]) in self.w.robot_bodies
            if ra==rb:continue
            robot=a if ra else b
            if robot not in self.w.hand_geoms['left']:continue
            force=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,force)
            sign=-1. if ra else 1.
            R=c.frame.reshape(3,3)
            mujoco.mj_applyFT(self.m,self.d,sign*(R.T@force[:3]),sign*(R.T@force[3:]),
                             c.pos,int(self.m.geom_bodyid[robot]),value)
        return value

    def command(self,velocity):
        d,m=self.d,self.m
        if d.time-self.last_inverse<.01:
            d.ctrl[self.aids]=self.torque
            return
        self.last_inverse=float(d.time)
        vs=np.r_[np.arange(6),self.vids];n=len(vs);total=n+12
        M=np.zeros((m.nv,m.nv));mujoco.mj_fullM(m,M,d.qM)
        bias=d.qfrc_bias-d.qfrc_passive-self.hand_reaction()
        Jcom=np.zeros((3,m.nv));Jr=np.zeros_like(Jcom)
        mujoco.mj_jacSubtreeCom(m,d,Jcom,1);mujoco.mj_jacBody(m,d,None,Jr,1)
        feet=[]
        for b in self.feet:
            J=np.zeros((3,m.nv));Jrfoot=np.zeros_like(J)
            mujoco.mj_jac(m,d,J,Jrfoot,self.point(b),b)
            feet.append(np.vstack([J,Jrfoot]))
        E=np.zeros((6,total));E[:,:n]=M[np.ix_(np.arange(6),vs)]
        for i,J in enumerate(feet):E[:,n+6*i:n+6*i+6]=-J[:,:6].T
        rows=[];targets=[]
        def task(J,target,weight):
            weight=np.broadcast_to(weight,len(target));A=np.zeros((len(target),total))
            A[:,:n]=J[:,vs]*weight[:,None];rows.append(A);targets.append(np.asarray(target)*weight)
        for i,(b,J) in enumerate(zip(self.feet,feet)):
            R=d.xmat[b].reshape(3,3);goal=self.rotations[i]
            rot=.5*sum((np.cross(R[:,j],goal[:,j]) for j in range(3)),np.zeros(3))
            task(J,np.r_[500*(self.anchors[i]-self.point(b)),180*rot]-35*(J@d.qvel),[70,70,90,8,8,8])
        R=d.xmat[1].reshape(3,3)
        orient=.5*sum((np.cross(R[:,j],self.rotation[:,j]) for j in range(3)),np.zeros(3))
        task(Jcom,120*(self.com_target-d.subtree_com[1])-22*(Jcom@d.qvel),35.)
        task(Jr,180*orient-26*(Jr@d.qvel),8.)
        posture=np.zeros((12,m.nv));posture[:,self.vids]=np.eye(12)
        task(posture,100*(self.initial_target-d.qpos[self.qids])-20*d.qvel[self.vids],.25)
        A=np.vstack(rows+[np.eye(total)*.001]);target=np.r_[*targets,np.zeros(total)]
        torque=np.zeros((12,total));torque[:,:n]=M[np.ix_(self.vids,vs)]
        for i,J in enumerate(feet):torque[:,n+6*i:n+6*i+6]=-J[:,self.vids].T
        G=[*E];lo=list(-bias[:6]);hi=list(-bias[:6])
        def bounded(row,low,high):G.append(row);lo.append(low);hi.append(high)
        for i in range(2):
            T=np.zeros((6,total));T[:3,n+6*i:n+6*i+3]=self.rotations[i].T
            T[3:,n+6*i+3:n+6*i+6]=self.rotations[i].T
            bounded(T[2],0.,4.)
            for axis,extent in [(0,.55),(1,.55),(5,.008)]:
                bounded(T[axis]-extent*T[2],-np.inf,0.)
                bounded(-T[axis]-extent*T[2],-np.inf,0.)
            # Conservative sole bounds in the foot frame, checked by actual
            # contact loads and collision verifiers in the physics world.
            for row in [-T[4]-.014*T[2],T[4]-.014*T[2],T[3]-.005*T[2],-T[3]-.005*T[2]]:
                bounded(row,-np.inf,0.)
        limits=m.actuator_forcerange[self.aids]
        for i,row in enumerate(torque):bounded(row,limits[i,0]-bias[self.vids[i]],limits[i,1]-bias[self.vids[i]])
        units=np.r_[np.ones(3),np.full(15,40.),np.tile([1.,1.,1.,.03,.03,.03],2)]
        As=A*units;Gs=np.asarray(G)*units
        scale=1/np.maximum(np.linalg.norm(Gs,axis=1),.001)
        solver=osqp.OSQP();solver.setup(P=sparse.csc_matrix(As.T@As),q=-As.T@target,
             A=sparse.csc_matrix(Gs*scale[:,None]),l=np.asarray(lo)*scale,u=np.asarray(hi)*scale,
             verbose=False,eps_abs=2e-5,eps_rel=2e-5,max_iter=4000,polishing=True)
        result=solver.solve(raise_error=False)
        if result.info.status_val in [1,2]:
            x=result.x*units
            self.torque=np.clip(torque@x+bias[self.vids],limits[:,0],limits[:,1])
        else:self.failures.append({'t':float(d.time),'status':result.info.status})
        d.ctrl[self.aids]=self.torque
        if not self.inverse_log or d.time-self.inverse_log[-1]['t']>.1:
            self.inverse_log.append({'t':float(d.time),'status':result.info.status,
                    'roll_rad':math.atan2(R[2,1],R[2,2]),'loads_n':self.w.loads()})

    def description(self):
        return {'controller':self.label,'native_weights_trained':False,
                'solver_calls_logged':len(self.inverse_log),'solver_failures':len(self.failures),
                'actuation':'bounded leg joint torques; no applied base wrench'}
