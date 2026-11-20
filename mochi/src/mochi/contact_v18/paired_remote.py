"""More time for two unchanged evaluations in the same worker.

Only the runtime envelope changes. The original single-episode evaluator,
physics, controller library and task checks remain untouched.
"""
import time
from .remote import app, image, secret, volume, evaluate
from ..terrain_v12.learning_remote import receipt


@app.function(image=image,secrets=[secret],cpu=1,memory=4096,max_containers=4,
              timeout=3600,retries=0,volumes={'/artifacts':volume})
def evaluate_pair(seed,models,run_id,group):
    assert len(models)==2
    started=time.perf_counter()
    answer=evaluate.local(seed,models,run_id,group)
    answer['receipt']['duration_seconds']=time.perf_counter()-started
    answer['receipt']['paired_runtime_seconds_max']=3600
    answer['receipt']['runtime_scope']='Original evaluator called locally inside the same worker; timeout envelope only.'
    return answer


@app.function(image=image,secrets=[secret],cpu=1,memory=4096,max_containers=1,
              timeout=120,retries=0,volumes={'/artifacts':volume})
def probe_pair_wrapper(seed,run_id,group):
    """Reach the unchanged action validator through both local-call layers."""
    started=time.perf_counter()
    try:
        evaluate_pair.local(seed,[('invalid-static',None,{'walk:alarm':'INVALID'}),
                                  ('not-reached',None,None)],run_id,group)
    except ValueError as exc:
        assert str(exc)=='Unavailable action'
        return {'seed':seed,'expected_error':str(exc),'receipt':receipt(started,1),
                'scope':'Intentional invalid-action diagnostic after the original 0.4-second physical initialization. One failed attempt charged; no successful task or training label.'}
    raise AssertionError('The original invalid-action validator did not run')
