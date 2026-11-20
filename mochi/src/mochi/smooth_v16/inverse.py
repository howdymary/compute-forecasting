"""Converged per-leg inverse kinematics for forward terrain transitions.

Uses the existing bounded descent solver with explicit forward trajectories.
Only scratch joint references are solved; the free physical root is untouched.
"""
import math
import mujoco
import numpy as np
from ..terrain_v12.contact import ContactWalker
from ..balanced.inverse import PlannedContactInverseWalker

class ConvergedContactWalker(ContactWalker):
    def walking_bounds(self):
        return self.limits.copy()

    def leg_solution(self,root,feet,yaw):
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
        if self.stage=='shift' and self.d.time-self.stage_t>self.p.shift_seconds*.5 and self.w.loads()[['left','right'][1-self.swing]]<.02:
            self.stage_t+=dt
        oldstage=self.stage;oldtime=self.stage_t
        PlannedContactInverseWalker.command(self,velocity)
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
