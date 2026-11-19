"""Continuous furnished-desk engineering reference, with actuator-only motion.

No resets or object edits after construction. A completed engineering run is
the prerequisite for training; it is never reported as a trained improvement.
"""
import argparse
import hashlib
import json
import math
import time

import numpy as np
import mujoco

from ..curriculum.world import ROOT, PROFILES, wrap
from ..control_v8.manipulation import PRESSES
from .recovery import RECOVERIES, recover
from ..richdesk.verify import book_top
from .budget import reserve, finish, OUT
from .onnx_walk import HubWalker, HoldWalker
from .world import BalancedWorld


class PhysicalStop(RuntimeError):
    pass


class SequenceWorld(BalancedWorld):
    def step(self, *args, **kwargs):
        if kwargs.get('standing',False) and isinstance(self.walker,HubWalker) and self.walker.mode!='walk':
            kwargs['standing']=False
        super().step(*args, **kwargs)
        # Walking may use desk/book foot contact, never a clock/cabinet/body
        # brace. Task fixtures are not part of the terrain-only parent check.
        if self.phase=='walk':
            from .balance import walking_contact_violation
            violation=walking_contact_violation(self)
            if violation:
                self.invalid_contact=True;self.contact_failures.append(violation)
        if self.stopped:
            self.stop_contacts=[]
            for i,c in enumerate(self.d.contact):
                a,b=int(c.geom1),int(c.geom2)
                ra=int(self.m.geom_bodyid[a]) in self.robot_bodies
                rb=int(self.m.geom_bodyid[b]) in self.robot_bodies
                if ra==rb:continue
                f=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,f)
                if f[0]>.01:
                    self.stop_contacts.append({'geom_names':[mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_GEOM,g) for g in [a,b]],
                                               'body_names':[mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_BODY,int(self.m.geom_bodyid[g])) for g in [a,b]],
                                               'normal':c.frame[:3].tolist(),'force_n':float(f[0])})
            raise PhysicalStop('fall' if self.fall else 'invalid_terrain_contact')


def average_velocity(w, seconds=.10):
    rows = w.measurements
    if not rows:
        return np.array(w.d.qvel[:2])
    recent = next((r for r in reversed(rows) if rows[-1]['t']-r['t'] >= seconds), rows[0])
    return (w.d.qpos[:2]-np.array(recent['root'][:2]))/max(.001, float(w.d.time)-recent['t'])


