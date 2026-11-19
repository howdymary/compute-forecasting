"""Bounded development probe; never supplies held-out or training claims."""
import argparse,json,math,time
from pathlib import Path
from mochi.richdesk.world import DeskWorld
from mochi.richdesk.wholebody import WholeBodyWalker
from mochi.richdesk.stepping import StepParameters,FootstepController

p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--seconds',type=float,default=12.)
p.add_argument('--shift',type=float,default=1.);p.add_argument('--stride',type=float,default=.034)
p.add_argument('--swing',type=float,default=.52);p.add_argument('--crouch',type=float,default=.006)
p.add_argument('--speed',type=float,default=.025)
p.add_argument('--controller',choices=['wholebody','reference','native'],default='wholebody');a=p.parse_args()
w=DeskWorld(31000,True)
while w.d.time<.4:w.step(standing=True)
parameters=StepParameters(shift_seconds=a.shift,stride=a.stride,swing_seconds=a.swing,crouch=a.crouch,com_tracking=0,torso_gain=0,angular_damping=0)
if a.controller!='native':w.walker=(WholeBodyWalker if a.controller=='wholebody' else FootstepController)(w,parameters)
t=time.perf_counter();next_report=2.
while w.d.time<a.seconds and not w.fall:
    w.step((a.speed,0,0))
    if w.d.time>next_report:
        print(json.dumps({'id':a.id,'t':round(w.d.time,2),'steps':getattr(w.walker,'steps',None),'phase':getattr(w.walker,'stage',None),'failure':getattr(w.walker,'failed_reason',None),'position':w.d.qpos[:3].round(4).tolist()}),flush=True);next_report+=2
r={'id':a.id,'time':float(w.d.time),'position':w.d.qpos[:3].tolist(),'fall':w.fall,
   'tilt':math.degrees(w.max_tilt),'controller':w.walker.description() if hasattr(w.walker,'description') else {'controller':'frozen-native'},'wall_s':time.perf_counter()-t}
out=Path('mochi/artifacts/richdesk-v10');out.mkdir(parents=True,exist_ok=True)
(out/(a.id+'.json')).write_text(json.dumps({'result':r,'episode':w.episode()},separators=(',',':')))
print(json.dumps({k:v for k,v in r.items() if k!='controller'}),flush=True)
