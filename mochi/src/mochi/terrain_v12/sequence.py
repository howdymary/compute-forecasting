"""One uninterrupted furnished-desk episode, including book traversal.

Every route, posture and hand reference is executed through actuators. No
physical root or object state is reassigned after TerrainWorld construction.
"""
import argparse,hashlib,json,math,time
from pathlib import Path
import numpy as np
from ..balanced.sequence import PhysicalStop,navigate
from ..balanced.onnx_walk import HubWalker,HoldWalker
from .tasks import press_alarm
from ..balanced.recovery import RECOVERIES,recover
from ..balanced.legs import execute_leg
from ..control_v8.manipulation import PRESSES
from ..control_v8.verification import full_success
from ..curriculum.world import PROFILES,TASKS
from ..richdesk.verify import book_top
from .world import TerrainWorld
from .contact import ContactWalker,descent_landings
from .budget import reserve,finish,OUT
from .legs import execute_selected_leg


def book_leg(w,direction,parameters,timeout=160.,landings=None,label=None):
    w.task=None;w.phase='walk';w.path_origin=w.d.qpos[:2].copy();w.path_heading=math.pi/2 if direction>0 else -math.pi/2
    if direction<0 and landings is None:
        width=parameters.get('width',.024)
        landings=descent_landings(w,width)
    w.walker=ContactWalker(w,landings=landings,**parameters);started=float(w.d.time);next_report=started+10.
    while w.d.time-started<timeout:
        w.step((direction*.025,0,0))
        if w.record and w.d.time>=next_report:
            print(json.dumps({'traversal':label or direction,'t':round(w.d.time,2),'step':w.walker.steps,'phase':w.walker.stage}),flush=True);next_report+=10.
        if w.walker.completed:break
    else:raise PhysicalStop('book-controller-timeout:'+str(label or direction))
    history={'label':label or ('ascent' if direction>0 else 'descent'),'t':float(w.d.time),'controller':w.walker.description()}
    w.terrain_controller_history.append(history)
    w.walker=HoldWalker(w);dwell=0.;begin=float(w.d.time)
    while w.d.time-begin<3.:
        w.step()
        top=direction>0 and (landings is None or landings[-1]['position'][2]>.02)
        good=book_top(w)['instant_valid'] if top else (
            all(w.foot_touching(s) for s in ['left','right']) and w.terrain_height(*w.d.qpos[:2])<.001)
        dwell=dwell+w.m.opt.timestep if good else 0.
        if dwell>=.4:break
    else:raise PhysicalStop('supported-dwell-timeout:'+str(label or direction))
    row={'label':label or ('book-ascent' if direction>0 else 'book-descent'),'success':True,
         'duration_s':float(w.d.time)-started,'dwell_s':dwell,'root':w.d.qpos[:3].tolist(),
         'sole_patches':{s:w.sole_patch(s) for s in ['left','right']},
         'book_top':book_top(w) if top else None}
    w.events.append({'phase':'arrival','t':float(w.d.time),**row});return row


def prepare_flat_walking(w,parameters):
    # Widen with two real steps before restoring the pretrained flat gait's
    # stand pose. The soles are never dragged or repositioned in render space.
    y=float(np.mean([w.d.xpos[w.id('body',s+'_ankle_roll_link'),1] for s in ['left','right']]))+.005
    landings=[{'side':s,'position':[x,y,-.00015]} for s,x in [('left',-.395),('right',-.355)]]
    p={**parameters,'width':.04,'support_roll':0.}
    arrival=book_leg(w,1,p,landings=landings,label='flat-stance-transition',timeout=30.)
    w.walker=HoldWalker(w,neutral=True);start=float(w.d.time);dwell=0.
    while w.d.time-start<3.:
        w.step()
        steady=(all(w.foot_touching(s) for s in ['left','right']) and np.linalg.norm(w.d.qvel[:3])<.015
                and abs(w.d.qpos[2]-w.terrain_neutral_clearance)<.003)
        dwell=dwell+w.m.opt.timestep if steady else 0.
        if dwell>=.4:return arrival
    raise PhysicalStop('neutral-standing-transition-timeout')


