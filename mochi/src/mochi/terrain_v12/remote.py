"""Bounded cloud diagnostics; no jobs or training launch on import."""
import time
import modal
from ..curriculum.remote import ROOT,base_image,with_assets

image=(with_assets(base_image.pip_install('onnxruntime==1.32.0','osqp==1.1.1'))
       .add_local_dir(ROOT/'configs',remote_path='/app/configs')
       .add_local_dir(ROOT/'assets/robot/g1-v11-policy',remote_path='/app/assets/robot/g1-v11-policy'))

app=modal.App('mochi-terrain-v12-controller-lab')

@app.function(image=image,cpu=.25,memory=2048,max_containers=1,timeout=60)
def runtime_check():
    import hashlib,inspect
    import mujoco,numpy,osqp
    from .contact import ContactWalker
    started=time.perf_counter();loaded=inspect.getfile(ContactWalker)
    assert hashlib.sha256(open(loaded,'rb').read()).digest()==hashlib.sha256((ROOT/'src/mochi/terrain_v12/contact.py').read_bytes()).digest()
    return {'mujoco':mujoco.__version__,'numpy':numpy.__version__,'osqp':osqp.__version__,
            'physical_rollouts':0,'cpu':.25,'duration_seconds':time.perf_counter()-started,'controller_code_matches':True}

@app.function(image=image,cpu=1,memory=3072,max_containers=4,timeout=900)
def traversal(seed,parameters,label):
    from .probe import run
    started=time.perf_counter();row=run(160.,.025,'contact',parameters,seed)
    row.update(variant=label,seed=seed,receipt={'provider':'Modal','cpu':1,'memory_mib':3072,
         'physical_rollouts':1,'duration_seconds':time.perf_counter()-started,'optimizer_updates':0})
    return row
