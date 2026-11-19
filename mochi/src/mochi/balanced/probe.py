"""Reproducible, budget-counted development probes; never opens test seeds."""
import argparse,hashlib,json,math,time,traceback
import numpy as np
from dataclasses import asdict
from ..curriculum.world import ROOT
from ..richdesk.world import scene_spec
from ..richdesk.stepping import StepParameters
from ..richdesk.terrain import PlannedTerrainWalker
from ..richdesk.verify import book_top
from .world import BalancedWorld
from .inverse import PlannedContactInverseWalker
from .budget import reserve,finish,OUT


def main():
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--kind',choices=['old','inverse','preview','preview_inverse','reachable','reachable_inverse','landing','landing_reachable','native_residual','hub'],default='old')
    p.add_argument('--seconds',type=float,default=15);p.add_argument('--shift',type=float,default=1.8);p.add_argument('--crouch',type=float,default=.012)
    p.add_argument('--lift',type=float,default=.003);p.add_argument('--terrain-gain',type=float,default=0.);p.add_argument('--speed',type=float,default=.065)
    p.add_argument('--waist',action='store_true');p.add_argument('--sole',choices=['source','flat'],default='source');p.add_argument('--width',type=float,default=.04);p.add_argument('--isolated',action='store_true');a=p.parse_args();reserve(a.id,vars(a));started=time.perf_counter()
    try:
        scene=scene_spec()
        if a.isolated:scene['initial_pose'][1]=-.155
        w=BalancedWorld(31000,True,scene=scene)
        if a.sole=='flat':
            from .model import install_flat_soles
            install_flat_soles(w)
        if a.waist:
            from .model import install_native_waist
            install_native_waist(w)
        while w.d.time<.4 and not w.stopped:w.step(standing=True)
        params=StepParameters(shift_seconds=a.shift,swing_seconds=.7,lift=.010,stride=.022,crouch=a.crouch,
            com_tracking=0,torso_gain=0,angular_damping=0,support_forward=.003,stance_posture_weight=.6)
        ys=[-.110,-.09,-.049,.0,.025] if a.isolated else [-.207,-.19,-.17,-.151,-.110,-.09,-.049,.0,.025]
        steps=[{'side':s,'position':[x,y,w.terrain_height(x,y)]} for y in ys for s,x in [('left',-.375-a.width/2),('right',-.375+a.width/2)]]
        if a.kind=='old':
            w.walker=PlannedTerrainWalker(w,steps,params)
        elif a.kind=='inverse':w.walker=PlannedContactInverseWalker(w,steps,params)
        elif a.kind in ['landing','landing_reachable']:
            from .landing import LandingWalker,ReachableLandingWalker
            w.walker=(ReachableLandingWalker if a.kind=='landing_reachable' else LandingWalker)(w,steps,params)
        elif a.kind in ['reachable','reachable_inverse']:
            from .reachable import ReachableWalker,ReachableInverseWalker
            w.walker=(ReachableInverseWalker if a.kind=='reachable_inverse' else ReachableWalker)(w,steps,params)
        elif a.kind=='native_residual':
            from ..richdesk.reference import ReferenceWalker,Parameters
            from ..curriculum.world import SCALE
            w.walker=ReferenceWalker(w.m,w.d,SCALE,w.walker.offsets,w.terrain_height,w.meta['pelvis_height_m'],Parameters(lift=a.lift,terrain_gain=a.terrain_gain,target_tau=.012))
        elif a.kind=='hub':
            from .onnx_walk import HubWalker
            w.walker=HubWalker(w)
        else:
            from .preview import PreviewWalker,PreviewInverseWalker
            w.walker=(PreviewInverseWalker if a.kind=='preview_inverse' else PreviewWalker)(w,params)
        next_report=2.
        book_dwell=0.;book_verified=False;holding=False
        while w.d.time<a.seconds and not w.stopped:
            if getattr(w.walker,'failed_reason',None)=='no_reachable_support_pose':break
            reached=(abs(w.d.qpos[1]-.035)<.018) if a.kind=='hub' else (w.d.qpos[1]>=.025) if a.kind=='native_residual' else (a.kind not in ['preview','preview_inverse'] and w.walker.steps>=len(steps))
            if reached or holding:
                if a.kind=='hub':
                    loads=w.loads()
                    rows=w.measurements
                    recent=next((r for r in reversed(rows) if rows[-1]['t']-r['t']>=.10),rows[0])
                    average_velocity=(w.d.qpos[:2]-np.array(recent['root'][:2]))/max(.001,float(w.d.time)-recent['t'])
                    if not holding and np.linalg.norm(average_velocity)<.015 and np.linalg.norm(w.d.qvel[:2])<.08 and all(v>.05 for v in loads.values()):
                        from .onnx_walk import HoldWalker
                        w.walker=HoldWalker(w);holding=True
                    if holding:
                        w.step((0,0,0));book_dwell=book_dwell+w.m.opt.timestep if book_top(w)['instant_valid'] and not w.stopped else 0.
                        if book_dwell>=.4:book_verified=True;break
                        continue
                else:
                    w.step(standing=True)
                    book_dwell=book_dwell+w.m.opt.timestep if book_top(w)['instant_valid'] and not w.stopped else 0.
                    if book_dwell>=.4:book_verified=True;break
                    continue
            if a.kind in ['native_residual','hub']:
                lateral=float(np.clip((w.d.qpos[0]+.375)*.8,-.025,.025));turn=float(np.clip((math.pi/2-w.yaw())*2,-.6,.6))
                forward=float(np.clip((.035-w.d.qpos[1])*.6,-.035,a.speed)) if a.kind=='hub' else a.speed
                w.step((forward,lateral,turn))
            else:w.step((.025,0,0))
            if w.d.time>next_report:
                print(json.dumps({'id':a.id,'t':round(w.d.time,2),'steps':getattr(w.walker,'steps',0),'phase':getattr(w.walker,'stage','native'),'root':w.d.qpos[:3].round(4).tolist()}),flush=True);next_report+=2
        episode=w.episode();r={'id':a.id,'kind':a.kind,'parameters':asdict(params),'duration':float(w.d.time),
            'fall':w.fall,'invalid_contact':w.invalid_contact,'balance_metrics':episode['balance_metrics'],
            'book_top':book_top(w),'book_top_dwell_s':book_dwell,'book_ascent_verified':book_verified,
            'controller':w.walker.description(),'wall_seconds':time.perf_counter()-started,
            'sources':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT/'src/mochi/balanced').glob('*.py')}}
        (OUT/(a.id+'.json')).write_text(json.dumps({'result':r,'episode':episode},separators=(',',':')))
        finish(a.id,{'status':'completed','duration':float(w.d.time),'fall':w.fall,'invalid_contact':w.invalid_contact})
        print(json.dumps({k:v for k,v in r.items() if k not in ['controller','sources','parameters']}),flush=True)
    except Exception as e:
        finish(a.id,{'status':'failed','error':type(e).__name__});raise


if __name__=='__main__':main()