def navigate(w, goal, *, timeout=35., stop=True, speed=.055, book=False,
             position_tolerance=.027, label='waypoint',capture_margin=.001):
    """Holonomic route tracking, measured support capture, then actual dwell."""
    start = float(w.d.time)
    w.task = None
    w.phase = 'walk'
    # Crossing a navigation waypoint must preserve the gait's phase, previous
    # action, and command filter. Resetting the neural gait at every corner
    # introduces a controller discontinuity despite continuous physics.
    if not isinstance(w.walker,HubWalker):
        w.walker = HubWalker(w)
    else:
        w.walker.resume()
    if not book and w.terrain_height(*w.d.qpos[:2])>.001:
        w.walker.control_arms=False
        for arm in w.arm.values():w.d.ctrl[arm['acts']]=arm['rest']
    origin = w.d.qpos[:2].copy()
    delta = np.array(goal[:2])-origin
    w.path_heading = math.atan2(delta[1], delta[0]) if np.linalg.norm(delta)>.001 else goal[2]
    w.path_origin = origin
    holding = False
    stable = 0.
    while w.d.time-start < timeout:
        distance = math.dist(w.d.qpos[:2], goal[:2])
        heading = abs(wrap(goal[2]-w.yaw()))
        if not stop and distance < .018:
            break
        approach_ok = abs(w.d.qpos[1]-goal[1])<.018 if book else distance<position_tolerance
        from .balance import support
        considering_stop=stop and not holding and approach_ok and heading<math.radians(9)
        balance=support(w) if capture_margin is not None and considering_stop else None
        support_ok=capture_margin is None or (balance is not None and balance['capture_margin_m'] is not None and balance['capture_margin_m']>=capture_margin)
        if not book and considering_stop:
            _,foot_speeds=w.foot_state()
            support_ok = (support_ok and all(w.foot_touching(s) for s in ['left','right'])
                          and all(v>.2 for v in w.loads().values()))
            if label.endswith('-station') and not getattr(w,'use_native_stand',False):
                support_ok=(support_ok and balance is not None
                            and np.linalg.norm(balance['com_velocity_m_s'][:2])<.03
                            and np.max(abs(w.d.qvel[w.walker.vids]))<5.)
        if (stop and not holding and approach_ok and heading < math.radians(9) and support_ok
                and np.linalg.norm(average_velocity(w)) < .015
                and np.linalg.norm(w.d.qvel[:2]) < .08
                and all(v>.05 for v in w.loads().values())):
            if getattr(w,'use_native_stand',False) and not book and w.terrain_height(*w.d.qpos[:2])<.001:
                w.walker.hold()
            else:
                w.walker = HoldWalker(w,neutral=not book and w.terrain_height(*w.d.qpos[:2])<.001)
            holding = True
            w.events.append({'phase':'supported-capture','t':float(w.d.time),'station':label,
                             'balance':balance,'loads_n':w.loads(),
                             'leg_speed_max_rad_s':float(np.max(abs(w.d.qvel[w.walker.vids])))})
        if holding:
            w.step()
            good = book_top(w)['instant_valid'] if book else (all(v>.05 for v in w.loads().values()) and heading < math.radians(9))
            stable = stable+w.m.opt.timestep if good else 0.
            if stable >= .4:
                if isinstance(w.walker,HubWalker) and w.walker.mode!='walk':
                    # Let the feedback policy settle before capturing a static
                    # stance; freezing a moving joint pose was unstable.
                    w.events.append({'phase':'native-settle-finished','t':float(w.d.time),'station':label,
                                     'leg_speed_max_rad_s':float(np.max(abs(w.d.qvel[w.walker.vids])))})
                    w.walker=HoldWalker(w)
                    stable=0.
                    continue
                break
        else:
            yaw = w.yaw()
            R = np.array([[math.cos(yaw),-math.sin(yaw)], [math.sin(yaw),math.cos(yaw)]])
            error = R.T@(np.array(goal[:2])-w.d.qpos[:2])
            command = np.clip(error*np.array([.6,.8]), [-.035,-.025], [speed,.025])
            if book:
                # Preserve the physically verified straight-book approach.
                command = np.array([np.clip((goal[1]-w.d.qpos[1])*.6,-.035,speed),
                                    np.clip((w.d.qpos[0]-goal[0])*.8,-.025,.025)])
            turn = float(np.clip(wrap(goal[2]-yaw)*2,-.6,.6))
            w.step((*command,turn))
    success = bool((not stop and math.dist(w.d.qpos[:2],goal[:2])<.018) or stable>=.4)
    result = {'label':label,'goal':list(goal),'success':success,'duration_s':float(w.d.time)-start,
              'position_error_mm':math.dist(w.d.qpos[:2],goal[:2])*1000,
              'heading_error_degrees':math.degrees(abs(wrap(goal[2]-w.yaw()))),
              'root':w.d.qpos[:3].tolist(),'loads_n':w.loads(),'dwell_s':stable,
              'book_top':book_top(w) if book else None}
    w.events.append({'phase':'arrival','t':float(w.d.time),**result})
    print(json.dumps({'arrival':result}),flush=True)
    if not success:
        raise PhysicalStop('navigation_timeout:'+label)
    return result


