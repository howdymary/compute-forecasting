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

@app.function(image=image,cpu=1,memory=2048,max_containers=4,timeout=900)
def sequence(seed,route,profiles=None,old=False):
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
