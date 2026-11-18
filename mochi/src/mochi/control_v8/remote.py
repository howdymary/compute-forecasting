"""Bounded Modal physics, real model inference, and branch-labeled supervision."""
import asyncio,dataclasses,os,pickle,time,math,platform
import modal
from ..curriculum.remote import base_image,with_assets
app=modal.App('mochi-control-v8')
image=with_assets(base_image.pip_install('httpx==0.28.1','tinker==0.39.0','tinker-cookbook==0.6.1','transformers==5.23.0'))
secret=modal.Secret.from_dict({k:os.environ[k] for k in ['TINKER_API_KEY'] if k in os.environ})
def sampler_payload(sampler):
 state=sampler._pickle_state();state=dataclasses.replace(state,holder=dataclasses.replace(state.holder,api_key=None,default_headers_overrides={}));payload=pickle.dumps(state)
 if os.environ.get('TINKER_API_KEY') and os.environ['TINKER_API_KEY'].encode() in payload:raise RuntimeError('Credential in sampling payload')
 return payload
def receipt(start,rollouts):return {'provider':'Modal','cpu':1,'memory_mib':3072,'wall_seconds':time.perf_counter()-start,'physical_rollouts':rollouts,'architecture':platform.machine()}
def route_observation(r):
 s=r.status()
 if s['mode']=='task':s['observation']['relative_position_mm']=((__import__('numpy').array(r.route['legs'][r.index]['goal'][:2])-r.w.d.qpos[:2])*1000).round(1).tolist()
 return s

@app.function(image=image,cpu=1,memory=3072,max_containers=4,timeout=3600)
def collect_teacher(seed,route):
 from .runner import ControlRunner
 from ..planning.follower import teacher
 from ..curriculum.world import PROFILES
 from .manipulation import PRESSES
 from .recovery import RECOVERIES,snapshot,restore,recover,observation
 from .decisions import encode
 import hashlib,json
 start=time.perf_counter();r=ControlRunner(route);r.reset(seed,True);examples=[];trials=[];branches=[];count=1
 for _ in range(1500):
  s=route_observation(r)
  if s['mode']=='done':break
  obs=s['observation'];task=s['station']
  if s['mode']=='walk':action=teacher(obs)
  else:
   snap=snapshot(r.w);snap['task']=task;snap_hash=hashlib.sha256(json.dumps(snap,sort_keys=True).encode()).hexdigest();outcomes=[]
   options=(PRESSES if task=='laptop' else [p for p in PROFILES if p.code in ['A','B','C']]) if s['mode']=='task' else RECOVERIES
   for p in options:
    w=restore(snap,False);result=w.do_task(task,p) if s['mode']=='task' else recover(w,task,p);outcomes.append({'action':p.code,'result':result,'initial_state_sha256':snap_hash});count+=1
   trials.append({'domain':obs['domain'],'task':task,'observation':obs,'snapshot':snap,'outcomes':outcomes});candidates=[o for o in outcomes if o['result']['success']]
   if not candidates:return {'seed':seed,'valid':False,'failure_domain':obs['domain'],'failure_task':task,'trials':trials,'examples':examples,'episode':r.w.episode(),'receipt':receipt(start,count)}
   best=min(candidates,key=lambda o:(o['result']['duration'] if s['mode']=='task' else o['result']['duration_s'],o['result'].get('arm_joint_travel_rad',o['result'].get('max_force_n',0))));action=best['action']
  examples.append({'observation':obs,'model_observation':encode(obs),'action':action,'domain':obs['domain'],'task':task,'t':float(r.w.d.time)});r.advance(action)
  if s['mode']!='walk' and not (r.w.results[task]['success'] if s['mode']=='task' else r.w.recoveries[-1]['success']):
   examples.pop();return {'seed':seed,'valid':False,'failure_domain':obs['domain'],'failure_task':task,'trials':trials,'examples':examples,'episode':r.w.episode(),'receipt':receipt(start,count)}
 from .verification import full_success,sequence_success
 row=r.result();return {'seed':seed,'valid':sequence_success(row),'examples':examples,'trials':trials,'row':row,'receipt':receipt(start,count)}

@app.function(image=image,secrets=[secret],cpu=1,memory=3072,max_containers=4,timeout=3600)
def evaluate(seed,route,models,fixed,recovery_fixed,record=True):
 async def run():
  import tinker,torch,mujoco,numpy
  from tinker.lib.public_interfaces.sampling_client import _unpickle_sampling_client
  from tinker_cookbook import model_info,renderers
  from tinker_cookbook.recipes.decisions import DecisionRenderer
  from .runner import ControlRunner
  from .legacy import LegacyRunner
  from ..curriculum.features import CachedSelector
  from .decisions import Selector,encode
  from ..planning.follower import teacher
  from .verification import full_success,sequence_success
  start=time.perf_counter();results={}
  for label,payload in models:
   sampler=_unpickle_sampling_client(pickle.loads(payload)) if payload else None;renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'),sampler.get_tokenizer())) if sampler else None;legacy=label=='legacy_original_stack';selector=CachedSelector() if legacy else Selector();r=LegacyRunner() if legacy else ControlRunner(route);r.reset(seed,record);decisions=[]
   for _ in range(1500):
    s=r.status() if legacy else route_observation(r)
    if s['mode']=='done':break
    obs=s['observation']
    if sampler:action,distribution=await selector(sampler,renderer,obs)
    else:action=teacher(obs) if s['mode']=='walk' else fixed[s['station']] if s['mode']=='task' else recovery_fixed[s['station']];distribution=None
    decisions.append({'t':float(r.w.d.time),'observation':obs,'model_observation':obs if legacy else encode(obs),'action':action,'distribution':distribution});r.advance(action)
   row=r.result();row.update(model_decisions=decisions,inference=selector.receipt(),full_success=full_success(row['episode']) if legacy else sequence_success(row));results[label]=row
  return {'seed':seed,'results':results,'receipt':{**receipt(start,len(models)),'paired_on_one_worker':True,'torch':str(torch.__version__),'mujoco':mujoco.__version__,'numpy':numpy.__version__,'keys_serialized':False}}
 return asyncio.run(run())
