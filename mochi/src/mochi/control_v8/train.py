"""Resume real Tinker weights; train six decision domains; evaluate frozen physics."""
import asyncio,hashlib,json,os,time
from collections import Counter,defaultdict
from pathlib import Path
import modal,numpy as np
from ..curriculum.world import ROOT,TASKS
from ..curriculum.train import wilson
from ..desk.services import DeskServices
from ..integrations import now,digest
from ..maintenance.checkpoints_by_date import inventory
from .remote import app,collect_teacher,evaluate,sampler_payload
from .decisions import decision
from .verification import sequence_success
OUT=ROOT/'artifacts/control-v8'
def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True);p=OUT/(name+'.json');tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)
def log(event,**fields):print('MOCHI_CONTROL_V8 '+json.dumps({'event':event,'at':now(),**fields}),flush=True)
def summary(rows):
 n=len(rows);success=sum(sequence_success(r) for r in rows);arrivals=[a for r in rows for a in r['arrivals']];recoveries=[x for r in rows for x in r['episode'].get('recoveries',[])];completed=[r for r in recoveries if r['success']]
 return {'n':n,'full_successes':success,'wilson_95_full_success_rate':wilson(success,n),'task_successes':{t:sum(r['episode']['results'].get(t,{}).get('success',False) for r in rows) for t in TASKS},'stations_reached':len(arrivals),'station_opportunities':n*4,'falls':sum(r['episode']['fall'] for r in rows),'mean_duration_s':float(np.mean([r['episode']['duration'] for r in rows])),'recovery_successes':len(completed),'recovery_attempts':len(recoveries),'recovery_contact_steps':sum(r['fixture_contact_steps'] for r in recoveries),'successful_recovery_mean_s':float(np.mean([r['duration_s'] for r in completed])) if completed else None,'successful_recovery_mean_joint_travel_rad':float(np.mean([r['arm_joint_travel_rad'] for r in completed])) if completed else None,'mean_arrival_position_error_mm':float(np.mean([r['position_error_mm'] for r in arrivals])) if arrivals else None}
def rank(s):return (s['full_successes'],-s['falls'],sum(s['task_successes'].values()),s['stations_reached'],s['recovery_successes'],-s['recovery_contact_steps'],-s['mean_duration_s'])
def balanced(data,n,rng,by_task=False):
 groups=defaultdict(list)
 for i,(o,a) in enumerate(data):groups[o['task'] if by_task else a].append(i)
 keys=sorted(groups);return [int(rng.choice(groups[keys[int(j)%len(keys)]])) for j in rng.permutation(n)]
async def publish(report,services):
 report['services']=services.report();save('progress',report);await modal.Dict.from_name('mochi-control-v8-progress',create_if_missing=True).put.aio('latest',json.loads(json.dumps(report)))
async def research(services,report,observation,update):
 rid=await services.write('experimenter',{'kind':'observation','study':'mochi-control-v8','update':update,**observation});seen=await services.read('researcher',rid)
 sources=await services.search('humanoid manipulation collision free arm retraction contact force laptop lid closing locomotion imitation learning waypoint error')
 hid=await services.write('researcher',{'kind':'hypothesis','evidence_record':rid,'sources':sources,'mechanism':'State-dependent safe withdrawal and balanced command imitation may reduce collisions and excess arm travel. The experiment must establish whether weights help.','supersedes':report.get('last_hypothesis')});report['last_hypothesis']=hid
 idea=await services.read('designer',hid);allocation=await services.decide('designer','Choose equal-size 80-example batches. balanced: 32 walk + 8 per task + 16 recovery; recovery_first: 24 walk + 8 per task + 24 recovery. All six domains always receive gradients. Recovery samples are balanced across tasks.',{'sources':idea,'observations':seen},['balanced','recovery_first'],[hid])
 pid=await services.write('designer',{'kind':'proposal','allocation':allocation,'hypothesis_record':hid,'update':update});proposal=await services.read('experimenter',pid);counts={'walk':32 if proposal['allocation']=='balanced' else 24,**{t:8 for t in TASKS},'recovery':16 if proposal['allocation']=='balanced' else 24};report.setdefault('research_allocation',[]).append({'update':update,'domain_batch_counts':counts,'proposal_record':pid});return counts
