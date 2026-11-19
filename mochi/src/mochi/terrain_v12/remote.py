"""Bounded cloud diagnostics; no jobs or training launch on import."""
import time
import modal
from ..balanced.remote import image

app=modal.App('mochi-terrain-v12-controller-lab')

@app.function(image=image,cpu=1,memory=3072,max_containers=4,timeout=900)
def traversal(seed,parameters,label):
    from .probe import run
    started=time.perf_counter();row=run(160.,.025,'contact',parameters,seed)
    row.update(variant=label,seed=seed,receipt={'provider':'Modal','cpu':1,'memory_mib':3072,
         'physical_rollouts':1,'duration_seconds':time.perf_counter()-started,'optimizer_updates':0})
    return row
