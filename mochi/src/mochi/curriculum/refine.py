"""A separately frozen, geometry-encoded 96-update post-training study."""
import asyncio,hashlib,json,os,time
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np,modal
from .world import ROOT,TASKS,PROFILES,World
from .remote import app,walking_coverage,contact_trial,Runner,image
from .remote_policy import app as policy_app,evaluate_bundle,sampler_payload
from .decisions import decision
from .features import encode,CachedSelector
from ..desk.services import DeskServices
from ..integrations import now,digest
OUT=ROOT/'artifacts/refinement-v7'
def save(name,value):
 OUT.mkdir(exist_ok=True,parents=True);(OUT/(name+'.json')).write_text(json.dumps(value,indent=2))
def log(event,**fields):print('MOCHI_REFINEMENT '+json.dumps({'event':event,'at':now(),**fields}),flush=True)
async def publish(report,services):
 report['services']=services.report();save('progress',report);await modal.Dict.from_name('mochi-curriculum-v7-progress',create_if_missing=True).put.aio('latest',json.loads(json.dumps(report)))
def contact_rank(row):
 r=row['result'];return (not r['success'],r['max_force_n'],r['duration'])
def balanced_indices(data,count,rng):
 classes=defaultdict(list)
 for i,(_,label) in enumerate(data):classes[label].append(i)
 labels=sorted(classes);return [int(rng.choice(classes[labels[i%len(labels)]])) for i in rng.permutation(count)]
async def navigation(sampler,renderer,selector,seed,offset,expert=False):
 r=Runner();status=r.reset(seed,False);goal=(float(r.w.d.qpos[0])+offset[0],float(r.w.d.qpos[1])+offset[1],offset[2]);r.goal=goal;status=r.status();actions=[]
 for _ in range(100):
  if status['mode']!='walk':break
  obs=status['observation'];action=World.teacher_move(obs) if expert else (await selector(sampler,renderer,obs))[0];actions.append(action);status=r.advance(action)
 return {'seed':seed,'goal':goal,'actions':actions,'success':bool(status['mode']=='task' and not r.w.fall),'end_observation':r.w.walk_observation(goal),'episode':r.w.episode()}
@app.function(image=image,cpu=1,memory=2048,max_containers=8,timeout=600)
def replay_navigation(seed,goal,actions):
 start=time.perf_counter();r=Runner();r.reset(seed,False);r.goal=goal;s=r.status()
 for action in actions:
  if s['mode']!='walk':break
  s=r.advance(action)
 return {'seed':seed,'success':bool(s['mode']=='task' and not r.w.fall),'duration_s':float(r.w.d.time),'provider':'Modal','cpu':1,'memory_mib':2048,'duration_seconds':time.perf_counter()-start}
async def research(services,report,observation,update):
 rid=await services.write('experimenter',{'kind':'observation','update':update,**observation});observed=await services.read('researcher',rid)
 focus=await services.decide('researcher','Choose which observed failure needs targeted literature before the next bounded experiments.',observed,['waypoint_stopping','contact_margin'],[rid])
 query={'waypoint_stopping':'robot imitation learning waypoint stopping state discretization class imbalance compounding errors','contact_margin':'humanoid manipulation force margin contact control uncertainty'}[focus];sources=await services.search(query)
 idea=await services.write('researcher',{'kind':'hypothesis','observed':observed,'sources':sources,'mechanism':'Reduce ambiguous numeric encoding and correct rare walking actions; prefer lower-force successful contacts. Source evidence motivates this study but does not establish benefit.'});evidence=await services.read('designer',idea)
 allocation=await services.decide('designer','Choose locomotion_first (48 walking + 4 per task) or balanced_updates (32 walking + 8 per task). Both are 64-example batches and train all five domains.',evidence,['locomotion_first','balanced_updates'],[idea]);pid=await services.write('designer',{'kind':'proposal','allocation':allocation,'source_record':idea,'update':update});proposal=await services.read('experimenter',pid)
 counts={'walk':48,**{t:4 for t in TASKS}} if proposal['allocation']=='locomotion_first' else {'walk':32,**{t:8 for t in TASKS}}
 report.setdefault('research_allocation',[]).append({'update':update,'focus':allocation,'domain_batch_counts':counts,'proposal_record':pid});return counts,proposal,pid
