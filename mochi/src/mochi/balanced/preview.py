"""Finite-horizon CoM preview with jerk cost and support-region constraints.

The preview is a reference, not a motion export. Joint actuators and MuJoCo
contacts determine whether it can be tracked. No physical qpos is assigned.
"""
import math
import numpy as np
from scipy import sparse
import osqp
import mujoco
from ..richdesk.stepping import ease
from .dynamics import PreviewDynamics


class PreviewPlan:
    def __init__(self,feet,landings,initial_com,initial_velocity,single=.4,double=.12,prepare=1.4,dt=.02):
        self.feet=[np.array(p).copy() for p in feet];self.landings=landings
        self.single=single;self.double=double;self.prepare=prepare;self.dt=dt
        self.end=prepare+len(landings)*(single+double)+.6
        N=math.ceil(self.end/dt);t=np.arange(1,N+1)*dt
        A=np.array([[1,dt,.5*dt*dt],[0,1,dt],[0,0,1.]])
        B=np.array([dt**3/6,dt*dt/2,dt]);S=np.zeros((3*N,N));F=np.zeros((3*N,3));current=np.eye(3)
        for i in range(N):
            current=A@current;F[3*i:3*i+3]=current
            for j in range(i+1):S[3*i:3*i+3,j]=np.linalg.matrix_power(A,i-j)@B
        lo=[];hi=[];centres=[]
        for tm in t:
            fs,stance,ratio=self.support(tm)
            if stance is None:
                centre=fs[0]*(1-ratio)+fs[1]*ratio;extent=np.array([.0015,.010])
            else:centre=fs[stance];extent=np.array([.0015,.011])
            lo.append(centre[:2]-extent);hi.append(centre[:2]+extent);centres.append(np.mean(fs,axis=0)[:2])
        lo=np.array(lo);hi=np.array(hi);centres=np.array(centres)
        h=max(.08,float(initial_com[2]));C=np.array([1.,0.,-h/9.81]);Z=np.vstack([C@S[3*i:3*i+3] for i in range(N)])
        Cz=np.vstack([C@F[3*i:3*i+3] for i in range(N)])
        P=S[::3];V=S[1::3];self.states=[];self.receipts=[]
        for axis in range(2):
            x0=np.array([initial_com[axis],initial_velocity[axis],0.])
            target=centres[:,axis];free=F@x0
            objective=np.vstack([P*25,V*.5,np.eye(N)*.0008]);rhs=np.r_[(target-free[::3])*25,-free[1::3]*.5,np.zeros(N)]
            solver=osqp.OSQP();solver.setup(P=sparse.csc_matrix(objective.T@objective),q=-objective.T@rhs,
                A=sparse.csc_matrix(Z),l=lo[:,axis]-Cz@x0,u=hi[:,axis]-Cz@x0,
                verbose=False,eps_abs=1e-6,eps_rel=1e-6,max_iter=20000,polishing=True)
            result=solver.solve(raise_error=False)
            if result.info.status_val not in [1,2]:raise RuntimeError('Preview QP '+result.info.status)
            states=(free+S@result.x).reshape(N,3)
            self.states.append(np.vstack([x0,states]));self.receipts.append({'axis':axis,'status':result.info.status,'iterations':result.info.iter})
        self.times=np.r_[0.,t];self.states=np.stack(self.states,axis=1)

    def support(self,t):
        fs=[p.copy() for p in self.feet]
        if t<self.prepare:return fs,None,.5+.5*ease(t/self.prepare)
        elapsed=t-self.prepare;j=min(int(elapsed/(self.single+self.double)),len(self.landings))
        for k in range(j):fs[k%2]=np.array(self.landings[k]['position'])
        if j==len(self.landings):return fs,None,.5
        phase=elapsed-j*(self.single+self.double);swing=j%2;stance=1-swing
        if phase<self.single:return fs,stance,0.
        fs[swing]=np.array(self.landings[j]['position']);u=ease((phase-self.single)/self.double)
        right=(1-u)*float(stance==1)+u*float(swing==1)
        return fs,None,right

    def sample(self,t):
        k=min(len(self.times)-2,max(0,int(t/self.dt)));u=float(np.clip((t-self.times[k])/self.dt,0,1))
        return (1-u)*self.states[k]+u*self.states[k+1]


