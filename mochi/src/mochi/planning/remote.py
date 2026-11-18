"""Bounded planning calibration on Modal; no model optimization or saving."""
import math,time,modal
from ..curriculum.remote import base_image,with_assets
app=modal.App('mochi-route-planning-v1')
image=with_assets(base_image)

@app.function(image=image,cpu=1,memory=2048,max_containers=4,timeout=600)
def contact(seed,task,code,pose):
 import mujoco
 from ..curriculum.world import World,PROFILES
 start=time.perf_counter();w=World(seed,False,start_task=task);w.d.qpos[:2]=pose[:2];w.d.qpos[3:7]=[math.cos(pose[2]/2),0,0,math.sin(pose[2]/2)];mujoco.mj_forward(w.m,w.d);obs=w.task_observation(task);result=w.do_task(task,next(p for p in PROFILES if p.code==code))
 return {'seed':seed,'task':task,'pose':pose,'observation':obs,'result':result,'receipt':{'provider':'Modal','cpu':1,'wall_s':time.perf_counter()-start,'mujoco':mujoco.__version__,'isolated_initialization_before_physics':True}}

def execute_sequence(seed,route,profiles=None,old=False):
 start=time.perf_counter()
 if old:
  from ..curriculum.remote import Runner
  from ..curriculum.world import World
  r=Runner();status=r.reset(seed,True)
  for _ in range(600):
   if status['mode']=='done':break
   obs=status['observation'];a=World.teacher_move(obs) if obs['domain']=='walk' else {'alarm':'B','drawer':'A','laptop':'C','globe':'A'}[obs['domain']];status=r.advance(a)
  row={'seed':seed,'mode':status['mode'],'arrivals':r.arrivals,'episode':r.w.episode(),'label':'old_reference_fixed_controller'}
 else:
  from .follower import PathRunner,teacher
  r=PathRunner(route);status=r.reset(seed,True)
  for _ in range(1200):
   if status['mode']=='done':break
   obs=status['observation'];a=teacher(obs) if obs['domain']=='walk' else profiles[obs['domain']][obs.get('material_cue','default')] if isinstance(profiles[obs['domain']],dict) else profiles[obs['domain']];status=r.advance(a)
  row=r.result();row['label']='new_reference_fixed_controller'
 row['receipt']={'provider':'Modal','cpu':1,'wall_s':time.perf_counter()-start,'no_tinker_optimizer_updates':True};return row

@app.function(image=image,cpu=1,memory=2048,max_containers=4,timeout=900)
def sequence(seed,route,profiles=None,old=False):return execute_sequence(seed,route,profiles,old)

@app.function(image=image,cpu=1,memory=2048,max_containers=4,timeout=1800)
def sequence_pair(seed,route,profiles):
 # Both methods run on the same CPU worker from exactly the same reset seed.
 return {'seed':seed,'old':execute_sequence(seed,route,profiles,True),'new':execute_sequence(seed,route,profiles,False),'paired_on_one_worker':True}

@app.function(image=image,cpu=1,memory=2048,max_containers=1,timeout=300)
def navigation_probe(kind):
 from .follower import PathRunner,teacher
 import mujoco
 start=time.perf_counter();pose=[-.45,-.15,0.];goal=[-.30,-.15,0.] if kind=='repeat_stop_probe' else [-.45,-.15,math.pi/2];length=math.dist(pose[:2],goal[:2]);route={'version':'training-only-'+kind,'legs':[{'task':'alarm','goal':goal,'segments':[{'from':pose[:2],'to':goal[:2],'heading':0.,'command':'forward','length_m':length}]}]};r=PathRunner(route);r.reset(19004,True);r.w.d.qpos[:2]=pose[:2];r.w.d.qpos[3:7]=[1,0,0,0];mujoco.mj_forward(r.w.m,r.w.d);r.w.frames=[];r.w.capture();status=r.status()
 for _ in range(250):
  if status['mode']!='walk':break
  status=r.advance(teacher(status['observation']))
 row=r.result();row['probe']=kind;row['receipt']={'provider':'Modal','cpu':1,'wall_s':time.perf_counter()-start,'isolated_initialization_before_physics':True};return row
