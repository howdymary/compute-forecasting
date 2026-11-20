"""Physical book-top clearance, turning and forward descent references."""
import math
import numpy as np
import mujoco

from ..balanced.onnx_walk import HoldWalker, HubWalker
from ..balanced.sequence import PhysicalStop
from ..curriculum.world import wrap
from ..terrain_v12.contact import ContactWalker
from ..terrain_v12.legs import BASE
from ..richdesk.verify import book_top
from .navigation import navigate, NavigationParameters
from .inverse import ConvergedContactWalker


class TurningContactWalker(ContactWalker):
    """Rotate each airborne foot while preserving the planted sole heading."""
    def start_shift(self,velocity):
        self.foot_yaws=[math.atan2(self.d.xmat[b].reshape(3,3)[1,0],self.d.xmat[b].reshape(3,3)[0,0]) for b in self.feet]
        target=self.landings[self.steps]['yaw'] if self.steps<len(self.landings) else float(np.mean(self.foot_yaws))
        stance=self.foot_yaws[1-self.swing]
        heading=stance+wrap(target-stance)/2 if self.steps<len(self.landings) else target
        self.swing_yaw_start=self.foot_yaws[self.swing]
        self.swing_yaw_goal=target
        super().start_shift((0.,0.,2*wrap(heading-self.w.yaw())))

    def leg_solution(self,root,feet,yaw):
        from ..richdesk.stepping import ease
        s=self.scratch
        s.qpos[:]=self.d.qpos
        s.qpos[:3]=root
        s.qpos[3:7]=self.body_quaternion(yaw,0.)
        s.qpos[self.qids]=self.joint_target
        headings=list(self.foot_yaws)
        if self.stage in ['swing','land']:
            u=1. if self.stage=='land' else ease((self.d.time-(self.arc_start or self.d.time))/self.swing_scale)
            headings[self.swing]=self.swing_yaw_start+wrap(self.swing_yaw_goal-self.swing_yaw_start)*u
        for _ in range(9):
            mujoco.mj_forward(self.m,s)
            for i,b in enumerate(self.feet):
                R=s.xmat[b].reshape(3,3)
                c,sn=math.cos(headings[i]),math.sin(headings[i])
                desired=np.array([[c,-sn,0],[sn,c,0],[0,0,1.]])
                rot=.5*sum((np.cross(R[:,j],desired[:,j]) for j in range(3)),np.zeros(3))
                J=np.zeros((3,self.m.nv));Jr=np.zeros_like(J)
                mujoco.mj_jac(self.m,s,J,Jr,s.xpos[b]+R@self.local,b)
                ids=np.arange(i*6,(i+1)*6);qs=self.qids[ids];vs=self.vids[ids]
                A=np.vstack([J[:,vs],Jr[:,vs]*.03])
                error=np.r_[feet[i]-(s.xpos[b]+R@self.local),rot*.03]
                step=A.T@np.linalg.solve(A@A.T+np.eye(6)*2e-8,error)
                s.qpos[qs]=np.clip(s.qpos[qs]+np.clip(step,-.10,.10),self.limits[ids,0]+.002,self.limits[ids,1]-.002)
        return s.qpos[self.qids].copy()


def execute_steps(w, landings, parameters, label, backwards=False, timeout=100., turning=False, converged=False):
    start = float(w.d.time)
    w.task = None
    w.phase = 'walk'
    w.path_origin = w.d.qpos[:2].copy()
    w.path_heading = w.yaw() + (math.pi if backwards else 0)
    controller=TurningContactWalker if turning else ConvergedContactWalker if converged else ContactWalker
    w.walker = controller(w, landings=landings, **parameters)
    while w.d.time-start < timeout:
        w.step((-.025 if backwards else .025, 0., 0.))
        if w.walker.completed:
            break
    else:
        print({'label':label,'step':w.walker.steps,'stage':w.walker.stage,
            'root':w.d.qpos[:3].tolist(),'feet':[w.walker.foot(i).tolist() for i in [0,1]],
            'goal':w.walker.swing_goal.tolist(),'support':{s:w.sole_patch(s) for s in ['left','right']}},flush=True)
        raise PhysicalStop(label+'-controller-timeout')
    w.terrain_controller_history.append({'label': label, 't': float(w.d.time),
        'controller': w.walker.description()})
    w.walker = HoldWalker(w)
    stable = 0.
    for _ in range(round(3./w.m.opt.timestep)):
        w.step()
        good = all(w.foot_touching(s) for s in ['left', 'right'])
        if turning:
            good=good and book_top(w)['instant_valid']
        stable = stable+w.m.opt.timestep if good else 0.
        if stable >= .4:
            break
    else:
        raise PhysicalStop(label+'-support-dwell-timeout')
    row = {'label': label, 'success': True, 'duration_s': float(w.d.time)-start,
        'root': w.d.qpos[:3].tolist(), 'dwell_s': stable,
        'sole_patches': {s: w.sole_patch(s) for s in ['left', 'right']}}
    if turning:
        row['book_top']=book_top(w)
    w.events.append({'phase': 'arrival', 't': float(w.d.time), **row})
    return row