async def main():
 from .train import complete,sequence_summary,task_summary
 import tinker
 from tinker_cookbook.recipes.decisions import decision_choice_datums
 protocol=json.loads((ROOT/'configs/refinement-protocol.json').read_text());cfg=protocol['training'];services=DeskServices();started=time.perf_counter();report={'study':protocol['study'],'status':'running','phase':'Freeze and research','source_sha':os.getenv('GITHUB_SHA'),'created_at':now(),'protocol':protocol,'protocol_sha256':digest(protocol),'scope':protocol['scope'],'training_log':[],'checkpoints':[],'rollouts':0,'optimizer_updates_completed':0,'prior_study_updates':64,'checkpoint_retention':protocol['checkpoint_retention']};snapshots={};selectors={};private_paths={}
 for path,expected in protocol['frozen_physics_sha256'].items():
  if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:raise RuntimeError('Frozen physics mismatch: '+path)
 source=next((ROOT/'.cache/refine-source').rglob('contact-outcomes.json')).parent;rows=json.loads((source/'contact-outcomes.json').read_text());prior=json.loads((source/'incomplete.json').read_text());old_paths=json.loads((source/'checkpoint-paths.json').read_text());train_seeds=protocol['train_seeds'];dev_seeds=protocol['development_seeds'];test_seeds=protocol['held_out_seeds'];dev_route_seeds=protocol['checkpoint_development_seeds'];base_path=old_paths['0']['optimizer'];report['source_data']={'workflow_run':protocol['source_dataset_run'],'contact_sha256':hashlib.sha256((source/'contact-outcomes.json').read_bytes()).hexdigest(),'prior_completed_modal_rollouts':prior['rollouts'],'prior_study_source_sha':prior['source_sha'],'new_physics_trials_are_counted_separately':True}
 try:
  await services.setup()
  async with app.run(),policy_app.run():
   allocation,proposal,pid=await research(services,report,{'prior_development':prior['checkpoints'][-1]['continuous_development'],'prior_replication':protocol['prior_replication'],'limits':'V6 reached 3/10 waypoints and zero full routes. New development and test seeds are untouched. Same frozen world, gait, action catalogue and success rules.'},0)
   coverage_focus=await services.decide('experimenter','Select equal-budget training navigation coverage. near_waypoints emphasizes final alignment; turn_recovery includes goals behind the robot. Only training seeds may be used.',proposal,['near_waypoints','turn_recovery'],[pid]);rng=np.random.default_rng(cfg['seed']);jobs=[]
   for i in range(protocol['additional_training_navigation_rollouts']):
    dx=float(rng.uniform(.025,.11)) if coverage_focus=='near_waypoints' else float(rng.uniform(-.05,.11));dy=float(rng.uniform(-.055,.055));yaw=float(rng.choice([-1.57,-.35,0,.35,1.57]));
    if dx>.06 and dy>.025:dy=.02
    jobs.append((train_seeds[i%len(train_seeds)],[dx,dy,yaw]))
   report['phase']='Training-only navigation coverage';await publish(report,services);coverage=[r async for r in walking_coverage.starmap.aio(jobs,order_outputs=True)];report['rollouts']+=len(coverage);save('extra-navigation',coverage)
   teachers=json.loads((source/'walking-teachers.json').read_text())+json.loads((source/'walking-coverage.json').read_text())+coverage;walking={};conflicts=[];physical_states=0
   for trial in teachers:
    for d in trial['episode']['decisions']:
     if d['observation']['domain']!='walk':continue
     physical_states+=1;obs=encode(d['observation']);key=json.dumps(obs,sort_keys=True);label=d['action']
     if key in walking and walking[key][1]!=label:conflicts.append(key)
     walking[key]=(obs,label)
   if conflicts:raise RuntimeError('State encoding aliases different teacher actions')
   data={'walk':list(walking.values())};audit={'walk':{'physical_observations':physical_states,'unique_encoded_observations':len(walking),'label_counts':dict(Counter(label for _,label in data['walk'])),'ambiguous_encodings':0}};groups=defaultdict(list)
   for r in rows:groups[(r['seed'],r['result']['task'])].append(r)
   for task in TASKS:
    data[task]=[];excluded=[]
    for seed in train_seeds:
     candidates=[r for r in groups[(seed,task)] if r['result']['success']]
     if not candidates:excluded.append(seed);continue
     best=min(candidates,key=contact_rank);data[task].append((best['observation'],best['result']['profile']['code']))
    audit[task]={'n':len(data[task]),'excluded_no_successful_profile':excluded,'label_counts':dict(Counter(label for _,label in data[task]))}
   report['data_audit']=audit;save('data-audit',audit);save('training-observations',data)
   def fixed_key(task,code):
    r=[x['result'] for x in rows if x['seed'] in train_seeds and x['result']['task']==task and x['result']['profile']['code']==code];return (-sum(x['success'] for x in r),float(np.mean([x['max_force_n'] for x in r])),float(np.mean([x['duration'] for x in r])))
   fixed={t:min(PROFILES,key=lambda p:fixed_key(t,p.code)).code for t in TASKS};report['fixed_baseline']=fixed
   dev_jobs=[(seed,t,p.code,False) for seed in dev_seeds for t in TASKS for p in PROFILES];report['phase']='Development contact measurements';await publish(report,services);dev_contact=[r async for r in contact_trial.starmap.aio(dev_jobs,order_outputs=True)];report['rollouts']+=len(dev_contact);save('development-contact-outcomes',dev_contact)
   canary=await services.write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},private=True);await services.read('designer',canary,False)
   trainer=await services.service.create_training_client_from_state_with_optimizer(base_path);renderer=services.renderer;datums={d:decision_choice_datums(renderer,[(decision(o),label) for o,label in examples]) for d,examples in data.items()};private_paths['0']={'optimizer':base_path};report['phase']='Tinker post-training';save('frozen',report);selected=None
   for update in range(cfg['updates']+1):
    if update in cfg['checkpoints']:
     sampler=await trainer.save_weights_and_get_sampling_client(kind='snapshot');session=getattr(sampler,'_sampling_session_id',None)
     if not isinstance(session,str):raise RuntimeError('Pinned SDK snapshot receipt missing')
     snapshots[update]=sampler;selector=CachedSelector();selectors[update]=selector;private_paths[str(update)]={'sampling_session_id':session,'kind':'fixed_ephemeral_snapshot',**private_paths.get(str(update),{})};cp={'update':update,'checkpoint_id':digest(session)[:20],'checkpoint_id_kind':'fixed_ephemeral_snapshot','created_at':now()}
     save('checkpoint-paths',private_paths);report['phase']='Development evaluation at update '+str(update);await publish(report,services)
     payload=sampler_payload(sampler);remote_dev=[r async for r in evaluate_bundle.starmap.aio([(seed,[('policy',payload)],fixed,None,True,False,True) for seed in dev_route_seeds],order_outputs=True)];report['rollouts']+=len(remote_dev);dev=[r['results']['policy'] for r in remote_dev];save('checkpoint-'+str(update),dev);save('checkpoint-receipts-'+str(update),remote_dev);picked=[]
     for seed in dev_seeds:
      for task in TASKS:
       cell=[r for r in dev_contact if r['seed']==seed and r['result']['task']==task];action,_=await selector(sampler,renderer,cell[0]['observation']);picked.append(next(r for r in cell if r['result']['profile']['code']==action))
     cp.update(continuous_development=sequence_summary(dev),isolated_contact_development=task_summary(picked),inference={'actual_tinker_calls':selector.calls+sum(r['results']['policy']['inference']['actual_tinker_inference_calls'] for r in remote_dev),'identical_observation_cache_hits':selector.hits+sum(r['results']['policy']['inference']['identical_observation_cache_hits'] for r in remote_dev)});report['checkpoints'].append(cp);save('inference-'+str(update),selector.receipt());await publish(report,services);log('checkpoint',**cp)
     if update>=64 and (cp['continuous_development']['full_successes']==len(dev_route_seeds) or update==cfg['updates']):
      selected=update;state=await trainer.save_state('mochi_geometry_walk_tasks_'+str(update));private_paths[str(update)]['optimizer']=state.path;cp['optimizer_state_id']=digest(state.path)[:20];save('checkpoint-paths',private_paths);report['selected_checkpoint']=cp;report['stopping_rule_trigger']='both development routes passed' if cp['continuous_development']['full_successes']==len(dev_route_seeds) else '96-update budget';save('selection-freeze',report);break
     if update==16:allocation,_,_=await research(services,report,{'development':cp['continuous_development'],'isolated_contact':cp['isolated_contact_development'],'scope':'Development evidence only; held-out still sealed.'},update)
    if update==cfg['updates']:break
    pending=[];batch={}
    for domain,examples in data.items():
     indices=balanced_indices(examples,allocation[domain],rng) if domain=='walk' else rng.integers(0,len(examples),allocation[domain]).tolist();batch[domain]=indices;pending.append((domain,trainer.forward_backward([datums[domain][int(i)] for i in indices],loss_fn='cross_entropy')))
    optimizer=trainer.optim_step(tinker.AdamParams(learning_rate=cfg['learning_rate']));losses={}
    for domain,future in pending:losses[domain]=(await future).metrics
    await optimizer;report['training_log'].append({'update':update+1,'domain_counts':{d:len(v) for d,v in batch.items()},'domain_loss_metrics':losses,'batch_sha256':digest(batch),'forward_backward_completed':True,'optimizer_completed':True,'at':now()});report['optimizer_updates_completed']=len(report['training_log']);report['phase']='Tinker post-training'
    if (update+1)%4==0:await publish(report,services);log('optimizer_update',update=update+1)
   assert selected in [64,96] and report['optimizer_updates_completed']==selected and all(set(x['domain_counts'])=={'walk',*TASKS} for x in report['training_log'])
   report['held_out_not_yet_run']=True;save('selection-freeze',report);report['phase']='Fresh paired Modal routes';await publish(report,services)
   models=[('starting_model',sampler_payload(snapshots[0])),('post_trained_model',sampler_payload(snapshots[selected])),('classical_fixed',None)];paired=[r async for r in evaluate_bundle.starmap.aio([(seed,models,fixed,None,True,False,True) for seed in test_seeds],order_outputs=True)];report['rollouts']+=len(paired)*len(models);save('paired-held-out-routes',paired);result={name:[r['results'][name] for r in paired] for name,_ in models}
   for name,group in result.items():save('held-out-'+('classical' if name=='classical_fixed' else name),group)
   report['held_out']={k:sequence_summary(v) for k,v in result.items()};report['evaluation_runtime']='All checkpoint and held-out physics executes on Modal. Each held-out before/after/classical triplet shares one worker.'
   report['phase']='Fresh isolated contact tasks';await publish(report,services);test_jobs=[(seed,t,p.code,False) for seed in test_seeds for t in TASKS for p in PROFILES];isolated=[r async for r in contact_trial.starmap.aio(test_jobs,order_outputs=True)];report['rollouts']+=len(isolated);save('held-out-isolated-outcomes',isolated);picked_groups={}
   for name,update in [('starting_model',0),('post_trained_model',selected)]:
    picked=[]
    for seed in test_seeds:
     for task in TASKS:
      cell=[r for r in isolated if r['seed']==seed and r['result']['task']==task];action,_=await selectors[update](snapshots[update],renderer,cell[0]['observation']);picked.append(next(r for r in cell if r['result']['profile']['code']==action))
    picked_groups[name]=picked
   picked_groups['fixed_profiles']=[r for r in isolated if r['result']['profile']['code']==fixed[r['result']['task']]];report['held_out_isolated_contact']={k:task_summary(v) for k,v in picked_groups.items()};save('held-out-isolated-evaluation',picked_groups)
   # Walking is tested independently, with all three policies on each worker.
   from .walk_audit import summary as walk_summary
   offsets=json.loads((ROOT/'configs/walking-audit-protocol.json').read_text())['goal_offsets'];report['phase']='Fresh paired isolated walking';await publish(report,services);nav_paired=[r async for r in evaluate_bundle.starmap.aio([(16500+i,models,fixed,offset,False,False,True) for i,offset in enumerate(offsets)],order_outputs=True)];report['rollouts']+=len(nav_paired)*len(models);save('paired-held-out-navigation',nav_paired);nav={name:[r['results'][name] for r in nav_paired] for name,_ in models};report['held_out_isolated_walking']={k:walk_summary(v) for k,v in nav.items()};save('held-out-navigation',nav)
   report['modal_execution_receipts']=[r['receipt'] for r in paired+nav_paired];report['paired_outcomes']=[{'seed':a['seed'],'starting_full':complete(a),'trained_full':complete(b),'starting_tasks':sum(x['success'] for x in a['episode']['results'].values()),'trained_tasks':sum(x['success'] for x in b['episode']['results'].values()),'starting_arrivals':len(a['arrivals']),'trained_arrivals':len(b['arrivals'])} for a,b in zip(result['starting_model'],result['post_trained_model'])];delta=np.array([int(r['trained_full'])-int(r['starting_full']) for r in report['paired_outcomes']]);boot=delta[np.random.default_rng(8312).integers(0,len(delta),(10000,len(delta)))].mean(1);report['paired_full_success_gain']={'n':len(delta),'percentage_points':float(delta.mean()*100),'bootstrap_95_percentage_points':(np.quantile(boot,[.025,.975])*100).tolist()};report['held_out_not_yet_run']=False
   rid=await services.write('experimenter',{'kind':'observation','held_out':report['held_out'],'isolated_walking':report['held_out_isolated_walking'],'isolated_contact':report['held_out_isolated_contact'],'optimizer_updates_completed':selected});evidence=await services.read('critic',rid);view=await services.decide('critic','Does the evidence support a qualified gain, or is an improvement not established? Simulation pilot only; report task, walking and full-route results separately.',evidence,['qualified_improvement','improvement_not_established'],[rid]);cid=await services.write('critic',{'kind':'conclusion','model_assessment':view,'evidence':evidence,'numerically_verified_full_route_gain':report['paired_full_success_gain'],'limits':'One training run, four held-out routes, fixed Unitree gait and classical balance/IK. Discrete command/profile post-training, not raw torque learning. Search and memory have no causal ablation.'});await services.read('researcher',cid)
   for update,selector in selectors.items():save('inference-'+str(update),selector.receipt())
  report.update(status='completed',completed_at=now(),duration_seconds=time.perf_counter()-started,phase='Completed',services=services.report());save('report',report);await publish(report,services);log('completed',held_out=report['held_out'],walking=report['held_out_isolated_walking'])
 except Exception as exc:
  report.update(status='incomplete',error_type=type(exc).__name__,error=str(exc)[:240],services=services.report());save('incomplete',report);await publish(report,services);raise
 finally:await services.http.aclose()
if __name__=='__main__':
 with modal.enable_output():asyncio.run(main())
