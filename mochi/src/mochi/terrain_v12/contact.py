"""Reachable support poses and converged floating-base contact inverse control."""
import math
from dataclasses import replace
import mujoco,numpy as np
from scipy.optimize import least_squares
from ..balanced.inverse import PlannedContactInverseWalker
from ..richdesk.stepping import StepParameters


def stair_landings(w,width=.028,book_goal=None):
    rows=[]
    ys=[-.208,-.185,-.16,-.152,-.107,-.092,-.046,.002,.025]+([] if book_goal is None else [book_goal])
    for y in ys:
        for side,x in [('left',-.375-width/2),('right',-.375+width/2)]:
            rows.append({'side':side,'position':[x,y,w.terrain_height(x,y)-.00015]})
    return rows


def descent_landings(w,width=.024,short=True):
    # Backward reach is more restricted than forward reach. Approach each
    # edge before descending, with the entire sole clear of the riser.
    ys=[.002,-.041,-.052,-.091,-.112,-.151,-.18] if short else [.002,-.046,-.092,-.107,-.152,-.16,-.185]
    return [{'side':s,'position':[x,y,w.terrain_height(x,y)-.00015]} for y in ys
            for s,x in [('left',-.375-width/2),('right',-.375+width/2)]]


class ContactWalker(PlannedContactInverseWalker):
    label='reachable-support-pose-with-converged-contact-inverse-control'
    def __init__(self,w,crouch=.012,pose_search=True,newton_iterations=16,servo_kp=300.,servo_kd=35.,cartesian_swing=False,landings=None,width=.028,adaptive_swing=True,book_goal=None,arm_model=True,balance_feedback=0.,descent_lift=.004,bounded_backward=True,lower_during_descent=False,descent_height_fraction=None,support_roll=0.):
        self.pose_search=pose_search;self.newton_iterations=newton_iterations;self.servo_kp=servo_kp;self.servo_kd=servo_kd;self.pose_log=[];self.cartesian_swing=cartesian_swing
        self.swing_data=mujoco.MjData(w.m);self.width=width;self.last_command_time=float(w.d.time);self.support_wait_started=None
        self.adaptive_swing=adaptive_swing;self.active_lift_step=None;self.arc_start=None;self.rise_start=None
        self.arm_model=arm_model;self.completed=False;self.center_dwell=0.;self.balance_feedback=balance_feedback
        self.ascent_lift=.010;self.descent_lift=descent_lift
        self.backward=False;self.ik_log=[];self.bounded_backward=bounded_backward;self.lower_during_descent=lower_during_descent
        self.descent_height_fraction=float(lower_during_descent) if descent_height_fraction is None else descent_height_fraction
        self.support_roll=support_roll;self.roll_start=0.;self.roll_goal=0.
        p=StepParameters(crouch=crouch,shift_seconds=1.8,swing_seconds=.65,lift=.010,
            com_tracking=0,torso_gain=0,angular_damping=0,support_forward=.002)
        super().__init__(w,landings or stair_landings(w,width,book_goal),p)

    def begin(self,velocity):
        self.anchors=[self.foot(i).copy() for i in [0,1]];self.yaw=self.w.yaw();self.body_z=float(self.d.qpos[2]);self.root_start=self.d.qpos[:3].copy()
        self.com_offset=self.d.xmat[1].reshape(3,3).T@(self.d.subtree_com[1]-self.d.qpos[:3]);self.com_target=self.d.subtree_com[1].copy()
        if not hasattr(self.w,'terrain_neutral_clearance'):
            self.w.terrain_neutral_clearance=self.body_z-float(np.mean([p[2] for p in self.anchors]))
        self.base_clearance=self.w.terrain_neutral_clearance-self.p.crouch
        self.swing=0;self.start_shift(velocity)

    def start_shift(self,velocity):
        self.backward=velocity[0]<0
        R=self.d.xmat[1].reshape(3,3);self.roll_start=math.atan2(R[2,1],R[2,2])
        self.roll_goal=(self.support_roll*(1 if 1-self.swing==1 else -1)) if self.backward and self.steps<len(self.landings) else 0.
        self.p=replace(self.p,support_forward=-.002 if velocity[0]<0 else .002,lift=self.descent_lift if velocity[0]<0 else self.ascent_lift)
        # A toe contact leaves the sole centre above the surface. Preserve
        # measured horizontal placement, but seat the *reference* on the
        # known tread plane before planning load transfer.
        if self.anchors is not None:
            for anchor in self.anchors:
                height=self.w.terrain_height(*anchor[:2])
                if abs(anchor[2]-height)<.003:anchor[2]=height-.00015
        previous=self.joint_target.copy();super().start_shift(velocity)
        if not self.pose_search:return
        target=self.com_goal[:2].copy();s=self.scratch;m=self.m
        if self.steps>=len(self.landings):
            target=np.mean(self.anchors,axis=0)[:2]+self.rotation[:2,0]*.002
            self.stage='center';self.center_dwell=0.
        desiredR=self.rotation.copy();z0=self.root_goal[2]
        bounds=self.walking_bounds() if self.backward and self.bounded_backward else self.limits
        lo=np.r_[self.root_goal[:2]-.05,min(p[2] for p in self.anchors)+.09,bounds[:,0]+.003]
        hi=np.r_[self.root_goal[:2]+.05,min(p[2] for p in self.anchors)+.14,bounds[:,1]-.003]
        def residual(x):
            s.qpos[:]=self.d.qpos;s.qpos[:3]=x[:3];s.qpos[3:7]=self.body_quaternion(self.yaw_goal,self.roll_goal);s.qpos[self.qids]=x[3:]
            mujoco.mj_forward(m,s);errors=[]
            for i,b in enumerate(self.feet):
                R=s.xmat[b].reshape(3,3);point=s.xpos[b]+R@self.local
                rot=.5*sum((np.cross(R[:,j],desiredR[:,j]) for j in range(3)),np.zeros(3))
                errors.extend((point-self.anchors[i])*20);errors.extend(rot*.6)
            return np.r_[errors,(s.subtree_com[1,:2]-target)*20,(x[2]-z0)*.5,(x[3:]-previous)*.0001]
        x0=np.clip(np.r_[self.root_goal,self.joint_target],lo+.00001,hi-.00001)
        opt=least_squares(residual,x0,bounds=(lo,hi),max_nfev=100,ftol=1e-8,xtol=1e-8,gtol=1e-8)
        residual(opt.x);self.root_goal=opt.x[:3].copy();self.com_goal=s.subtree_com[1].copy()
        foot_error=max(np.linalg.norm(self.anchors[i]-(s.xpos[b]+s.xmat[b].reshape(3,3)@self.local)) for i,b in enumerate(self.feet))
        self.pose_log.append({'t':float(self.d.time),'step':self.steps,'root_goal':self.root_goal.tolist(),'com_goal':self.com_goal.tolist(),
                              'foot_error_m':float(foot_error),'com_error_m':float(np.linalg.norm(self.com_goal[:2]-target)),'nfev':opt.nfev})
        self.joint_target=previous

    def solve(self,root,feet,yaw):
        if not self.adaptive_swing or self.stage not in ['swing','land']:
            return self.leg_solution(root,feet,yaw)
        from ..richdesk.stepping import ease
        if self.active_lift_step!=self.steps:
            self.active_lift_step=self.steps;self.arc_start=float(self.d.time);self.rise_start=float(self.d.time)
        t=float(self.d.time);references=[p.copy() for p in feet];i=self.swing
        u=float(np.clip((t-self.arc_start)/(1.4 if self.backward else 1.),0,1));start=self.swing_start;goal=self.swing_goal
        travel=ease((u-.15)/.55) if self.backward else ease(u)
        references[i]=(1-travel)*start+travel*goal
        peak=max(start[2],goal[2])+self.p.lift
        if self.backward:
            if u<.2:references[i][2]=(1-ease(u/.2))*start[2]+ease(u/.2)*peak
            else:references[i][2]=(1-ease((u-.72)/.28))*peak+ease((u-.72)/.28)*goal[2]
        elif u<.45:references[i][2]=(1-ease(u/.45))*start[2]+ease(u/.45)*peak
        else:references[i][2]=(1-ease((u-.55)/.45))*peak+ease((u-.55)/.45)*goal[2]
        # Keep the lower support reachable until it is actually unloaded;
        # then extend the stance leg instead of trapping the swing leg in a
        # deep crouch. This changes references, never physical root state.
        if self.w.loads()[['left','right'][i]]>.05 and t-self.rise_start<.2:
            self.rise_start=t
        corrected=np.asarray(root).copy();stance_height=self.anchors[1-i][2]
        target_height=self.base_clearance+stance_height+self.descent_height_fraction*min(0.,goal[2]-stance_height)
        corrected[2]+=ease((t-self.rise_start)/.5)*(target_height-root[2])
        self.com_target=self.com_goal.copy();self.com_target[2]+=corrected[2]-root[2]
        for _ in range(3):
            result=self.leg_solution(corrected,references,yaw);mujoco.mj_forward(self.m,self.scratch)
            corrected[:2]+=np.clip(self.com_target[:2]-self.scratch.subtree_com[1,:2],-.003,.003)
        return result

    def walking_bounds(self):
        b=self.limits.copy()
        for offset in [0,6]:
            for j,lo,hi in [(0,-1.1,.7),(1,-.45,.45),(2,-.6,.6),(3,.08,1.85)]:
                b[offset+j]=[max(b[offset+j,0],lo),min(b[offset+j,1],hi)]
        return b

    @staticmethod
    def body_quaternion(yaw,roll):
        c,s=math.cos(yaw/2),math.sin(yaw/2);a,b=math.cos(roll/2),math.sin(roll/2)
        return [c*a,c*b,s*b,s*a]

    def reference_roll(self):
        from ..richdesk.stepping import ease
        if self.stage=='shift':return self.roll_start+(self.roll_goal-self.roll_start)*ease((self.d.time-self.stage_t)/self.p.shift_seconds)
        if self.stage=='center':return self.roll_start*(1-ease((self.d.time-self.stage_t)/1.2))
        return self.roll_goal

    def leg_solution(self,root,feet,yaw):
        if not self.backward or not self.bounded_backward:return super().solve(root,feet,yaw)
        from ..richdesk.stepping import ease
        s=self.scratch;m=self.m;s.qpos[:]=self.d.qpos;s.qpos[:3]=root
        s.qpos[3:7]=self.body_quaternion(yaw,self.reference_roll());s.qpos[self.qids]=self.joint_target
        c,sn=math.cos(yaw),math.sin(yaw);desired=np.array([[c,-sn,0],[sn,c,0],[0,0,1.]])
        bounds=self.walking_bounds();errors=[]
        for i,body in enumerate(self.feet):
            ids=np.arange(i*6,(i+1)*6);qs=self.qids[ids];vs=self.vids[ids];previous=self.joint_target[ids].copy()
            lo=np.maximum(bounds[ids,0]+.002,previous-.08);hi=np.minimum(bounds[ids,1]-.002,previous+.08)
            pitch_weight=.03
            if self.stage=='swing' and i==self.swing:
                u=float(np.clip((self.d.time-(self.arc_start or self.d.time))/1.,0,1))
                pitch_weight=.003+.027*ease((u-.7)/.3)
            weights=np.array([.03,pitch_weight,.03]);s.qpos[qs]=np.clip(previous,lo,hi)
            def residual():
                mujoco.mj_forward(m,s);R=s.xmat[body].reshape(3,3);point=s.xpos[body]+R@self.local
                rot=desired.T@(.5*sum((np.cross(R[:,j],desired[:,j]) for j in range(3)),np.zeros(3)))
                return np.r_[feet[i]-point,rot*weights,(previous-s.qpos[qs])*.0003]
            for _ in range(10):
                error=residual();old=s.qpos[qs].copy();cost=float(error@error)
                J=np.zeros((3,m.nv));Jr=np.zeros_like(J);mujoco.mj_jac(m,s,J,Jr,s.xpos[body]+s.xmat[body].reshape(3,3)@self.local,body)
                A=np.vstack([J[:,vs],(desired.T@Jr[:,vs])*weights[:,None],np.eye(6)*.0003])
                step=np.linalg.solve(A.T@A+np.eye(6)*1e-9,A.T@error)
                accepted=False
                for fraction in [1.,.5,.25,.125]:
                    s.qpos[qs]=np.clip(old+step*fraction,lo,hi);candidate=residual()
                    if candidate@candidate<=cost:accepted=True;break
                if not accepted:s.qpos[qs]=old;break
                if np.linalg.norm(s.qpos[qs]-old)<1e-6:break
            error=residual();errors.append(float(np.linalg.norm(error[:3])))
        result=s.qpos[self.qids].copy()
        if not self.ik_log or self.d.time-self.ik_log[-1]['t']>.04:
            self.ik_log.append({'t':float(self.d.time),'phase':self.stage,'foot_position_error_m':errors,'maximum_reference_change_rad':float(np.max(abs(result-self.joint_target)))})
        return result

    def command(self,velocity):
        dt=float(self.d.time)-self.last_command_time;self.last_command_time=float(self.d.time)
        if self.stage=='center':
            from ..richdesk.stepping import ease
            u=ease((self.d.time-self.stage_t)/1.2);root=(1-u)*self.root_start+u*self.root_goal
            self.com_target=(1-u)*self.com_start+u*self.com_goal
            self.target=self.solve(root,self.anchors,self.yaw_goal);self.joint_target=self.target.copy();self.servo()
            steady=all(self.w.foot_touching(s) for s in ['left','right']) and np.linalg.norm(self.d.qvel[:3])<.01
            self.center_dwell=self.center_dwell+dt if u>=1 and steady else 0.
            self.completed=self.center_dwell>=.4
            return
        # Allow load to transfer while the old support remains planted. A
        # lightly touching sole can flatten under preload, but cannot authorize
        # lifting the old foot until a broad loaded patch is measured.
        if self.stage=='shift' and self.d.time-self.stage_t>self.p.shift_seconds*.5 and not self.w.foot_touching(['left','right'][1-self.swing]):
            self.stage_t+=dt
        oldstage=self.stage;oldtime=self.stage_t
        super().command(velocity)
        if self.stage=='land' and self.d.time-self.stage_t>self.p.landing_seconds:
            from ..balanced.sequence import SequenceWorld
            side=['left','right'][self.swing]
            light_contact=SequenceWorld.foot_touching(self.w,side)
            if light_contact and np.linalg.norm(self.foot(self.swing)-self.swing_goal)<.007:
                self.phase_log.append({'t':float(self.d.time),'phase':'light-touchdown-start-transfer','side':side,'full_support_verified':False})
                self.anchors[self.swing]=self.foot(self.swing).copy();self.steps+=1;self.swing=1-self.swing;self.start_shift(velocity)
        if oldstage=='shift' and self.stage=='swing':
            check=self.w.sole_patch(['left','right'][1-self.swing]);margin=check['capture_margin_m']
            if not self.w.foot_touching(['left','right'][1-self.swing]) or margin is None or margin<.0005:
                self.stage='shift';self.stage_t=oldtime
                self.active_lift_step=None
                self.phase_log[-1].update(accepted=False,reason='support-patch-or-capture-margin')

    def swing_target(self):
        if not self.cartesian_swing or self.stage!='land':return self.target
        m=self.m;s=self.swing_data;i=self.swing;b=self.feet[i]
        s.qpos[:]=self.d.qpos;s.qpos[self.qids]=self.target
        mujoco.mj_forward(m,s)
        # Preserve the nominal leg-position reference and its support bias;
        # level the sole against the measured body orientation at touchdown.
        goal=s.xpos[b]+s.xmat[b].reshape(3,3)@self.local
        if not self.w.foot_touching(['left','right'][self.swing]):
            goal[2]-=min(.0015,max(0.,float(self.d.time)-self.stage_t)*.001)
        ids=np.arange(i*6,(i+1)*6);qs=self.qids[ids];vs=self.vids[ids]
        for _ in range(5):
            mujoco.mj_forward(m,s);R=s.xmat[b].reshape(3,3);point=s.xpos[b]+R@self.local
            rot=.5*sum((np.cross(R[:,j],self.rotation[:,j]) for j in range(3)),np.zeros(3))
            J=np.zeros((3,m.nv));Jr=np.zeros_like(J);mujoco.mj_jac(m,s,J,Jr,point,b)
            A=np.vstack([J[:,vs],Jr[:,vs]*.03]);delta=A.T@np.linalg.solve(A@A.T+np.eye(6)*2e-8,np.r_[goal-point,rot*.03])
            s.qpos[qs]=np.clip(s.qpos[qs]+np.clip(delta,-.12,.12),self.limits[ids,0]+.002,self.limits[ids,1]-.002)
        target=self.target.copy();target[ids]=s.qpos[qs];return target

    def servo(self):
        m,d,s=self.m,self.d,self.inverse
        if d.time-self.last_inverse<.004:d.ctrl[self.aids]=self.torque;return
        self.last_inverse=float(d.time);s.qpos[:]=d.qpos;s.qvel[:]=d.qvel;s.qacc[:]=d.qacc
        target=self.swing_target()
        s.qacc[self.vids]=np.clip(self.servo_kp*(target-d.qpos[self.qids])-self.servo_kd*d.qvel[self.vids],-1200,1200)
        if self.balance_feedback:
            R=d.xmat[1].reshape(3,3);error=R.T@(d.subtree_com[1]-self.com_target)
            J=np.zeros((3,m.nv));mujoco.mj_jacSubtreeCom(m,d,J,1);v=R.T@(J@d.qvel)
            pitch=math.asin(float(np.clip(-R[2,0],-1,1)));roll=math.atan2(R[2,1],R[2,2])
            correction=np.array([800*error[0]+80*v[0]+40*pitch+8*d.qvel[4],
                                  -800*error[1]-80*v[1]+40*(roll-self.reference_roll())+8*d.qvel[3]])*self.balance_feedback
            correction=np.clip(correction,-3.,3.)
            loads=self.w.loads();total=max(sum(loads.values()),.001)
            for i,side in enumerate(['left','right']):
                weight=loads[side]/total
                s.qacc[self.vids[6*i+4]]+=correction[0]*weight
                s.qacc[self.vids[6*i+5]]+=correction[1]*weight
        arms=np.array(self.w.arm_dofs);M=np.empty((m.nv,m.nv));mujoco.mj_fullM(m,M,d.qM)
        # Arm accelerations are not prescribed by the leg controller. Solve
        # their linear dynamics using their actual position-servo effort,
        # rather than carrying an incompatible acceleration from the old step.
        arm_effort=[]
        for side in ['left','right']:
            arm=self.w.arm[side];a=arm['acts'];v=arm['vs'];q=arm['qs']
            effort=m.actuator_gainprm[a,0]*d.ctrl[a]+m.actuator_biasprm[a,0]+m.actuator_biasprm[a,1]*d.qpos[q]+m.actuator_biasprm[a,2]*d.qvel[v]
            effort=np.clip(effort,m.actuator_forcerange[a,0],m.actuator_forcerange[a,1])+d.qfrc_bias[v]
            arm_effort.extend(effort)
        arm_effort=np.array(arm_effort)
        aa=M[np.ix_(arms,arms)];ab=M[np.ix_(arms,np.arange(6))]
        rhs=arm_effort-(d.qfrc_bias-d.qfrc_passive)[arms]-M[np.ix_(arms,self.vids)]@s.qacc[self.vids]
        arm_constant=np.linalg.solve(aa,rhs);arm_base=np.linalg.solve(aa,ab)
        def couple():
            if self.arm_model:s.qacc[arms]=arm_constant-arm_base@s.qacc[:6]
        couple()
        mujoco.mj_inverse(m,s)
        for iteration in range(self.newton_iterations):
            f=s.qfrc_inverse[:6].copy()
            if np.linalg.norm(f)<1e-6:break
            base=s.qacc[:6].copy();A=np.zeros((6,6));h=.001
            for j in range(6):
                s.qacc[:6]=base;s.qacc[j]+=h;couple();mujoco.mj_inverseSkip(m,s,mujoco.mjtStage.mjSTAGE_VEL,1)
                A[:,j]=(s.qfrc_inverse[:6]-f)/h
            step=np.linalg.lstsq(A,-f,rcond=1e-9)[0];s.qacc[:6]=base+np.clip(step,-1000,1000)
            couple()
            mujoco.mj_inverseSkip(m,s,mujoco.mjtStage.mjSTAGE_VEL,1)
        limits=m.actuator_forcerange[self.aids];desired=s.qfrc_inverse[self.vids]-d.qfrc_applied[self.vids]
        self.torque=np.clip(desired,limits[:,0],limits[:,1]);d.ctrl[self.aids]=self.torque
        if not self.inverse_log or d.time-self.inverse_log[-1]['t']>.05:
            self.inverse_log.append({'t':float(d.time),'virtual_base_residual':float(np.linalg.norm(s.qfrc_inverse[:6])),
                'arm_effort_residual':float(np.max(abs(s.qfrc_inverse[arms]-arm_effort))),
                'torque_clipped':bool(np.any(abs(desired-self.torque)>1e-6)),'iterations':iteration+1})

    def description(self):return {**super().description(),'support_poses':self.pose_log,'stance_width_m':self.width,'adaptive_swing':self.adaptive_swing,'balance_feedback':self.balance_feedback,'ik_trace':self.ik_log,'native_weights_trained':False}
