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
        super().step(*args, **kwargs)
        if self.stopped:
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
        balance=support(w) if capture_margin is not None else None
        support_ok=capture_margin is None or (balance['capture_margin_m'] is not None and balance['capture_margin_m']>=capture_margin)
        if not book:
            support_ok = support_ok and all(w.foot_touching(s) for s in ['left','right']) and all(v>.2 for v in w.loads().values())
        if (stop and not holding and approach_ok and heading < math.radians(9) and support_ok
                and np.linalg.norm(average_velocity(w)) < .015
                and np.linalg.norm(w.d.qvel[:2]) < .08
                and all(v>.05 for v in w.loads().values())):
            w.walker = HoldWalker(w)
            holding = True
        if holding:
            w.step()
            good = book_top(w)['instant_valid'] if book else (all(v>.05 for v in w.loads().values()) and heading < math.radians(9))
            stable = stable+w.m.opt.timestep if good else 0.
            if stable >= .4:
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


def run(seed=31000, record=True, until='all', speed=.055, alarm_x=-.375,alarm_y=.035,capture_margin=None,forward_descent=False,descent_speed=None):
    w = SequenceWorld(seed,record)
    arrivals = []
    failure = None
    started = time.perf_counter()
    try:
        while w.d.time<.4:
            w.step(standing=True)
        arrivals.append(navigate(w,(alarm_x,alarm_y,math.pi/2),book=True,speed=speed,label='alarm-book-top',capture_margin=capture_margin))
        if until=='ascent':
            return result(w,arrivals,None,started,until)
        for task,code in [('alarm','B'),('drawer','A'),('laptop','P0'),('globe','A')]:
            if task=='drawer':
                if forward_descent:
                    arrivals.append(navigate(w,(*w.d.qpos[:2],-math.pi/2),capture_margin=.001,
                                             label='book-turn-for-forward-descent'))
                heading=-math.pi/2 if forward_descent else math.pi/2
                descend_x=float(w.d.qpos[0])
                arrivals.append(navigate(w,(descend_x,-.18,heading),stop=True,speed=descent_speed or speed,
                                         capture_margin=.001,position_tolerance=.018,label='descend-supported-stop'))
                if forward_descent:
                    arrivals.append(navigate(w,(*w.d.qpos[:2],math.pi/2),capture_margin=.001,label='desk-turn-to-corridor'))
                for point in [(-.19,-.18,math.pi/2),(-.19,-.03,math.pi/2)]:
                    arrivals.append(navigate(w,point,stop=False,speed=speed,label='drawer-corridor'))
                arrivals.append(navigate(w,(-.13,.02,math.pi/2),speed=speed,position_tolerance=.012,label='drawer-station'))
            elif task=='laptop':
                for point in [(.08,.02,math.pi/2),(.08,-.055,math.pi/2),(.30,-.055,math.pi/2),(.30,.02,math.pi/2)]:
                    arrivals.append(navigate(w,point,stop=False,speed=speed,label='laptop-corridor'))
                arrivals.append(navigate(w,(.30,.16,math.pi/2),speed=speed,position_tolerance=.012,label='laptop-station'))
            elif task=='globe':
                arrivals.append(navigate(w,(.30,.02,math.pi/2),stop=False,speed=speed,label='leave-laptop'))
                arrivals.append(navigate(w,(.35,-.145,0.),speed=speed,position_tolerance=.012,label='globe-station'))
            profile = next(p for p in (PRESSES if task=='laptop' else PROFILES) if p.code==code)
            if task=='alarm':
                from .tasks import press_alarm
                task_result=press_alarm(w,profile)
            else:
                task_result = w.do_task(task,profile)
            print(json.dumps({'task':task_result}),flush=True)
            if not task_result['success']:
                raise PhysicalStop('task_failed:'+task)
            recovery = recover(w,task,RECOVERIES[1 if task=='alarm' else 0])
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
    return {'study':'mochi-balanced-v11','seed':w.s['seed'],'scope':'Engineering reference; zero new Tinker optimizer updates',
            'complete_sequence_success':bool(until=='all' and failure is None and len(w.results)==4),
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
    args=p.parse_args()
    reserve(args.id,vars(args))
    try:
        row=run(until=args.until,speed=args.speed,alarm_x=args.alarm_x,alarm_y=args.alarm_y,capture_margin=args.capture_margin,forward_descent=args.forward_descent,descent_speed=args.descent_speed)
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