async def main():
 import tinker
 from tinker_cookbook.recipes.decisions import decision_choice_datums
 cfg=json.loads((ROOT/'configs/control-v8-protocol.json').read_text());route=json.loads((ROOT/'configs/desk-route-v8.json').read_text());services=DeskServices();start=time.perf_counter();report={'study':cfg['study'],'status':'running','phase':'Preflight','source_sha':os.getenv('GITHUB_SHA'),'workflow_run':os.getenv('GITHUB_RUN_ID'),'created_at':now(),'protocol':cfg,'scope':cfg['scope'],'training_log':[],'checkpoints':[],'rollouts':0,'optimizer_updates_completed':0,'parent_optimizer_updates':96,'evaluation_runtime':'Paired closed-loop Modal physics; fixed gait, standing balance, IK and success verifiers.'};paths={};snapshots={};rng=np.random.default_rng(cfg['training']['seed'])
 for p,expected in {**cfg['frozen_physics_sha256'],**cfg['frozen_controller_sha256']}.items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=expected:raise RuntimeError('Frozen physics mismatch '+p)
 try:
  records=await inventory(tinker.RestClient());parents=[c for c in records if digest(c.tinker_path)==cfg['parent_checkpoint_sha256']];assert len(parents)==1,'Canonical parent missing or ambiguous';assert len(records)+4<100,'Insufficient checkpoint headroom';parent=parents[0].tinker_path;report['parent_checkpoint_id']=digest(parent);report['checkpoint_count_before']=len(records)
  await services.setup()
  async with app.run():
   allocation=await research(services,report,{'engineering_changes':cfg['engineering_changes'],'new_physical_training_results':'Not yet measured; no improvement claimed.'},0)
   report['phase']='Modal branch experiments for training labels';await publish(report,services)
   teachers=[]
   if cfg.get('source_dataset_run'):
    source=next((ROOT/'.cache/control-reuse').rglob('teacher-summaries.json')).parent;prior=json.load(open(source/'progress.json'));assert prior['optimizer_updates_completed']==0;assert prior['protocol']['frozen_controller_sha256']==cfg['frozen_controller_sha256'];assert prior['protocol']['frozen_physics_sha256']==cfg['frozen_physics_sha256'];assert prior['protocol']['route_version']==cfg['route_version']
    teachers=[json.load(open(source/f'teacher-{seed}.json')) for seed in cfg['train_seeds']];report['rollouts']=sum(row['receipt']['physical_rollouts'] for row in teachers);report['source_data']={'workflow_run':cfg['source_dataset_run'],'optimizer_updates':0,'reused_completed_physical_rollouts':report['rollouts'],'dataset_sha256':{str(row['seed']):digest(row) for row in teachers},'interrupted_development_calls_at_most':2,'reason':'Before any gradient updates, replace fastest-only labels with lower-force contacts and least-travel safe recovery. Reuse identical frozen physical branches.'}
    for row in teachers:save('teacher-'+str(row['seed']),row)
   else:
    async for row in collect_teacher.starmap.aio([(seed,route) for seed in cfg['train_seeds']],order_outputs=True):
     teachers.append(row);report['rollouts']+=row['receipt']['physical_rollouts'];save('teacher-'+str(row['seed']),row);log('teacher',seed=row['seed'],valid=row['valid'],failure_task=row.get('failure_task'),rollouts=row['receipt']['physical_rollouts']);await publish(report,services)
   save('teacher-summaries',[{k:r[k] for k in ['seed','valid','receipt']} for r in teachers]);data=defaultdict(list);unique=defaultdict(dict);conflicts=[]
   for row in teachers:
    for e in row['examples']:
     d=e['domain'];o=e['model_observation'];key=json.dumps(o,sort_keys=True);old=unique[d].get(key);label=e['action']
     if d!='walk':
      trial=next(t for t in row['trials'] if t['domain']==d and t['task']==e['task']);candidates=[x for x in trial['outcomes'] if x['result']['success']];best=min(candidates,key=lambda x:(x['result']['arm_joint_travel_rad'],x['result']['duration_s']) if d=='recovery' else (x['result']['max_force_n'],x['result']['duration']));label=best['action']
     if old and old[1]!=label:conflicts.append({'domain':d,'observation':o,'labels':[old[1],label]})
     unique[d][key]=(o,label)
   if any(c['domain']=='walk' for c in conflicts):raise RuntimeError('Walking encoding aliases different teacher commands')
   data={d:list(v.values()) for d,v in unique.items()};domains=['walk',*TASKS,'recovery'];assert set(data)==set(domains),'Missing physical supervision domain'
   report['data_audit']={d:{'unique_observations':len(data[d]),'label_counts':dict(Counter(a for _,a in data[d])),'physical_observations':sum(e['domain']==d for r in teachers for e in r['examples'])} for d in domains};report['data_audit']['recovery']['task_counts']=dict(Counter(o['task'] for o,_ in data['recovery']));assert len(report['data_audit']['walk']['label_counts'])>=5;assert set(report['data_audit']['recovery']['task_counts'])==set(TASKS);save('training-observations',data);save('label-conflicts',conflicts)
   def fixed_action(domain,task):
    values=[a for o,a in data[domain] if domain!='recovery' or o['task']==task];return Counter(values).most_common(1)[0][0]
   fixed={t:fixed_action(t,t) for t in TASKS};recovery_fixed={t:fixed_action('recovery',t) for t in TASKS};report['fixed_baseline']=fixed;report['fixed_recovery_baseline']=recovery_fixed
   rid=await services.write('experimenter',{'kind':'observation','data_audit':report['data_audit'],'valid_teacher_sequences':sum(r['valid'] for r in teachers),'training_only':True});evidence=await services.read('critic',rid);verdict=await services.write('critic',{'kind':'qualified-conclusion','evidence':evidence,'conclusion':'Training labels are real physical measurements. No held-out improvement has been tested. Failed branches remain archived.'});await services.read('researcher',verdict);canary=await services.write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},private=True);await services.read('designer',canary,False)
   trainer=await services.service.create_training_client_from_state_with_optimizer(parent);renderer=services.renderer;datums={d:decision_choice_datums(renderer,[(decision(o),a) for o,a in data[d]]) for d in domains};paths['0']={'optimizer':parent};save('frozen',report);best=None
   for update in range(cfg['training']['updates']+1):
    if update in cfg['training']['checkpoints']:
     if update:
      state=await trainer.save_state(f'mochi_control_v8_{update}');paths[str(update)]={'optimizer':state.path,'rng_state':rng.bit_generator.state}
     sampler=await trainer.save_weights_and_get_sampling_client(kind='snapshot');snapshots[update]=sampler;payload=sampler_payload(sampler);save('checkpoint-paths',paths);report['phase']='Development checkpoint '+str(update);await publish(report,services)
     bundle=[r async for r in evaluate.starmap.aio([(seed,route,[('policy',payload)],fixed,recovery_fixed,True) for seed in cfg['development_seeds']],order_outputs=True)];report['rollouts']+=len(bundle);rows=[r['results']['policy'] for r in bundle];save('checkpoint-'+str(update),rows);save('checkpoint-receipts-'+str(update),[r['receipt'] for r in bundle]);s=summary(rows);cp={'update':update,'cumulative_parent_plus_updates':96+update,'checkpoint_id':digest(paths[str(update)]['optimizer'])[:20],'created_at':now(),'continuous_development':s};report['checkpoints'].append(cp)
     if best is None or rank(s)>best[0]:best=(rank(s),cp)
     await publish(report,services);log('checkpoint',**cp)
     if update==16:allocation=await research(services,report,{'development':s,'data_audit':report['data_audit'],'held_out_unused':True},update)
    if update==cfg['training']['updates']:break
    batches={d:balanced(data[d],allocation[d],rng,d=='recovery') for d in domains};pending=[(d,trainer.forward_backward([datums[d][i] for i in batches[d]],loss_fn='cross_entropy')) for d in domains];optimizer=trainer.optim_step(tinker.AdamParams(learning_rate=cfg['training']['learning_rate']));losses={}
    for d,future in pending:losses[d]=(await future).metrics
    await optimizer;report['optimizer_updates_completed']=update+1;report['phase']='Tinker six-domain post-training';report['training_log'].append({'update':update+1,'domain_counts':{d:len(batches[d]) for d in domains},'domain_loss_metrics':losses,'batch_sha256':digest(batches),'forward_backward_completed':True,'optimizer_completed':True,'at':now()})
    if (update+1)%4==0:await publish(report,services);log('optimizer_update',update=update+1)
   report['selected_checkpoint']=best[1];report['held_out_not_yet_run']=True;save('selection-freeze',report);selected=best[1]['update'];log('held_out_unsealed',selected=selected)
   payloads=[('starting_model',sampler_payload(snapshots[0])),('post_trained_model',sampler_payload(snapshots[selected])),('classical_fixed',None),('legacy_original_stack',sampler_payload(snapshots[0]))]
   bundles=[r async for r in evaluate.starmap.aio([(seed,route,payloads,fixed,recovery_fixed,True) for seed in cfg['held_out_seeds']],order_outputs=True)];report['rollouts']+=len(bundles)*len(payloads);results={label:[b['results'][label] for b in bundles] for label,_ in payloads}
   for label,rows in results.items():save('held-out-'+label,rows)
   report['held_out']={label:summary(rows) for label,rows in results.items() if label!='legacy_original_stack'};report['legacy_original_stack']={'n':len(results['legacy_original_stack']),'task_successes':{t:sum(r['episode']['results'].get(t,{}).get('success',False) for r in results['legacy_original_stack']) for t in TASKS},'falls':sum(r['episode']['fall'] for r in results['legacy_original_stack'])};report['modal_execution_receipts']=[r['receipt'] for r in bundles];report['paired_outcomes']=[{'seed':a['seed'],'starting_full':sequence_success(a),'trained_full':sequence_success(b),'starting_arrivals':len(a['arrivals']),'trained_arrivals':len(b['arrivals']),'trained_tasks':sum(x['success'] for x in b['episode']['results'].values()),'trained_fall':b['episode']['fall']} for a,b in zip(results['starting_model'],results['post_trained_model'])];report['held_out_not_yet_run']=False
   assert report['rollouts']<=cfg['maximum_modal_rollouts'];rid=await services.write('experimenter',{'kind':'observation','held_out':report['held_out'],'updates':report['optimizer_updates_completed'],'selected_update':selected});evidence=await services.read('critic',rid);verdict=await services.write('critic',{'kind':'conclusion','evidence':evidence,'qualification':'Small simulation pilot, one training run. Training changes decision weights, not gait-network weights or raw actuator control. Engineering changes are separate. No causal search or memory ablation.'});await services.read('researcher',verdict)
  report.update(status='completed',phase='Held-out evaluation complete',completed_at=now(),duration_seconds=time.perf_counter()-start);save('report',report);await publish(report,services);log('completed',held_out=report['held_out'])
 except Exception as exc:
  report.update(status='incomplete',error_type=type(exc).__name__,error=str(exc)[:240]);await publish(report,services);save('incomplete',report);raise
 finally:await services.http.aclose()
if __name__=='__main__':
 with modal.enable_output():asyncio.run(main())
