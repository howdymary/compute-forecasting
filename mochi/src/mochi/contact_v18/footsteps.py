"""Lifted flat-ground footstep references executed through real joint torques.

Planning edits reference poses only. MuJoCo retains the floating base and
all physical contacts. Actual sole clearance is measured independently.
"""
import math
import numpy as np
import mujoco
from ..curriculum.world import wrap
from ..balanced.onnx_walk import HoldWalker
from ..balanced.sequence import PhysicalStop
from ..smooth_v16.terrain import TurningContactWalker
from ..richdesk.stepping import ease


class FlatContactWalker(TurningContactWalker):
    """One swing clock, followed by measured touchdown and support transfer."""
    def command(self,velocity):
        d=self.d
        if self.anchors is None:self.begin(np.asarray(velocity))
        if d.time-self.last>=.008:
            dt=max(.001,float(d.time)-self.last) if self.last>=0 else .008
            self.last=float(d.time);age=float(d.time)-self.stage_t
            feet=[x.copy() for x in self.anchors];yaw=self.yaw_goal
            if self.stage=='center':
                u=ease(age/1.2);root=(1-u)*self.root_start+u*self.root_goal
                self.com_target=(1-u)*self.com_start+u*self.com_goal
                self.target=self.solve(root,feet,yaw);self.joint_target=self.target.copy()
                steady=all(self.w.foot_touching(s) for s in ['left','right']) and np.linalg.norm(d.qvel[:3])<.01
                self.center_dwell=self.center_dwell+dt if u>=1 and steady else 0.
                self.completed=self.center_dwell>=.25
            else:
                root=self.root_goal.copy()
                if self.stage=='shift':
                    u=ease(age/self.p.shift_seconds)
                    root=(1-u)*self.root_start+u*self.root_goal
                    yaw=(1-u)*self.yaw_start+u*self.yaw_goal
                    self.com_target=(1-u)*self.com_start+u*self.com_goal
                    patch=self.w.sole_patch(['left','right'][1-self.swing])
                    if age>=self.p.shift_seconds and patch['loaded'] and patch['capture_margin_m'] is not None and patch['capture_margin_m']>=.0005:
                        self.stage='swing';self.stage_t=float(d.time);self.arc_start=float(d.time)
                        self.rise_start=float(d.time);self.active_lift_step=self.steps
                        self.phase_log.append({'t':float(d.time),'phase':'swing','swing':['left','right'][self.swing]})
                    elif age>4.:raise PhysicalStop('flat-support-transfer-timeout')
                else:
                    self.com_target=self.com_goal.copy()
                    feet[self.swing]=self.swing_goal.copy()
                    if self.stage=='swing' and age>=self.swing_scale+.04:
                        self.stage='land';self.stage_t=float(d.time);self.flat_touchdown_dwell=0.
                    elif self.stage=='land':
                        side=['left','right'][self.swing]
                        good=self.w.foot_touching(side) and np.linalg.norm(self.foot(self.swing)-self.swing_goal)<.007
                        self.flat_touchdown_dwell=self.flat_touchdown_dwell+dt if good else 0.
                        if self.flat_touchdown_dwell>=.04:
                            self.anchors[self.swing]=self.foot(self.swing).copy()
                            self.steps+=1;self.swing=1-self.swing;self.start_shift(velocity)
                            root=self.root_start.copy();feet=[x.copy() for x in self.anchors];yaw=self.yaw_start
                        elif age>1.8:raise PhysicalStop('flat-touchdown-not-confirmed')
                self.target=self.solve(root,feet,yaw);self.joint_target=self.target.copy()
        self.servo()

