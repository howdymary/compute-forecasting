"""Saved physical engineering states for isolated diagnostics, never demos.

Only load these local pickle files produced by this module. A branched
descent is labelled explicitly and cannot qualify as a continuous sequence.
"""
import argparse,copy,hashlib,json,pickle,time
import mujoco,numpy as np
from .world import TerrainWorld
from .contact import descent_landings
from .sequence import book_leg
from .budget import reserve,finish,OUT
from ..balanced.sequence import PhysicalStop
from ..balanced.onnx_walk import HubWalker,HoldWalker
from ..balanced.snapshot import MODEL_FIELDS

HOLD_FIELDS=['target','initial_target','neutral','origin','final_target','standing_target','previous_description','native_state']

def state(w):
    assert isinstance(w.walker,HoldWalker)
    skip={'m','d','viz','walker'}
    return {'world':{k:copy.deepcopy(v) for k,v in w.__dict__.items() if k not in skip},
            'data':copy.copy(w.d),'model':{k:getattr(w.m,k).copy() for k in MODEL_FIELDS},
            'walker':{k:copy.deepcopy(getattr(w.walker,k)) for k in HOLD_FIELDS}}

def restore(saved,record=False):
    values=saved['world'];w=TerrainWorld(values['s']['seed'],False,scene=values['scene'])
    for k,v in saved['model'].items():getattr(w.m,k)[:]=v
    for k,v in values.items():setattr(w,k,copy.deepcopy(v))
    w.d=copy.copy(saved['data']);ctrl=w.d.ctrl.copy();w.walker=HubWalker(w);w.walker=HoldWalker(w)
    for k,v in saved['walker'].items():setattr(w.walker,k,copy.deepcopy(v))
    w.d.ctrl[:]=ctrl;w.record=record;return w

def main():
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--prefix',action='store_true')
    p.add_argument('--parameters',default='{}');p.add_argument('--short',action='store_true');a=p.parse_args()
    reserve(a.id,vars(a));start=time.perf_counter();parameters={'width':.024,'balance_feedback':.5,'descent_lift':.006,**json.loads(a.parameters)}
    try:
        if a.prefix:
            w=TerrainWorld(41000,True);w.terrain_controller_history=[]
            while w.d.time<.4:w.step(standing=True)
            arrival=book_leg(w,1,parameters);saved=state(w)
            # Exact next-step equality is required before using a branch.
            x,y=restore(saved),restore(saved);x.step();y.step()
            assert np.array_equal(x.d.qpos,y.d.qpos) and np.array_equal(x.d.qvel,y.d.qvel)
            with (OUT/'supported-ascent-state.pickle').open('wb') as f:pickle.dump(saved,f)
            row={'scope':'Engineering prefix only; not a four-task run','arrival':arrival,'clone_next_step_exact':True,'episode':w.episode()}
        else:
            with (OUT/'supported-ascent-state.pickle').open('rb') as f:saved=pickle.load(f)
            w=restore(saved,True);begin=float(w.d.time);failure=None;arrival=None
            try:arrival=book_leg(w,-1,parameters,landings=descent_landings(w,parameters['width'],a.short))
            except PhysicalStop as e:failure=str(e)
            row={'scope':'Isolated descent development branch from measured supported ascent; never spliced into demo',
                 'failure':failure,'descent_success':arrival is not None,'arrival':arrival,'episode':w.episode(),
                 'branch_start_physical_time':begin,'controller':w.walker.description()}
        row.update(parameters=parameters,wall_seconds=time.perf_counter()-start)
        (OUT/(a.id+'.json')).write_text(json.dumps(row,separators=(',',':')))
        result={k:row[k] for k in ['failure','descent_success','wall_seconds'] if k in row};result['status']='completed'
        finish(a.id,result);print(json.dumps(result),flush=True)
    except Exception as exc:finish(a.id,{'status':'failed','error':type(exc).__name__});raise

if __name__=='__main__':main()
