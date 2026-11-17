"""Mochi-only CPU rollout workers. No provider credentials in the image."""
import time
from dataclasses import asdict
import modal
from .physics import ROOT

image=(modal.Image.debian_slim(python_version='3.11')
 .apt_install('libgl1','libglib2.0-0')
 .pip_install('mujoco==3.3.7','numpy==2.3.4')
 .env({'PYTHONPATH':'/app/src','MUJOCO_GL':'disable','MOCHI_ROOT':'/app'})
 .add_local_dir(ROOT/'src',remote_path='/app/src')
 .add_local_file(ROOT/'desk-protocol.json',remote_path='/app/desk-protocol.json'))
app=modal.App('mochi-desk-v3-lab')

@app.function(image=image,cpu=1,memory=1024,timeout=180,max_containers=8,retries=1)
def trial(policy,seed,record=False):
    from .physics import Controller,rollout
    start=time.perf_counter();r=rollout(Controller(**policy),seed,record)
    r['remote_receipt']={'provider':'Modal','duration_seconds':time.perf_counter()-start,'cpu':1,'memory_mib':1024}
    return r

async def grid(catalog,seeds,record=False):
    jobs=[(asdict(c),s,record) for s in seeds for c in catalog]
    rows=[r async for r in trial.starmap.aio(jobs,order_outputs=True)]
    return [rows[i:i+len(catalog)] for i in range(0,len(rows),len(catalog))]
