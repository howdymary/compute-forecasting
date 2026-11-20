"""Bounded real physics, paired reset evaluations and measured training branches."""
import asyncio,gzip,hashlib,json,time
from pathlib import Path
import modal
from ..terrain_v12.learning_remote import image as base_image,secret,receipt
from ..terrain_v13.remote import Selector as BaseSelector
from ..smooth_v16.remote import physical_hash
from .public import export_clip
from ..smooth_v16.world import state
from .objective import valid_branch,branch_rank,branch_metrics
from ..balanced.sequence import PhysicalStop
from .world import restore
from .sequence import run
from .policy import observation,decision,choices,execute,fixed

VOLUME='mochi-contact-v18-artifacts'
image=base_image.env({'PYTHONHASHSEED':'0'})
volume=modal.Volume.from_name(VOLUME,create_if_missing=True)
app=modal.App('mochi-contact-v18-learning')

def archive(row,run_id,name):
 raw=json.dumps(row,separators=(',',':')).encode();p=Path('/artifacts')/run_id/(name+'.json.gz')
 assert not p.exists(),'Preserve immutable evidence'
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(raw,compresslevel=1));volume.commit()
 return {'volume':VOLUME,'path':str(p.relative_to('/artifacts')),'uncompressed_sha256':hashlib.sha256(raw).hexdigest()}

def compact(row):
 for k in ['trajectory','balance_measurements','control_telemetry']:row['episode'].pop(k,None)
 return row

class Selector(BaseSelector):
 async def select(self,obs):
  from tinker_cookbook.recipes.decisions import sample_decision
  key=json.dumps(obs,sort_keys=True)
  if key not in self.cache:
   rendered=self.renderer.render(decision(obs));n=len(rendered.tokens)+1
   if self.used+n>self.cap:raise PhysicalStop('inference_token_limit')
   self.used+=n;dist=await sample_decision(self.sampler,rendered)
   self.cache[key]=(max(dist,key=dist.get),dist)
  return self.cache[key]

@app.function(image=image,secrets=[secret],cpu=1,memory=4096,max_containers=4,timeout=2400,
              retries=0,volumes={'/artifacts':volume})
def evaluate(seed,models,run_id,group):
 started=time.perf_counter()
 async def body():
  rows={};tokens=0
  for label,payload,static in models:
   selector=Selector(payload) if payload else None
   if selector:selector.setup()
   decisions=[]
   def choose(w,domain,task,default,available):
    obs=observation(w,domain,task)
    if selector:action,dist=selector.sync(obs)
    elif static:action,dist=static[domain+':'+task],None
    else:return fixed(w,domain,task,default,available)
    item={'t':float(w.d.time),'observation':obs,'action':action,'distribution':dist,
          'initial_physical_state_sha256':physical_hash(w),
          'source':'Tinker saved checkpoint' if selector else 'training-derived static control'}
    decisions.append(item);w.decisions.append(item);return action
   row=await asyncio.to_thread(run,seed,True,choose=choose)
   row['model_decisions']=decisions
   row['archive']=archive(row,run_id,f'{group}-{seed}-{label}')
   clip=export_clip(row,run_id,f'{group}-{seed}-{label}',volume);clip['volume']=VOLUME
   row['public_recording']=clip;rows[label]=compact(row)
   tokens+=selector.used if selector else 0
  return {'seed':seed,'rows':rows,'receipt':{**receipt(started,len(models)),
        'inference_input_plus_max_output_tokens':tokens,'paired_same_process':len(models)>1}}
 return asyncio.run(body())

@app.function(image=image,secrets=[secret],cpu=1,memory=4096,max_containers=4,timeout=7200,
              retries=0,volumes={'/artifacts':volume})
def collect(seed,payload,run_id):
 started=time.perf_counter()
 async def body():
  selector=Selector(payload);selector.setup();count=1;examples=[];trials=[]
  def choose(w,domain,task,default,available):
   nonlocal count
   observed=observation(w,domain,task);preferred,dist=selector.sync(observed)
   planned=([preferred,'W2'] if task=='alarm' else [preferred,'W5','W8'] if task!='globe' else
      [preferred,'W5','W6','W8']) if domain=='walk' else (
      [preferred,'R0','R4'] if domain=='recovery' else [preferred,'P4','P5','P6'] if task=='laptop' else
      [preferred,'H0'] if task=='alarm' else [preferred,'G0'] if task=='globe' else [preferred,'B'])
   candidates=[x for x in dict.fromkeys(planned) if x in available];snapshot=state(w,include_history=False);initial=physical_hash(w)
   outcomes=[]
   for action in candidates:
    count+=1
    if count>35:raise PhysicalStop('collection_attempt_ceiling')
    clone=restore(snapshot,False);assert physical_hash(clone)==initial
    start=float(clone.d.time);index=len(clone.measurements);detail={};withdrawal=None;failure=None
    print(json.dumps({'seed':seed,'domain':domain,'task':task,'branch':action,'attempt':count}),flush=True)
    try:
     detail=execute(clone,domain,task,action)
     success=all(x['success'] for x in detail) if domain=='walk' else detail['success']
     if success and domain not in ['walk','recovery']:
      withdrawal=execute(clone,'recovery',task,'R4');success=success and withdrawal['success']
    except PhysicalStop as exc:success=False;failure=str(exc)
    episode=clone.episode()
    result={'action':action,'success':bool(success),'failure':failure,'result':detail,
      'coupled_recovery':withdrawal,'duration_s':float(clone.d.time)-start,
      'steps':clone.step_counter.summary(since=start),'metrics':branch_metrics(clone.measurements[index:]),
      'native_smoothness':episode['native_smoothness'],
      'longest_unsupported_seconds':episode['longest_unsupported_seconds'],
      'fall':clone.fall,'invalid_contact':clone.invalid_contact,'initial_state_sha256':initial}
    result['flat_foot_clearance']=episode.get('flat_foot_clearance')
    result['archive']=archive(result,run_id,f'branch-{seed}-{domain}-{task}-{action}')
    outcomes.append(result)
   trial={'domain':domain,'task':task,'observation':observed,'student_preference':preferred,
          'student_distribution':dist,'outcomes':outcomes}
   trials.append(trial)
   valid=[r for r in outcomes if valid_branch(r)]
   if not valid:raise PhysicalStop('teacher_no_valid_action:'+domain+':'+task)
   best=min(valid,key=lambda r:branch_rank(domain,r));action=best['action']
   examples.append({'domain':domain,'task':task,'observation':observed,'action':action,
        'student_distribution':dist,'guard_intervened':action!=preferred,
        'initial_state_sha256':initial,'outcomes_sha256':hashlib.sha256(json.dumps(outcomes,sort_keys=True).encode()).hexdigest()})
   w.decisions.append({'t':float(w.d.time),'observation':observed,'action':action,'source':'guarded measured training branches'})
   return action
  row=await asyncio.to_thread(run,seed,False,choose=choose)
  result={'seed':seed,'valid':row['complete_sequence_success'],'row':row,'examples':examples,'trials':trials}
  result['archive']=archive(result,run_id,f'teacher-{seed}')
  compact(row)
  result['receipt']={**receipt(started,count),'inference_input_plus_max_output_tokens':selector.used}
  return result
 return asyncio.run(body())