def clear_and_turn(w, parameters=None, turn_pairs=9):
    p = {**BASE, 'shift_seconds': 1.8, 'swing_scale': 1., **(parameters or {})}
    p.pop('flat_speed', None)
    # Two supported pairs move away from the clock within the existing book.
    landings=[{'side':side,'position':[-.375+offset,y,.02385]}
        for y in [.030,.020] for side,offset in [('left',-.012),('right',.012)]]
    rows=[execute_steps(w,landings,{**p,'width':.024},'book-turn-clearance',backwards=True)]
    w.efficiency_segment='book_turnaround'
    center=np.array([-.375,.020])
    headings=np.linspace(math.pi/2,-math.pi/2,turn_pairs+1)[1:]
    landings=[]
    for heading in headings:
        for side,offset in [('left',.012),('right',-.012)]:
            xy=center+np.array([-math.sin(heading),math.cos(heading)])*offset
            landings.append({'side':side,'position':[*xy,.02385],'yaw':float(heading)})
    initial=w.yaw()
    row=execute_steps(w,landings,p,'book-top-turnaround',timeout=120.,turning=True)
    row.update(initial_yaw=initial,final_yaw=w.yaw(),heading_error_degrees=math.degrees(abs(wrap(-math.pi/2-w.yaw()))))
    if row['heading_error_degrees']>10:
        raise PhysicalStop('book-turnaround-heading-missed')
    rows.append(row)
    return rows


def turn_in_place(w, heading, timeout=35.):
    start=float(w.d.time)
    origin=w.d.qpos[:2].copy()
    initial=w.yaw()
    w.walker=HubWalker(w)
    w.walker.control_arms=False
    for arm in w.arm.values():
        w.d.ctrl[arm['acts']]=arm['rest']
    w.efficiency_segment='book_turnaround'
    w.phase='turn'
    while w.d.time-start<timeout:
        error=wrap(heading-w.yaw())
        c,s=math.cos(w.yaw()),math.sin(w.yaw())
        local=np.array([[c,s],[-s,c]])@(origin-w.d.qpos[:2])
        velocity=np.clip(local*3.,-.05,.05)
        w.step((*velocity,float(np.clip(error*1.2,-.35,.35))))
        if abs(error)<math.radians(6) and all(v>.2 for v in w.loads().values()):
            break
    else:
        raise PhysicalStop('book-turnaround-timeout')
    w.walker.hold()
    end=float(w.d.time)+.4
    while w.d.time<end:
        w.step()
    w.walker=HoldWalker(w)
    row={'label':'book-top-turnaround','success':abs(wrap(heading-w.yaw()))<math.radians(10),
        'duration_s':float(w.d.time)-start,'initial_yaw':initial,'final_yaw':w.yaw(),
        'heading_error_degrees':math.degrees(abs(wrap(heading-w.yaw()))),
        'root':w.d.qpos[:3].tolist(),'displacement_m':float(np.linalg.norm(w.d.qpos[:2]-origin))}
    w.events.append({'phase':'arrival','t':float(w.d.time),**row})
    if not row['success']:
        raise PhysicalStop('book-turnaround-heading-missed')
    return row


def cross_postit(w, parameters=None):
    p={**BASE,'shift_seconds':1.65,'swing_scale':1.,**(parameters or {})}
    speed=p.pop('flat_speed',.080)
    direct=p.pop('direct',True)
    w.efficiency_segment='flat_transit'
    rows=[]
    # Retain the verified drawer departure corridor before approaching paper.
    points=[(.08,.02,0.),(.180,.015,0.)] if direct else [(.08,.02,0.),(.08,-.055,-math.pi/2),(.180,-.055,0.),(.180,.015,0.)]
    for i,point in enumerate(points):
        rows.append(navigate(w,point,speed=speed,stop=i==len(points)-1,label='postit-approach-'+str(i),
            parameters=NavigationParameters(forward_gain=1.)))
    w.efficiency_segment='postit_crossing'
    landings=[{'side':side,'position':[x,.015+offset,w.terrain_height(x,.015+offset)-.00015]}
        for x in [.195,.236,.275,.305,.335]
        for side,offset in [('left',.012),('right',-.012)]]
    rows.append(execute_steps(w,landings,{**p,'width':.024,'crouch':.022},'postit-loaded-crossing',timeout=90.,converged=True))
    if not getattr(w,'postit_crossings',[]):
        raise PhysicalStop('postit-required-loaded-contact-missing')
    landings=[{'side':side,'position':[.335,.015+offset,-.00015]}
        for side,offset in [('left',.020),('right',-.020)]]
    rows.append(execute_steps(w,landings,{**p,'width':.04},'postit-exit-stance',timeout=30.))
    w.walker=HoldWalker(w,neutral=True)
    end=float(w.d.time)+1.
    while w.d.time<end:
        w.step()
    return rows


def forward_descent(w, parameters=None):
    p={**BASE,'shift_seconds':1.8,'swing_scale':1.,**(parameters or {})}
    p.pop('flat_speed',None)
    if abs(wrap(w.yaw()+math.pi/2))>math.radians(10):
        raise PhysicalStop('forward-descent-start-heading-invalid')
    w.efficiency_segment='book_descent'
    landings=[{'side':side,'position':[x,y,w.terrain_height(x,y)-.00015]}
        for y in [.002,-.041,-.052,-.091,-.112,-.151,-.18]
        for side,x in [('left',-.363),('right',-.387)]]
    rows=[execute_steps(w,landings,p,'book-forward-descent',timeout=100.,converged=True)]
    from .verification import forward_descent_check
    rows[0]['forward_verification']=forward_descent_check(w.step_counter.events,w.book_motion_samples)
    if not rows[0]['forward_verification']['verified']:
        raise PhysicalStop('book-forward-descent-orientation-unverified')
    landings=[{'side':side,'position':[x,-.18,-.00015]}
        for side,x in [('left',-.355),('right',-.395)]]
    rows.append(execute_steps(w,landings,{**p,'width':.04},'forward-descent-exit-stance',timeout=30.))
    w.walker=HoldWalker(w,neutral=True)
    end=float(w.d.time)+1.
    while w.d.time<end:
        w.step()
    return rows