class PreviewWalker(PreviewDynamics):
    label='multi-step-com-preview-with-actuated-contact-control'

    def __init__(self,world,parameters=None,landings=None,single=.4,double=.12):
        super().__init__(world,parameters)
        self.start_time=float(self.d.time);self.anchors=[self.foot(i).copy() for i in [0,1]]
        self.yaw=self.w.yaw();c,s=math.cos(self.yaw),math.sin(self.yaw)
        self.rotation=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
        self.initial_com=self.d.subtree_com[1].copy();self.com_offset=self.initial_com-self.d.qpos[:3]
        self.com_target=self.initial_com.copy();self.com_reference_velocity=np.zeros(3);self.com_acceleration=np.zeros(3)
        if landings is None:
            # Four short steps stay before the first book; this is a flat
            # approach diagnostic, never a claim of stair completion.
            landings=[];centre=np.mean(self.anchors,axis=0)
            for j in range(4):
                side=j%2;p=self.anchors[side].copy();p[:2]+=self.rotation[:2,0]*(.012*(j+1));p[2]=world.terrain_height(*p[:2])
                landings.append({'side':['left','right'][side],'position':p.tolist()})
        self.landings=landings;self.plan=PreviewPlan(self.anchors,landings,self.initial_com,np.zeros(2),single,double)
        self.clock=0.;self.previous_time=float(self.d.time);self.active=-1;self.completed=False;self.reference_log=[]
        self.stage='prepare';self.target=self.d.qpos[self.qids].copy();self.joint_target=self.target.copy()

    def update_references(self,velocity):
        d=self.d;p=self.p;elapsed=float(d.time)-self.start_time;self.clock=elapsed
        sample=self.plan.sample(min(elapsed,self.plan.end));self.com_target[:2]=sample[:,0]
        self.com_reference_velocity[:2]=sample[:,1];self.com_acceleration[:2]=sample[:,2]
        feet=[a.copy() for a in self.anchors]
        if elapsed<self.plan.prepare:self.stage='prepare';self.swing=0
        elif self.steps>=len(self.landings):self.stage='settle';self.completed=True
        else:
            j=self.steps;self.swing=j%2;self.swing_goal=np.array(self.landings[j]['position']);self.swing_goal[2]-=.0001
            if self.active!=j:
                self.active=j;self.stage_t=float(d.time);self.swing_start=self.foot(self.swing).copy();self.stage='swing'
                self.phase_log.append({'t':float(d.time),'phase':'swing','swing':['left','right'][self.swing],'target':self.swing_goal.tolist()})
            age=float(d.time)-self.stage_t
            if age<self.plan.single:
                self.stage='swing';u=age/self.plan.single
                horizontal=ease((u-.18)/.64);feet[self.swing]=(1-horizontal)*self.swing_start+horizontal*self.swing_goal
                peak=max(self.swing_start[2],self.swing_goal[2])+p.lift
                if u<.5:height=(1-ease(u/.35))*self.swing_start[2]+ease(u/.35)*peak
                else:height=(1-ease((u-.65)/.35))*peak+ease((u-.65)/.35)*self.swing_goal[2]
                feet[self.swing][2]=height
            else:
                self.stage='land';feet[self.swing]=self.swing_goal.copy()
                touching=self.w.foot_touching(['left','right'][self.swing])
                if touching:
                    self.anchors[self.swing]=self.foot(self.swing).copy();self.stage='transfer'
                if age>self.plan.single+self.plan.double and touching:
                    self.steps+=1;self.active=-1
                if age>self.plan.single+.3 and not touching:self.failed_reason='touchdown_late'
        # Height is continuous and conservative while supports differ.
        zgoal=self.initial_com[2]-p.crouch+min(a[2] for a in self.anchors)
        weight=ease(elapsed/self.plan.prepare);self.com_target[2]=(1-weight)*self.initial_com[2]+weight*zgoal
        self.com_reference_velocity[2]=0.;self.com_acceleration[2]=0.
        root=self.com_target-self.com_offset
        self.joint_target=self.solve(root,feet,self.yaw);self.target=self.joint_target.copy()
        mujoco.mj_forward(self.m,self.scratch)
        if not self.reference_log or d.time-self.reference_log[-1]['t']>.02:
            self.reference_log.append({'t':float(d.time),'clock':elapsed,'com':self.com_target.tolist(),'velocity':self.com_reference_velocity.tolist(),'acceleration':self.com_acceleration.tolist()})

    def description(self):return {**super().description(),'preview_solver':self.plan.receipts,'reference_log':self.reference_log,'completed':self.completed}


class PreviewInverseWalker(PreviewWalker):
    label='com-preview-with-mujoco-contact-inverse-servo'
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.inverse=mujoco.MjData(self.m);self.last_inverse=-1.;self.torque=np.zeros(12);self.inverse_log=[]

    def command(self,velocity):
        from .inverse import ContactInverseWalker
        self.update_references(velocity);ContactInverseWalker.servo(self)