def run(seed=41000,record=True,parameters=None,choose=None,until='all'):
    parameters=parameters or {'width':.024,'balance_feedback':.5,'descent_lift':.006,'descent_height_fraction':1.,'book_goal':.04}
    w=TerrainWorld(seed,record);w.terrain_controller_history=[];w.use_native_stand=True
    started=time.perf_counter();arrivals=[];failure=None
    try:
        while w.d.time<.4:w.step(standing=True)
        w.walker=HubWalker(w);w.walker=HoldWalker(w)
        for task in TASKS:
            # Callback receives observed state only; it never edits the scene
            # or the verifier. The reference currently uses one fixed profile.
            walk=choose(w,'walk',task,'W0',['W0','W1','W2']) if choose else 'W0'
            arrivals.extend(execute_selected_leg(w,task,walk,parameters))
            if until=='ascent' and task=='alarm':break
            choices=[p.code for p in (PRESSES[:3] if task=='laptop' else [PROFILES[i] for i in [1,2,5]] if task=='alarm' else PROFILES[:3])]
            code=choose(w,task,task,{'alarm':'F','drawer':'B','laptop':'P0','globe':'A'}[task],choices) if choose else {'alarm':'F','drawer':'B','laptop':'P0','globe':'A'}[task]
            p=next(p for p in (PRESSES if task=='laptop' else PROFILES) if p.code==code)
            result=press_alarm(w,p) if task=='alarm' else w.do_task(task,p)
            print(json.dumps({'task':result}),flush=True)
            if not result['success']:raise PhysicalStop('task-failed:'+task)
            default='R1' if task=='alarm' else 'R0';code=choose(w,'recovery',task,default,['R0','R1','R3']) if choose else default
            result=recover(w,task,next(p for p in RECOVERIES if p.code==code))
            if not result['success']:raise PhysicalStop('recovery-failed:'+task)
            if until==task:break
        end=float(w.d.time)+.5
        while w.d.time<end:w.step()
    except PhysicalStop as exc:failure=str(exc)
    episode=w.episode();episode['terrain_controller_history']=w.terrain_controller_history
    episode['executed_root_distance_m']=float(sum(np.linalg.norm(np.array(b['root'][:2])-a['root'][:2]) for a,b in zip(w.measurements,w.measurements[1:])))
    supported=all(w.foot_touching(s) for s in ['left','right'])
    complete=bool(until=='all' and failure is None and full_success(episode) and not w.invalid_contact
        and episode['maximum_applied_base_force']==0 and len(episode.get('recoveries',[]))==4
        and all(r['success'] for r in episode['recoveries']) and supported
        and any(r['label']=='book-ascent' for r in arrivals) and any(r['label']=='book-descent' for r in arrivals))
    scope='Controller engineering reference; zero new Tinker optimizer updates' if choose is None else 'Physical categorical-policy rollout; checkpoint and training receipts are recorded by the caller'
    return {'study':'mochi-terrain-v12','seed':seed,'scope':scope,
        'complete_sequence_success':complete,'requested_end':until,'failure':failure,'parameters':parameters,
        'arrivals':arrivals,'terrain_conditions':w.terrain_conditions,'episode':episode,'wall_seconds':time.perf_counter()-started}


def main():
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--seed',type=int,default=41000)
    p.add_argument('--until',choices=['ascent','alarm','drawer','laptop','globe','all'],default='all');p.add_argument('--parameters',default='{}');a=p.parse_args()
    reserve(a.id,vars(a))
    try:
        row=run(a.seed,True,json.loads(a.parameters) or None,until=a.until)
        (OUT/(a.id+'.json')).write_text(json.dumps(row,separators=(',',':')))
        result={'status':'completed','complete_sequence_success':row['complete_sequence_success'],'failure':row['failure'],
                'duration':row['episode']['duration'],'tasks':{t:r['success'] for t,r in row['episode']['results'].items()}}
        finish(a.id,result);print(json.dumps(result),flush=True)
    except Exception as exc:finish(a.id,{'status':'failed','error':type(exc).__name__});raise

if __name__=='__main__':main()
