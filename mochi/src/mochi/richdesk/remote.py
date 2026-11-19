"""Small physical feasibility probes. No training or deployment on import."""
import time
import modal
from ..curriculum.remote import base_image,with_assets,ROOT

app=modal.App('mochi-richdesk-v10-feasibility')
image=with_assets(base_image.pip_install('osqp==1.1.1')).add_local_dir(ROOT/'configs',remote_path='/app/configs')

@app.function(image=image,cpu=1,memory=2048,max_containers=4,timeout=120)
def probe(seed,parameters,kind='wholebody',seconds=12.):
    from .world import DeskWorld
    from .wholebody import WholeBodyWalker
    from .stepping import StepParameters
    from .verify import book_top
    start=time.perf_counter();w=DeskWorld(seed,True)
    while w.d.time<.4:w.step(standing=True)
    if kind=='wholebody':w.walker=WholeBodyWalker(w,StepParameters(**parameters))
    while w.d.time<seconds and not w.fall:w.step((.025,0,0))
    return {'seed':seed,'parameters':parameters,'kind':kind,'episode':w.episode(),
      'controller':w.walker.description() if hasattr(w.walker,'description') else {'controller':'frozen-native'},
      'book_top':book_top(w),'receipt':{'provider':'Modal','cpu':1,'memory_mib':2048,
      'physical_rollouts':1,'wall_seconds':time.perf_counter()-start,'training_updates':0}}
