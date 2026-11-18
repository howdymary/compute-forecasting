"""Held-out task/recovery tests independent of whether navigation succeeds."""
import asyncio,json,math,pickle,time,hashlib
from .remote import app,image,secret,receipt
@app.function(image=image,secrets=[secret],cpu=1,memory=3072,max_containers=4,timeout=2400)
def evaluate_isolated(seed,route,models):
 async def run():
  import mujoco,numpy as np
  from tinker.lib.public_interfaces.sampling_client import _unpickle_sampling_client
  from tinker_cookbook import model_info,renderers
  from tinker_cookbook.recipes.decisions import DecisionRenderer
  from .manipulation import ControlWorld,PRESSES
  if route.get('controller_revision')=='xy-support-v1':
   from .support import SupportWorld as ControlWorld
  from .recovery import snapshot,restore,recover,observation,RECOVERIES
  from .decisions import Selector
  from ..curriculum.world import PROFILES
  def restore_revision(state):
   trial=restore(state);trial.__class__=ControlWorld;return trial
  start=time.perf_counter();count=0;results=[];clients={}
  for label,payload in models:
   sampler=_unpickle_sampling_client(pickle.loads(payload));renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'),sampler.get_tokenizer()));clients[label]=(sampler,renderer,Selector())
  for leg in route['legs']:
   task=leg['task'];w=ControlWorld(seed,False,start_task=task);goal=leg['goal'];w.d.qpos[:2]=goal[:2];w.d.qpos[3:7]=[math.cos(goal[2]/2),0,0,math.sin(goal[2]/2)];mujoco.mj_forward(w.m,w.d);snap=snapshot(w);obs=w.task_observation(task);obs['relative_position_mm']=[0.,0.];options=PRESSES if task=='laptop' else PROFILES
   for label,(sampler,renderer,selector) in clients.items():
    trial=restore_revision(snap);action,dist=await selector(sampler,renderer,obs);result=trial.do_task(task,next(p for p in options if p.code==action));count+=1;results.append({'domain':'task','task':task,'model':label,'observation':obs,'action':action,'distribution':dist,'result':result,'initial_state_sha256':hashlib.sha256(json.dumps(snap,sort_keys=True).encode()).hexdigest()})
   # Predeclared engineering controls create a shared post-task recovery state.
   fixed={'alarm':'B','drawer':'A','laptop':'P1','globe':'A'};reference=restore_revision(snap);reference_result=reference.do_task(task,next(p for p in options if p.code==fixed[task]));count+=1
   if not reference_result['success']:
    results.append({'domain':'recovery_reference','task':task,'result':reference_result,'recovery_comparison':'unavailable; reference task failed'});continue
   post=snapshot(reference);obs=observation(reference,task);state_hash=hashlib.sha256(json.dumps(post,sort_keys=True).encode()).hexdigest()
   for label,(sampler,renderer,selector) in clients.items():
    trial=restore_revision(post);action,dist=await selector(sampler,renderer,obs);result=recover(trial,task,next(p for p in RECOVERIES if p.code==action));count+=1;results.append({'domain':'recovery','task':task,'model':label,'observation':obs,'action':action,'distribution':dist,'result':result,'initial_state_sha256':state_hash})
  return {'seed':seed,'results':results,'receipt':receipt(start,count),'inference':{label:client[2].receipt() for label,client in clients.items()}}
 return asyncio.run(run())
