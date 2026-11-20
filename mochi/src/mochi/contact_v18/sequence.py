"""Uninterrupted evaluations with the frozen extended action library."""
import time
from ..balanced.onnx_walk import HubWalker,HoldWalker
from ..balanced.sequence import PhysicalStop
from ..control_v8.verification import full_success
from ..curriculum.world import TASKS
from ..smooth_v16.navigation import travel_metrics
from .world import ContactWorld as EfficientWorld
from ..smooth_v16.sequence import leg
from .policy import choices,execute,fixed

def run(seed, record=True, choose=None, until='all'):
    w=EfficientWorld(seed,record)
    w.terrain_controller_history=[]
    w.use_native_stand=True
    start=time.perf_counter()
    arrivals=[]
    failure=None
    try:
        while w.d.time<.4:
            w.step(standing=True)
        w.walker=HubWalker(w)
        w.walker=HoldWalker(w)
        for task in TASKS:
            for domain,default in [('walk','W0'),(task,{'alarm':'F','drawer':'B','laptop':'P0','globe':'A'}[task]),
                                   ('recovery','R1' if task=='alarm' else 'R0')]:
                available=choices(domain,task)
                code=(choose or fixed)(w,domain,task,default,available)
                result=execute(w,domain,task,code)
                success=all(a['success'] for a in result) if domain=='walk' else result['success']
                if not success:
                    raise PhysicalStop(domain+'-failed:'+task)
                if domain=='walk':
                    arrivals+=result
                else:
                    print(f'{domain} {task} {code}: passed at {w.d.time:.2f}s',flush=True)
            if until==task:
                break
        end=float(w.d.time)+.5
        while w.d.time<end:
            w.step()
    except PhysicalStop as exc:
        failure=str(exc)
    e=w.episode()
    complete=bool(until=='all' and not failure and full_success(e) and not w.invalid_contact and e['efficiency_validity']
        and e['maximum_applied_base_force']==0 and len(w.recoveries)==4
        and all(r['success'] for r in w.recoveries) and all(w.foot_touching(s) for s in ['left','right'])
        and any(a['label']=='book-ascent' for a in arrivals)
        and any(a['label']=='book-top-turnaround' and a['success'] for a in arrivals)
        and any(a['label']=='book-forward-descent' for a in arrivals)
        and bool(e.get('postit_crossings')))
    return {'study':'mochi-contact-v18','seed':seed,'complete_sequence_success':complete,
            'failure':failure,'arrivals':arrivals,'episode':e,'terrain_conditions':w.terrain_conditions,
            'direction_metrics':travel_metrics(w.direction_samples),'wall_seconds':time.perf_counter()-start,
            'scope':'Uninterrupted physical sequence; fixed native gait, directional controller and action library. Model attribution recorded by caller.'}
