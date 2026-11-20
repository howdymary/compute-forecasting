"""Real bounded Tinker continuation after the rejected V17 laptop study."""
import asyncio
from collections import Counter,defaultdict
import hashlib,json,os,time
from pathlib import Path
import modal
import numpy as np
from ..integrations import now,digest
from ..curriculum.world import ROOT,TASKS
from ..smooth_v16.parent import load_parent
from ..smooth_v16.objective import static_from_training
from .objective import summary,paired,select_checkpoint
from ..smooth_v17.finalize_memory import ReviewServices
from ..terrain_v12.learning_remote import sampler_payload
from ..maintenance.checkpoints_by_date import inventory
from .remote import app,evaluate,collect
from .policy import decision

OUT=ROOT/'artifacts/contact-v18-training'

def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True);p=OUT/(name+'.json');temp=p.with_suffix('.tmp')
 temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(p)

class Services(ReviewServices):
 def journal(self):save(self.run_id+'-memory-journal',{'pending':self.pending,'ready':self.records})

async def main():
 import tinker
 from tinker_cookbook.recipes.decisions import decision_choice_datums,sample_decision
 cfg=json.loads((ROOT/'configs/contact-v18-training.json').read_text())
 for p,h in cfg['frozen_sha256'].items():
  assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'Frozen source changed: '+p
 assert hashlib.sha256((ROOT/cfg['implementation_prompt']).read_bytes()).hexdigest()==cfg['prompt_sha256']
 previous,parent,parent_info=await load_parent(cfg)
 run_id='mochi-c18-'+os.environ['GITHUB_RUN_ID']
 progress=modal.Dict.from_name('mochi-contact-v18-progress',create_if_missing=True)
 assert await progress.get.aio(run_id) is None,'Existing campaign: inspect durable evidence before any retry'
 ledger=modal.Dict.from_name(run_id+'-budget',create_if_missing=True)
 usage={k:0 for k in cfg['bounds'] if k!='modal_concurrency'}
 usage.update(cfg['engineering_usage'])
 await ledger.put.aio('usage',usage)
 services=Services();services.run_id=run_id
 services.actors={role:run_id+'-'+role for role in ['researcher','designer','experimenter','critic']}
 services.audience,services.private=run_id+'-shared',run_id+'-critic'
 report={'study':cfg['study'],'run_id':run_id,'source_sha':os.environ['GITHUB_SHA'],
  'execution_source_sha':os.environ['GITHUB_SHA'],'created_at':now(),'protocol':cfg,
  'scope':cfg['scope'],'status':'running','phase':'Validate credentials, saved parent and frozen repair',
  'optimizer_updates_completed':0,'training_log':[],'checkpoints':[],'physics_receipts':[],
  'campaign_modal_rollouts_completed':0,'held_out_opened':False,'parent_selection':parent_info,
  'engineering_usage':cfg['engineering_usage']}
 lock=asyncio.Lock();publish_lock=asyncio.Lock();slots=asyncio.Semaphore(cfg['bounds']['modal_concurrency'])
 condition=asyncio.Condition(lock);reservations=0
 async def change(kind,n):
  async with lock:
   assert 0<=usage[kind]+n<=cfg['bounds'][kind], 'Budget limit: '+kind
   usage[kind]+=n;await ledger.put.aio('usage',dict(usage))
 async def publish():
  async with publish_lock:
   report['services']=services.report();report['budget_usage_or_reserved']=dict(usage)
   report['total_physical_attempts_accounted']=usage['physical_rollouts']
   report['total_physical_rollouts_completed']=cfg['engineering_usage']['physical_rollouts']+report['campaign_modal_rollouts_completed']
   save('progress',report);await progress.put.aio(run_id,report);await progress.put.aio('latest',report)
   print('MOCHI_CONTACT_V18 '+json.dumps({'phase':report['phase'],'updates':report['optimizer_updates_completed'],'usage':usage}),flush=True)
 async def write(role,value,private=False):
  assert len(json.dumps(value))<7000,'Keep memory compact; store exact arrays in artifacts'
  await change('past_writes',1);rid=await services.write(role,value,private);await publish();return rid
 async def read(role,rid,allowed=True):
  await change('past_recalls',1);value=await services.read(role,rid,allowed);await publish();return value
 async def batch(function,args,timeout,cap,token_cap):
  nonlocal reservations
  async def one(index,arg):
   nonlocal reservations
   async with slots:
    reserved={'physical_rollouts':cap,'simulation_cpu_hours':timeout/3600,'inference_tokens':token_cap}
    async with condition:
     while any(usage[k]+v>cfg['bounds'][k] for k,v in reserved.items()):
      if reservations==0:raise RuntimeError('No remaining resource reservation fits')
      await condition.wait()
     reservations+=1
     for k,v in reserved.items():usage[k]+=v
     await ledger.put.aio('usage',dict(usage))
    try:answer=await function.remote.aio(*arg)
    except BaseException:
     async with condition:reservations-=1;condition.notify_all()
     raise
    r=answer['receipt']
    actual={'physical_rollouts':r['physical_rollouts'],'simulation_cpu_hours':r['duration_seconds']/3600,
            'inference_tokens':r.get('inference_input_plus_max_output_tokens',0)}
    async with condition:
     for k,v in actual.items():
      usage[k]+=v-reserved[k];assert usage[k]<=cfg['bounds'][k]
     reservations-=1;await ledger.put.aio('usage',dict(usage));condition.notify_all()
    report['campaign_modal_rollouts_completed']+=r['physical_rollouts']
    report['physics_receipts'].append({'phase':report['phase'],'seed':answer['seed'],'receipt':r})
    key=('teacher-' if function is collect else str(arg[-1])+'-')+str(answer['seed'])
    save(key,answer);await publish();return answer
  return await asyncio.gather(*(one(i,arg) for i,arg in enumerate(args)))
 checkpoint_paths={};samplers={};development={}
 rng=np.random.default_rng(cfg['training']['seed'])
 try:
  assert len(await inventory(tinker.RestClient()))+5<100,'No checkpoint deletion is authorized'
  await services.setup();await publish()
  await change('exa_searches',1)
  sources=await services.search('humanoid robot quasi static laptop lid pushing contact force support polygon whole body manipulation balance')
  research=await write('researcher',{'kind':'hypothesis','experiment_id':run_id,
   'observation':'V17 selected model failed at laptop contact on all four opened cases; those cases are now regression evidence.',
   'engineering_evidence':cfg['engineering_evidence'],'sources':sources['sources'],
   'hypothesis':'A verified contact mechanism and arm posture can preserve support during lid closure. Evaluate the frozen repair; do not infer success from a source.'})
  context=await read('designer',research)
  allocation=await services.decide('designer','Choose a balanced six-domain training allocation or extra laptop/recovery examples.',
      context,['balanced','contact_and_recovery'],[research])
  design=await write('designer',{'kind':'experiment-plan','experiment_id':run_id,'allocation':allocation,
      'training_seeds':cfg['training_seeds'],'criteria':'Actual completed contact and safe withdrawal; fixed verifiers; no positive labels for failed branches.'})
  await read('experimenter',design)
  trainer=await services.service.create_training_client_from_state_with_optimizer(parent)
  samplers[0]=await trainer.save_weights_and_get_sampling_client(kind='snapshot')
  checkpoint_paths['0']={'optimizer':parent};save('checkpoint-paths',checkpoint_paths)
  async with app.run():
   report['phase']='Frozen repair preflight and untrained-parent development baseline';await publish()
   preflight=(await batch(evaluate,[(cfg['preflight_seed'],[('fixed',None,None)],run_id,'preflight')],2400,1,0))[0]['rows']['fixed']
   report['remote_reference']=preflight
   report['preflight_complete']=preflight['complete_sequence_success']
   # The preflight remains recorded even if this fixed heuristic fails. The
   # learning gate below requires both actually completed guarded sequences.
   baseline=await batch(evaluate,[(s,[('policy',sampler_payload(samplers[0]),None)],run_id,'dev-0') for s in cfg['development_seeds']],2400,1,24000)
   development[0]=[x['rows']['policy'] for x in baseline];save('checkpoint-0',development[0])
   report['parent_baseline']=summary(development[0],cfg);await publish()
   report['phase']='Guarded collection on actual parent-visited training states';await publish()
   teachers=await batch(collect,[(s,sampler_payload(samplers[0]),run_id) for s in cfg['training_seeds']],7200,35,24000)
   assert all(t['valid'] for t in teachers),'Complete both guarded sequences before model scaling'
   data=defaultdict(list)
   for teacher in teachers:
    for e in teacher['examples']:data[e['domain']].append((e['observation'],e['action']))
   for e in cfg.get('engineering_training_examples',[]):data[e['domain']].append((e['observation'],e['action']))
   domains=cfg['training']['domains'];assert all(data[d] for d in domains)
   report['data_audit']={d:{'examples':len(data[d]),'labels':dict(Counter(a for _,a in data[d]))} for d in domains}
   report['static_preference']=static_from_training(teachers)
   report['data_collection_provenance']={'type':'guarded actual parent visitation and measured branches','training_seeds':cfg['training_seeds'],
       'physical_attempts':sum(t['receipt']['physical_rollouts'] for t in teachers),'reused_regression_examples':len(cfg.get('engineering_training_examples',[]))}
   save('training-observations',data)
   evidence=await write('experimenter',{'kind':'training-observations','experiment_id':run_id,'data_audit':report['data_audit'],
        'complete_guarded_sequences':sum(t['valid'] for t in teachers),'data_sha256':digest(data)})
   await read('critic',evidence)
   counts={'walk':12,'recovery':12 if allocation=='contact_and_recovery' else 8,
       **{t:8 if t=='laptop' and allocation=='contact_and_recovery' else 4 for t in TASKS}}
   datums={d:decision_choice_datums(services.renderer,[(decision(o),a) for o,a in data[d]]) for d in domains}
   probes={}
   for d in domains:
    candidates=[e for t in teachers for e in t['examples'] if e['domain']==d]
    informative=min(candidates,key=lambda e:(max(e['student_distribution'],key=e['student_distribution'].get)==e['action'],max(e['student_distribution'].values())))
    probes[d]=informative['observation']
   initial=None
   report['phase']='Actual six-domain Tinker post-training';await publish()
   for update in range(cfg['training']['updates']+1):
    if update in cfg['training']['checkpoints']:
     if update:
      saved=await trainer.save_state(f'mochi_contact_v18_{os.environ["GITHUB_RUN_ID"]}_{update}')
      checkpoint_paths[str(update)]={'optimizer':saved.path,'rng_state':rng.bit_generator.state};save('checkpoint-paths',checkpoint_paths)
      samplers[update]=await trainer.save_weights_and_get_sampling_client(kind='snapshot')
     distributions={}
     for d,o in probes.items():
      rendering=services.renderer.render(decision(o));await change('inference_tokens',len(rendering.tokens)+1)
      distributions[d]=await sample_decision(samplers[update],rendering)
     if initial is None:initial=distributions
     if update==1:
      delta={d:max(abs(v-initial[d][a]) for a,v in dist.items()) for d,dist in distributions.items()}
      report['first_optimizer_probability_change']=delta
      assert max(delta.values())>1e-7,'No measurable change after the first optimizer update'
      report['recovery_probe_scope']='Recovery is post-trained in every update; saturated retention examples may leave its chosen action unchanged. Physical arm-travel changes can also come from the task-end posture.'
     cp={'update':update,'cumulative_updates':parent_info['cumulative_updates']+update,
         'checkpoint_id':digest(checkpoint_paths[str(update)]['optimizer']),'probe_distributions':distributions,'development':None}
     report['checkpoints'].append(cp);await publish()
    if update==cfg['training']['updates']:break
    indices={d:[int(i) for i in rng.choice(len(datums[d]),counts[d],replace=True)] for d in domains}
    tokens=sum(datums[d][i].model_input.length for d in domains for i in indices[d])
    await change('training_token_presentations',tokens);await change('optimizer_updates',1)
    backward=[(d,trainer.forward_backward([datums[d][i] for i in indices[d]],loss_fn='cross_entropy')) for d in domains]
    optimizer=trainer.optim_step(tinker.AdamParams(learning_rate=cfg['training']['learning_rate']))
    losses={d:(await future).metrics for d,future in backward};await optimizer
    report['optimizer_updates_completed']=update+1
    report['training_log'].append({'update':update+1,'domain_loss_metrics':losses,'tokens':tokens,
       'domain_counts':counts,'batch_sha256':digest(indices),'optimizer_completed':True,'forward_backward_completed':True,'at':now()})
    await publish()
   report['phase']='Matched development evaluations at every actual checkpoint';await publish()
   for cp in report['checkpoints']:
    u=cp['update']
    if u:
     rows=await batch(evaluate,[(s,[('policy',sampler_payload(samplers[u]),None)],run_id,'dev-'+str(u)) for s in cfg['development_seeds']],2400,1,24000)
     development[u]=[r['rows']['policy'] for r in rows];save('checkpoint-'+str(u),development[u])
    cp['development']=summary(development[u],cfg);await publish()
   selected=select_checkpoint(report['checkpoints'],development,cfg);report['selected_checkpoint']=selected
   save('selection-freeze',report);report['held_out_opened']=True
   report['phase']='Fresh final tests with paired reset playback and fixed/static controls';await publish()
   selected_payload=sampler_payload(samplers[selected['update']]);parent_payload=sampler_payload(samplers[0])
   pairs=await batch(evaluate,[(s,[('parent',parent_payload,None),('selected',selected_payload,None)],run_id,'held-out') for s in cfg['held_out_seeds']],2400,2,48000)
   controls=await batch(evaluate,[(s,[('fixed',None,None),('static',None,report['static_preference'])],run_id,'held-out-controls') for s in cfg['held_out_seeds']],2400,2,0)
   held={label:[bundle['rows'][label] for bundle in (pairs if label in ['parent','selected'] else controls)] for label in ['parent','selected','fixed','static']}
   report['held_out']={label:summary(rows,cfg) for label,rows in held.items()}
   for label,rows in held.items():save('held-out-'+label,rows)
   report['paired_held_out']=paired(held['parent'],held['selected'])
   report['paired_fixed_control']=paired(held['fixed'],held['selected'])
   pp=report['paired_held_out']
   report['all_fresh_tasks_qualified']=report['held_out']['selected']['qualified_complete_successes']==len(cfg['held_out_seeds'])
   report['all_fresh_clear_stepping']=report['held_out']['selected']['clear_stepping_successes']==len(cfg['held_out_seeds'])
   report['improvement_goal_met']=bool(report['all_fresh_tasks_qualified'] and pp['n']>=2 and
      pp['mean_step_reduction_fraction']>=.10 and pp['mean_recovery_arm_travel_reduction_fraction']>=.15 and pp['mean_time_reduction_fraction']>=0)
   report['phase']='Source-verified final review of numerical outcomes';await publish()
   result=await write('experimenter',{'kind':'final-observation','experiment_id':run_id,
      'selected_update':selected['update'],'optimizer_updates':report['optimizer_updates_completed'],
      'cohort':{k:{x:v[x] for x in ['n','complete_successes','qualified_complete_successes','falls','invalid_contacts','successful_mean_steps','successful_mean_seconds','successful_mean_recovery_arm_joint_travel_rad']} for k,v in report['held_out'].items()},
      'paired':report['paired_held_out'],'all_fresh_tasks_qualified':report['all_fresh_tasks_qualified'],
      'improvement_goal_met':report['improvement_goal_met']})
   recalled=await read('critic',result)
   verdict=await services.decide('critic','Does this evidence establish both complete fresh-scenario success and the declared efficiency improvement?',
       recalled,['qualified_success','reject_joint_improvement'],[result])
   review=await write('critic',{'kind':'conclusion','experiment_id':run_id,'model_verdict':verdict,
       'measured_goal_met':report['improvement_goal_met'],'all_fresh_tasks_qualified':report['all_fresh_tasks_qualified'],
       'qualification':'Deterministic measurements govern the conclusion. Fixed and static controls limit claims of adaptation; no hardware or native gait training.'})
   await read('researcher',review)
   canary=await write('critic',{'kind':'isolation-test','canary':'MOCHI_PRIVATE_CANARY'},True)
   await read('designer',canary,False)
   report['status']='completed';report['phase']='Completed bounded contact and recovery study';report['completed_at']=now()
   await publish();save('report',report)
 except BaseException as exc:
  report['status']='incomplete';report['error_type']=type(exc).__name__;report['error']=str(exc)
  await publish();save('incomplete',report);raise
 finally:await services.http.aclose()

if __name__=='__main__':asyncio.run(main())