def run(seed=31000, record=True, until='all', speed=.055, alarm_x=-.375,alarm_y=.035,capture_margin=None,forward_descent=False,descent_speed=None,native_stand=False,drawer_profile='A',choose=None,warm_resume=False,native_feedback=.7):
    w = SequenceWorld(seed,record)
    w.use_native_stand=native_stand
    w.warm_resume=warm_resume
    w.native_feedback=native_feedback
    w.decision_interface_enabled=choose is not None
    arrivals = []
    failure = None
    started = time.perf_counter()
    try:
        while w.d.time<.4:
            w.step(standing=True)
        from .legs import execute_leg,execute_selected_leg,WALKS
        for task,code in [('alarm','B'),('drawer',drawer_profile),('laptop','P0'),('globe','A')]:
            if choose is None:
                arrivals.extend(execute_leg(w,task,speed=speed,alarm_x=alarm_x,alarm_y=alarm_y,
                                capture_margin=capture_margin,forward_descent=forward_descent,
                                descent_speed=descent_speed))
            else:
                walk_code=choose(w,'walk',task,'W1' if task=='drawer' else 'W0',list(WALKS))
                arrivals.extend(execute_selected_leg(w,task,walk_code))
            if until=='ascent' and task=='alarm':
                return result(w,arrivals,None,started,until)
            if choose is not None:
                code=choose(w,task,task,code,[p.code for p in (PRESSES[:3] if task=='laptop' else PROFILES[:3])])
            profile = next(p for p in (PRESSES if task=='laptop' else PROFILES) if p.code==code)
            if task=='alarm':
                from .tasks import press_alarm
                task_result=press_alarm(w,profile)
            else:
                task_result = w.do_task(task,profile)
            print(json.dumps({'task':task_result}),flush=True)
            if not task_result['success']:
                raise PhysicalStop('task_failed:'+task)
            recovery_code='R1' if task=='alarm' else 'R0'
            if choose is not None:recovery_code=choose(w,'recovery',task,recovery_code,['R0','R1','R3'])
            recovery = recover(w,task,next(r for r in RECOVERIES if r.code==recovery_code))
            print(json.dumps({'recovery':recovery}),flush=True)
            if not recovery['success']:
                raise PhysicalStop('recovery_failed:'+task)
            if until==task:
                break
        for _ in range(round(.5/w.m.opt.timestep)):
            w.step()
    except PhysicalStop as exc:
        failure = str(exc)
    return result(w,arrivals,failure,started,until)


def result(w,arrivals,failure,started,until):
    episode = w.episode()
    episode['stop_contacts']=getattr(w,'stop_contacts',[])
    from .verification import complete
    return {'study':'mochi-balanced-v11','seed':w.s['seed'],'scope':'Decision interface enabled' if getattr(w,'decision_interface_enabled',False) else 'Engineering reference; zero new Tinker optimizer updates',
            'complete_sequence_success':bool(until=='all' and complete(episode,arrivals,failure)),
            'requested_end':until,'failure':failure,'arrivals':arrivals,'episode':episode,
            'controller':w.walker.description(),'wall_seconds':time.perf_counter()-started,
            'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src/mochi/balanced').glob('*.py')}}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--id',required=True)
    p.add_argument('--until',choices=['ascent','alarm','drawer','laptop','globe','all'],default='all')
    p.add_argument('--speed',type=float,default=.055)
    p.add_argument('--alarm-x',type=float,default=-.375)
    p.add_argument('--alarm-y',type=float,default=.035)
    p.add_argument('--capture-margin',type=float)
    p.add_argument('--forward-descent',action='store_true')
    p.add_argument('--descent-speed',type=float)
    p.add_argument('--native-stand',action='store_true')
    p.add_argument('--drawer-profile',choices=[p.code for p in PROFILES],default='A')
    p.add_argument('--fixed-selector',action='store_true')
    args=p.parse_args()
    reserve(args.id,vars(args))
    try:
        from .policy import fixed
        row=run(until=args.until,speed=args.speed,alarm_x=args.alarm_x,alarm_y=args.alarm_y,capture_margin=args.capture_margin,forward_descent=args.forward_descent,descent_speed=args.descent_speed,native_stand=args.native_stand,drawer_profile=args.drawer_profile,choose=fixed if args.fixed_selector else None)
        (OUT/(args.id+'.json')).write_text(json.dumps(row,separators=(',',':')))
        summary={k:row[k] for k in ['complete_sequence_success','failure','requested_end','wall_seconds']}
        summary.update(duration_s=row['episode']['duration'],tasks={k:v['success'] for k,v in row['episode']['results'].items()})
        finish(args.id,{'status':'completed',**summary})
        print(json.dumps(summary),flush=True)
    except Exception as exc:
        finish(args.id,{'status':'failed','error':type(exc).__name__})
        raise


if __name__=='__main__':
    main()
