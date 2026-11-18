"""Evaluate fixed Tinker snapshots in one continuous Modal physics process.

The SDK's documented multiprocessing serialization is stripped of credentials.
Workers receive the existing key only as a backend Modal secret.
"""
import asyncio,dataclasses,os,pickle,time,platform
import modal
from .remote import base_image,with_assets,Runner
from .world import World
app=modal.App('mochi-curriculum-v6-closed-loop')
image=with_assets(base_image.pip_install('httpx==0.28.1','tinker==0.39.0','tinker-cookbook==0.6.1','transformers==5.23.0'))
backend_key=modal.Secret.from_dict({k:os.environ[k] for k in ['TINKER_API_KEY'] if k in os.environ})

def sampler_payload(sampler):
 state=sampler._pickle_state();state=dataclasses.replace(state,holder=dataclasses.replace(state.holder,api_key=None,default_headers_overrides={}));payload=pickle.dumps(state)
 key=os.environ.get('TINKER_API_KEY','')
 if key and key.encode() in payload:raise RuntimeError('Refusing to serialize a credential')
 return payload

@app.function(image=image,secrets=[backend_key],cpu=1,memory=3072,max_containers=4,timeout=2400)
def evaluate_bundle(seed,models,fixed,goal_offset=None,record=False,probe=False):
 async def run():
  import mujoco,numpy,torch,tinker
  from tinker.lib.public_interfaces.sampling_client import _unpickle_sampling_client
  from tinker_cookbook import model_info,renderers
  from tinker_cookbook.recipes.decisions import DecisionRenderer
  from .decisions import choose
  start=time.perf_counter();results={}
  for label,payload in models:
   sampler=_unpickle_sampling_client(pickle.loads(payload)) if payload is not None else None
   renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'),sampler.get_tokenizer())) if sampler is not None else None
   r=Runner();status=r.reset(seed,record);actions=[];model_decisions=[]
   if goal_offset is not None:r.goal=(float(r.w.d.qpos[0])+goal_offset[0],float(r.w.d.qpos[1])+goal_offset[1],goal_offset[2]);status=r.status()
   for _ in range(1 if probe else 500):
    if status['mode']=='done' or goal_offset is not None and status['mode']!='walk':break
    obs=status['observation'];action,dist=(await choose(sampler,renderer,obs)) if sampler else ((World.teacher_move(obs) if obs['domain']=='walk' else fixed[obs['domain']]),None);actions.append(action);model_decisions.append({'observation':obs,'action':action,'distribution':dist});status=r.advance(action)
   episode=r.w.episode();results[label]={'seed':seed,'actions':actions,'model_decisions':model_decisions,'episode':episode,'arrivals':r.arrivals,'mode':status['mode'],'success':bool(status['mode']=='task' and not r.w.fall) if goal_offset is not None else None,'end_observation':r.w.walk_observation(r.goal) if goal_offset is not None else None}
  return {'seed':seed,'results':results,'receipt':{'provider':'Modal','cpu':1,'memory_mib':3072,'duration_seconds':time.perf_counter()-start,'architecture':platform.machine(),'python':platform.python_version(),'mujoco':mujoco.__version__,'numpy':numpy.__version__,'torch':torch.__version__,'paired_on_one_worker':True,'keys_serialized_in_payload':False}}
 return asyncio.run(run())
