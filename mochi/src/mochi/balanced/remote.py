"""Bounded V11 remote physical reference probes; no jobs run on import."""
import time
import modal
from ..curriculum.remote import ROOT,base_image,with_assets

app=modal.App('mochi-balanced-v11-engineering')
image=(with_assets(base_image.pip_install('onnxruntime==1.32.0'))
       .add_local_dir(ROOT/'configs',remote_path='/app/configs')
       .add_local_dir(ROOT/'assets/robot/g1-v11-policy',remote_path='/app/assets/robot/g1-v11-policy'))

@app.function(image=image,cpu=1,memory=2048,max_containers=4,timeout=180)
def reference(parameters):
    from .sequence import run
    started=time.perf_counter()
    row=run(seed=31000,record=True,until='all',**parameters)
    row['receipt']={'provider':'Modal','physical_rollouts':1,'cpu':1,'memory_mib':2048,
                    'duration_seconds':time.perf_counter()-started,'optimizer_updates':0,
                    'seed_partition':'engineering','held_out_opened':False}
    return row