def plan(w,points,stride=.040,width=.028):
    xy=w.d.qpos[:2].copy();yaw=w.yaw();feet=[]
    for side in ['left','right']:
        b=w.id('body',side+'_ankle_roll_link')
        feet.append(w.d.xpos[b]+w.d.xmat[b].reshape(3,3)@np.array([.0058,0,-.00585]))
    c,s=math.cos(yaw),math.sin(yaw)
    offset=np.array([[c,s],[-s,c]])@(np.mean(feet,axis=0)[:2]-xy)
    rows=[]
    for point in points:
        goal=np.array(point[:2]);heading=point[2] if len(point)>2 else None
        for _ in range(100):
            delta=goal-xy;distance=float(np.linalg.norm(delta))
            if distance<.007:
                if heading is None or abs(wrap(heading-yaw))<math.radians(4):break
                desired=heading;advance=0.
            else:
                desired=math.atan2(delta[1],delta[0]);advance=min(stride,distance)
            error=wrap(desired-yaw);yaw+=float(np.clip(error,-math.radians(20),math.radians(20)))
            remaining=abs(wrap(desired-yaw))
            advance*=max(0.,math.cos(remaining))**2 if remaining<math.radians(12) else 0.
            xy+=advance*np.array([math.cos(yaw),math.sin(yaw)])
            c,s=math.cos(yaw),math.sin(yaw);R=np.array([[c,-s],[s,c]])
            center=xy+R@offset
            for side,sign in [('left',1),('right',-1)]:
                position=center+R@np.array([0.,sign*width/2])
                z=w.terrain_height(*position)
                rows.append({'side':side,'position':[*position,z-.00015],'yaw':yaw})
        else:raise ValueError('Footstep reference plan did not converge')
    return rows

def sole_clearance(w,side):
    b=w.id('body',side+'_ankle_roll_link');values=[]
    for g in range(w.m.ngeom):
        if int(w.m.geom_bodyid[g])!=b or w.m.geom_type[g]!=mujoco.mjtGeom.mjGEOM_SPHERE:continue
        p=w.d.geom_xpos[g];values.append(float(p[2]-w.m.geom_size[g,0]-w.terrain_height(*p[:2])))
    return min(values) if values else None

def execute_flat(w,points,*,label='lifted-flat-walk',shift=.55,swing=.60,timeout=160.):
    start=float(w.d.time);landings=plan(w,points)
    w.task=None;w.phase='walk';w.efficiency_segment='lifted_flat_walk'
    controller=FlatContactWalker(w,landings=landings,width=.028,crouch=.012,
                    shift_seconds=shift,swing_scale=swing,balance_feedback=.5)
    w.walker=controller;samples=[];w.flat_step_samples=samples;next_sample=start
    while w.d.time-start<timeout:
        turning=hasattr(controller,'yaw_goal') and abs(wrap(controller.yaw_goal-w.yaw()))>math.radians(10)
        w.phase='turn' if turning else 'walk'
        w.step((.025,0.,0.))
        if w.d.time>=next_sample:
            samples.append({'t':float(w.d.time),'swing':getattr(controller,'swing',None),'phase':controller.stage,
                    'clearance_m':{s:sole_clearance(w,s) for s in ['left','right']},'loads_n':w.loads()})
            next_sample=float(w.d.time)+.01
        if controller.completed:break
    else:raise PhysicalStop(label+'-timeout')
    w.walker=HoldWalker(w)
    end=float(w.d.time)+.4
    while w.d.time<end:w.step()
    goal=points[-1];distance=math.dist(w.d.qpos[:2],goal[:2])
    heading=abs(wrap(goal[2]-w.yaw())) if len(goal)>2 else 0.
    row={'label':label,'success':bool(distance<.012 and heading<math.radians(9) and not w.stopped),
         'duration_s':float(w.d.time)-start,'root':w.d.qpos[:3].tolist(),
         'position_error_mm':distance*1000,'heading_error_degrees':math.degrees(heading),
         'planned_footsteps':landings,'actual_clearance_samples':samples,
         'controller':controller.description()}
    w.events.append({'t':float(w.d.time),'phase':'arrival',**{k:v for k,v in row.items() if k not in ['actual_clearance_samples','controller','planned_footsteps']}})
    if not row['success']:raise PhysicalStop(label+'-arrival-error')
    return row
