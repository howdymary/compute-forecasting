"""Experimental floating-base inverse dynamics. All output is leg torque.

Kinematic copies are used for references only. The physical state evolves
through MuJoCo. This controller is engineering work, not neural training.
"""
import math
import mujoco
import numpy as np
from scipy.linalg import lstsq
from scipy import sparse
import osqp

from ..richdesk.stepping import FootstepController


class PreviewDynamics(FootstepController):
    label = 'experimental-contact-constrained-inverse-dynamics'

    def __init__(self, world, parameters=None):
        super().__init__(world, parameters)
        self.held_torque = np.zeros(12)
        self.previous_jac = None
        self.inverse_last = -1.
        self.inverse_stats = []
        self.last_qp_solution = None
        self.last_qp_stance = None
        self.solver_failures = []
        self.servo_state = None

    def apply_torque(self):
        tau=self.held_torque.copy()
        if self.servo_state is not None:
            t,q,v,a=self.servo_state;dt=min(.008,float(self.d.time)-t)
            predicted=q+v*dt+.5*a*dt*dt;speed=v+a*dt
            tau+=self.p.servo_kp*(predicted-self.d.qpos[self.qids])+self.p.servo_kd*(speed-self.d.qvel[self.vids])
        bounds=self.m.actuator_forcerange[self.aids]
        self.d.ctrl[self.aids]=np.clip(tau,bounds[:,0],bounds[:,1])

    def jacobians(self):
        Jcom = np.zeros((3, self.m.nv))
        mujoco.mj_jacSubtreeCom(self.m, self.d, Jcom, 1)
        Jr = np.zeros((3, self.m.nv))
        mujoco.mj_jacBody(self.m, self.d, None, Jr, 1)
        feet = []
        for i, b in enumerate(self.feet):
            J = np.zeros((3, self.m.nv)); R = np.zeros_like(J)
            mujoco.mj_jac(self.m, self.d, J, R, self.foot(i), b)
            feet.append(np.vstack([J, R]))
        return Jcom, Jr, feet

    def command(self, velocity):
        # Reuse the reference planner, then replace its torques with floating-
        # base inverse dynamics. The parent never writes physical qpos.
        self.update_references(velocity)
        d, m = self.d, self.m
        if d.time-self.inverse_last < self.p.inverse_interval:
            self.apply_torque()
            return
        dt = max(float(d.time)-self.inverse_last, self.p.inverse_interval)
        self.inverse_last = float(d.time)
        Jcom, Jr, feet = self.jacobians()
        current = [Jcom, Jr, *feet]
        derivatives = [np.zeros_like(j) if self.previous_jac is None else (j-old)/dt
                       for j, old in zip(current, self.previous_jac or current)]
        self.previous_jac = [j.copy() for j in current]
        vs = np.r_[np.arange(6), self.vids]
        touchdown = self.w.foot_touching(['left','right'][self.swing])
        single = self.stage == 'swing' or (self.stage == 'land' and not touchdown)
        stance = [1-self.swing] if single else [0, 1]
        n = len(vs); nf = 6*len(stance); total = n+nf
        M = np.empty((m.nv, m.nv)); mujoco.mj_fullM(m, M, d.qM)
        E = np.zeros((6, total)); b = np.zeros(E.shape[0]);contact_tasks=[]
        E[:6, :n] = M[np.ix_(np.arange(6), vs)]
        bias = d.qfrc_bias-d.qfrc_passive
        b[:6] = -bias[:6]
        R = d.xmat[1].reshape(3, 3)
        desired = self.rotation
        orient = .5*sum((np.cross(R[:, k], desired[:, k]) for k in range(3)), np.zeros(3))
        # Ground wrenches and zero support-foot acceleration determine the
        # floating base. Orientation feedback is in world coordinates.
        for k, i in enumerate(stance):
            J = feet[i]
            E[:6, n+6*k:n+6*k+6] = -J[:, :6].T
            anchor=self.swing_goal if self.stage=='land' and i==self.swing else self.anchors[i]
            position_error = anchor-self.foot(i)
            footR = d.xmat[self.feet[i]].reshape(3, 3)
            footrot = .5*sum((np.cross(footR[:, j], desired[:, j]) for j in range(3)), np.zeros(3))
            contact_tasks.append((J,np.r_[500*position_error,160*footrot]-35*(J@d.qvel)-derivatives[2+i]@d.qvel))
        # Equality-constrained weighted least squares. Force magnitude is
        # regularized; unilateral/friction/COP checks are reported below.
        rows = []; targets = []
        def task(J, target, weight):
            weight = np.broadcast_to(weight, (len(target),))
            A = np.zeros((len(target), total)); A[:, :n] = J[:, vs]*weight[:, None]
            rows.append(A); targets.append(np.asarray(target)*weight)
        f=self.p.foot_orientation_weight
        for J,value in contact_tasks:task(J,value,np.array([70,70,90,f,f,f]))
        com_velocity = Jcom@d.qvel
        task(Jcom, self.com_acceleration+120*(self.com_target-d.subtree_com[1])+22*(self.com_reference_velocity-com_velocity)-derivatives[0]@d.qvel, 35.)
        task(Jr, 180*orient-26*(Jr@d.qvel)-derivatives[1]@d.qvel, self.p.body_orientation_weight)
        if single:
            # IK scratch contains the planned swing reference, not physics.
            i = self.swing; footR = d.xmat[self.feet[i]].reshape(3, 3)
            refR = self.scratch.xmat[self.feet[i]].reshape(3, 3)
            point = self.scratch.xpos[self.feet[i]]+refR@self.local
            rot = .5*sum((np.cross(footR[:, j], refR[:, j]) for j in range(3)), np.zeros(3))
            task(feet[i], np.r_[180*(point-self.foot(i)), 100*rot]-24*(feet[i]@d.qvel)-derivatives[2+i]@d.qvel,
                 np.array([10,10,15,.5,.5,.5]))
        posture = np.zeros((12, m.nv)); posture[:, self.vids] = np.eye(12)
        posture_weights=np.full(12,self.p.stance_posture_weight)
        if single:posture_weights[self.swing*6:(self.swing+1)*6]=.8
        task(posture, 220*(self.target-d.qpos[self.qids])-30*d.qvel[self.vids], posture_weights)
        A = np.vstack(rows+[np.eye(total)*.0005]); target = np.r_[*targets, np.zeros(total)]
        torque_map = np.zeros((12,total));torque_map[:,:n]=M[np.ix_(self.vids,vs)]
        for k, i in enumerate(stance):
            torque_map[:,n+6*k:n+6*k+6]=-feet[i][:,self.vids].T
        inequalities=[]; lower=[];upper=[]
        def bounded(row,lo,hi):inequalities.append(row);lower.append(lo);upper.append(hi)
        for k,i in enumerate(stance):
            start=n+6*k
            # Wrench forces/moments use world coordinates. Transform local
            # tangential and COP constraints with the intended foot heading.
            T=np.zeros((6,total));T[:3,start:start+3]=self.rotation.T;T[3:,start+3:start+6]=self.rotation.T
            bounded(T[2],0.,3.)
            for axis,extent in [(0,.55),(1,.55),(5,.008)]:
                bounded(T[axis]-extent*T[2],-np.inf,0.)
                bounded(-T[axis]-extent*T[2],-np.inf,0.)
            points=[]
            for ci,c in enumerate(d.contact):
                geom_a,geom_b=int(c.geom1),int(c.geom2)
                other=geom_b if geom_a in self.w.support_geoms else geom_a if geom_b in self.w.support_geoms else -1
                if other<0 or int(m.geom_bodyid[other])!=self.feet[i] or abs(float(c.frame[2]))<.7:continue
                force=np.zeros(6);mujoco.mj_contactForce(m,d,ci,force)
                if force[0]>.0005:points.append((self.rotation.T@(c.pos-self.foot(i)))[:2])
            if points:
                points=np.array(points);xmin,ymin=points.min(0)-.0003;xmax,ymax=points.max(0)+.0003
            else:xmin,xmax,ymin,ymax=-.0003,.0003,-.0003,.0003
            if not self.p.measured_cop_bounds:xmin,xmax,ymin,ymax=-.014,.014,-.005,.005
            # CoP must stay within the currently contacting foot pads. A toe
            # touch cannot supply a full-sole ankle moment during landing.
            bounded(-T[4]-xmax*T[2],-np.inf,0.);bounded(T[4]+xmin*T[2],-np.inf,0.)
            bounded(T[3]-ymax*T[2],-np.inf,0.);bounded(-T[3]+ymin*T[2],-np.inf,0.)
        limits = m.actuator_forcerange[self.aids]
        for i,row in enumerate(torque_map):bounded(row,limits[i,0]-bias[self.vids[i]],limits[i,1]-bias[self.vids[i]])
        for i in range(12):
            row=np.zeros(total);row[6+i]=1.
            horizon=.045;position=d.qpos[self.qids[i]];speed=d.qvel[self.vids[i]]
            lo,hi=self.limits[i];lo=max(lo,.08) if i in [3,9] else lo
            lower_acc=max(-400.,2*(lo+.01-position-speed*horizon)/horizon**2)
            upper_acc=min(400.,2*(hi-.01-position-speed*horizon)/horizon**2)
            if lower_acc<=upper_acc:bounded(row,lower_acc,upper_acc)
        G=np.vstack([E,*inequalities]);lo=np.r_[b,lower];hi=np.r_[b,upper]
        # Normalize metre/radian accelerations and N/Nm contact wrenches.
        # Without this, small-biped rotational inertia makes landing QPs
        # needlessly ill-conditioned.
        units=np.r_[np.ones(3),np.full(15,40.),np.tile([1.,1.,1.,.03,.03,.03],len(stance))]
        As=A*units[None,:];Gs=G*units[None,:]
        row_scale=1/np.maximum(np.linalg.norm(Gs,axis=1),.001)
        solver=osqp.OSQP();solver.setup(P=sparse.csc_matrix(As.T@As),q=-As.T@target,
            A=sparse.csc_matrix(Gs*row_scale[:,None]),l=lo*row_scale,u=hi*row_scale,
            verbose=False,eps_abs=2e-5,eps_rel=2e-5,max_iter=10000,polishing=True)
        if self.last_qp_stance==stance and self.last_qp_solution is not None:solver.warm_start(x=self.last_qp_solution/units)
        result=solver.solve(raise_error=False)
        if result.info.status_val not in [1,2]:
            self.failed_reason='inverse_dynamics_'+result.info.status
            self.solver_failures.append({'t':float(d.time),'status':result.info.status})
            self.apply_torque()
            return
        x=result.x*units;self.last_qp_solution=x.copy();self.last_qp_stance=list(stance)
        tau=torque_map@x+bias[self.vids]
        self.held_torque = np.clip(tau, limits[:, 0], limits[:, 1])
        self.servo_state=(float(d.time),d.qpos[self.qids].copy(),d.qvel[self.vids].copy(),x[6:18].copy())
        self.apply_torque()
        if len(self.inverse_stats)==0 or d.time-self.inverse_stats[-1]['t']>.1:
            self.inverse_stats.append({'t':float(d.time),'phase':self.stage,'equality_error':float(np.max(np.abs(E@x-b))),
                'torque_clipped':bool(np.any(abs(tau-self.held_torque)>1e-5)),
                'wrenches':[x[n+6*k:n+6*k+6].tolist() for k in range(len(stance))]})

    def description(self):
        return {**super().description(), 'inverse_dynamics': self.inverse_stats,'solver_failures':self.solver_failures}
