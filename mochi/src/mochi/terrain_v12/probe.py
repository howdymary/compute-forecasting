"""Small recorded controller diagnostics with immutable receipts."""
import argparse,hashlib,json,math,time
import mujoco,numpy as np
from ..balanced.sequence import SequenceWorld,PhysicalStop
from ..balanced.onnx_walk import HubWalker
from .budget import reserve,finish,OUT

def run(horizon=3.,speed=.025,kind='native',parameters=None,seed=41000,short_descent=False):
    from pathlib import Path
    sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    snapshots=OUT/'source-snapshots';snapshots.mkdir(parents=True,exist_ok=True)
    for path,sha in sources.items():
        dest=snapshots/(sha+'.py')
        if not dest.exists():dest.write_bytes(Path(path).read_bytes())
    from .world import TerrainWorld
    w=TerrainWorld(seed,True);trace=[];failed=None;start=time.perf_counter();book_ascent=False;book_descent=False;dwell=0.;traversal='ascent';next_report=2.
    try:
        while w.d.time<.4:w.step(standing=True)
        if kind=='native':w.walker=HubWalker(w)
        elif kind=='quasi':
            from .quasi import QuasiWalker
            w.walker=QuasiWalker(w,**(parameters or {}))
        elif kind in ['contact','qp']:
            from .contact import ContactWalker
            from .qp import QpWalker
            w.walker=(QpWalker if kind=='qp' else ContactWalker)(w,**(parameters or {}))
        else:
            from .walker import TerrainWalker,PlannedSwingWalker
            w.walker=(PlannedSwingWalker if kind=='planned' else TerrainWalker)(w,**(parameters or {}))
        next_sample=0.
        while w.d.time<horizon:
            if kind in ['contact','qp'] and getattr(w.walker,'completed',False):
                from ..balanced.onnx_walk import HoldWalker
                w.walker=HoldWalker(w);dwell=0.
            if kind in ['contact','qp'] and isinstance(w.walker,__import__('mochi.balanced.onnx_walk',fromlist=['HoldWalker']).HoldWalker):
                from ..richdesk.verify import book_top
                good=book_top(w)['instant_valid'] if traversal=='ascent' else all(w.foot_touching(s) for s in ['left','right'])
                dwell=dwell+w.m.opt.timestep if good else 0.
                if dwell>=.4:
                    if traversal=='ascent':
                        book_ascent=True;traversal='descent'
                        from .contact import ContactWalker,descent_landings
                        width=(parameters or {}).get('width',.028)
                        landings=descent_landings(w,width,short_descent)
                        w.walker=(QpWalker if kind=='qp' else ContactWalker)(w,landings=landings,**(parameters or {}))
                    else:book_descent=True;break
            command_speed=-speed if traversal=='descent' else speed
            w.step((command_speed,float(np.clip((w.d.qpos[0]+.375)*.8,-.02,.02)),float(np.clip((math.pi/2-w.yaw())*2,-.6,.6))))
            if w.d.time>=next_report:
                print(json.dumps({'t':round(w.d.time,2),'steps':getattr(w.walker,'steps',None),'phase':getattr(w.walker,'stage',None),'traversal':traversal,'root':w.d.qpos[:3].round(4).tolist()}),flush=True);next_report+=5.
            if w.d.time>=next_sample:
                walker=w.walker
                scratch=mujoco.MjData(w.m);scratch.qpos[:]=w.d.qpos
                for q,target in zip(getattr(walker,'qmap',walker.qids),walker.target):
                    if q is not None:scratch.qpos[q]=target
                mujoco.mj_forward(w.m,scratch)
                trace.append({'t':float(w.d.time),'phase':(float(w.d.time)-walker.origin)/walker.time_scale%.6/.6 if hasattr(walker,'origin') else walker.stage,
                    'root':w.d.qpos[:3].tolist(),'loads':w.loads(),
                    'target_feet':{s:scratch.xpos[w.id('body',s+'_ankle_roll_link')].tolist() for s in ['left','right']},
                    'feet':{s:w.d.xpos[w.id('body',s+'_ankle_roll_link')].tolist() for s in ['left','right']},
                    'sole_patches':{s:w.sole_patch(s) for s in ['left','right']}})
                next_sample=float(w.d.time)+.01
    except PhysicalStop as e:failed=str(e)
    return {'study':'mochi-terrain-v12','parameters':{'kind':kind,'horizon':horizon,'speed':speed,'short_descent':short_descent,**(parameters or {})},'failure':failed,'book_ascent_verified':book_ascent,'book_descent_verified':book_descent,
        'wall_seconds':time.perf_counter()-start,'trace':trace,'episode':w.episode(),'controller':w.walker.description(),'source_sha256_at_start':sources}

def main():
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--kind',default='native');p.add_argument('--horizon',type=float,default=3.);p.add_argument('--speed',type=float,default=.025);p.add_argument('--parameters',default='{}');a=p.parse_args()
    reserve(a.id,vars(a))
    try:
        row=run(a.horizon,a.speed,a.kind,json.loads(a.parameters));(OUT/(a.id+'.json')).write_text(json.dumps(row,separators=(',',':')))
        result={'status':'completed','failure':row['failure'],'duration':row['episode']['duration'],'wall_seconds':row['wall_seconds'],'metrics':row['episode']['balance_metrics']};finish(a.id,result);print(json.dumps(result))
    except Exception as e:finish(a.id,{'status':'failed','error':type(e).__name__});raise

if __name__=='__main__':main()
