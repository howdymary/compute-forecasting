"""Separate Modal app. Parent forecasting apps, volumes and model weights untouched."""
import modal
from .simulation import ROOT

image=modal.Image.debian_slim(python_version='3.11').pip_install('mujoco==3.3.7','numpy==2.3.4').env({'PYTHONPATH':'/app/src'}).add_local_dir(ROOT/'src',remote_path='/app/src').add_local_dir(ROOT/'configs',remote_path='/app/configs')
app=modal.App('mochi-robot-lab')

@app.function(image=image,cpu=1,memory=1024,timeout=180,max_containers=8)
def trial(policy,seed,shift=False):
    import time,platform
    from .simulation import rollout,Policy
    start=time.perf_counter();r=rollout(Policy(**policy),seed,shift)
    r['remote_receipt']={'provider':'Modal','duration_seconds':time.perf_counter()-start,'python':platform.python_version(),'cpu_requested':1,'memory_mib':1024}
    return r

async def batch(policy,seeds,shift=False):return [r async for r in trial.starmap.aio([(policy,s,shift) for s in seeds])]
