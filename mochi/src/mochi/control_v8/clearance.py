"""Unchanged trained weights on a separately frozen, safer laptop stance."""
import asyncio,copy,json,os,shutil,time,uuid,hashlib
from collections import defaultdict
from pathlib import Path
import modal
from .remote import app,evaluate,sampler_payload
from .isolated import evaluate_isolated
from .train import summary,rank
from .verification import sequence_success
from ..curriculum.world import ROOT
from ..desk.services import DeskServices
from ..integrations import now,digest
OUT=ROOT/'artifacts/control-clearance'
def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/(name+'.json')).write_text(json.dumps(value,indent=2))
async def publish(r,services):
 r['services']=services.report();save('progress',r);await modal.Dict.from_name('mochi-control-clearance-progress',create_if_missing=True).put.aio('latest',json.loads(json.dumps(r)))
def continue_memory(prior):
 s=DeskServices();s.run_id='mochi-clr-'+uuid.uuid4().hex[:8];s.actors=prior['actors'];s.audience=prior['audiences']['shared'];s.private=prior['audiences']['critic_private'];s.records={x['id']:x for x in prior['records']};s.reads=prior['reads'].copy();s.decisions=prior['decisions'].copy();s.calls=prior['calls'].copy();s.sources=prior['sources'].copy();return s
async def main():
 cfg=json.load(open(ROOT/'configs/clearance-protocol.json'));source=next((ROOT/'.cache/clearance-source').rglob('report.json')).parent;base=json.load(open(source/'report.json'));assert base['status']=='completed' and base['optimizer_updates_completed']==64;private=json.load(open(source/'checkpoint-paths.json'));route=json.load(open(ROOT/'configs/desk-route-clearance.json'));assert route['version']==cfg['route_version'];services=continue_memory(base['services']);started=time.perf_counter();r=copy.deepcopy(base)
 r.update(study=cfg['study'],training_study=base['study'],training_workflow_run=base['workflow_run'],workflow_run=os.getenv('GITHUB_RUN_ID'),source_sha=os.getenv('GITHUB_SHA'),training_source_sha=base['source_sha'],status='running',phase='Clearance revision preflight',new_optimizer_updates=0,training_reused=True,created_at=now(),checkpoints=[],selected_checkpoint=None,held_out=None,paired_outcomes=[],source_training_rollouts=base['rollouts'],new_modal_rollouts=0,rollouts=base['rollouts'],original_v8_evaluation={'checkpoints':base['checkpoints'],'held_out':base['held_out'],'paired_outcomes':base['paired_outcomes']},engineering_revision=cfg,scope=cfg['scope'],training_workflow_url=f"https://github.com/howdymary/mochi-demo/actions/runs/{base['workflow_run']}")
 r['protocol']=copy.deepcopy(base['protocol']);r['protocol'].update(study=cfg['study'],development_seeds=cfg['development_seeds'],held_out_seeds=cfg['held_out_seeds'],route_version=route['version'],route_config='desk-route-clearance.json',selection=cfg['selection']);r['protocol']['training_source_route_version']=base['protocol']['route_version'];r.pop('completed_at',None);r.pop('duration_seconds',None)
 for name in ['training-observations.json','checkpoint-paths.json',*[f'teacher-{s}.json' for s in base['protocol']['train_seeds']]]:
  OUT.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,OUT/name)
 for p,expected in {**base['protocol']['frozen_physics_sha256'],**base['protocol']['frozen_controller_sha256']}.items():
  assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==expected,p
 try:
  await services.setup()
  async with app.run():
   observation=await services.write('experimenter',{'kind':'observation','study':cfg['study'],'source':'known training seed23000; no new test evidence','finding':'The falling lid contacted the left hip at the original stance. A20mm outward initial stance removed that contact in a physical diagnostic.','engineering_checks':cfg['engineering_evidence'],'new_optimizer_updates':0});seen=await services.read('researcher',observation)
   focus=await services.decide('researcher','Choose which evidence to investigate before interpreting this fixed stance revision.',seen,['articulated_object_swept_volume','contact_force_margin'],[observation]);sources=await services.search('robot manipulation articulated object swept volume collision clearance humanoid' if focus=='articulated_object_swept_volume' else 'robot contact manipulation force margin collision clearance articulated objects');idea=await services.write('researcher',{'kind':'hypothesis','sources':sources,'observation_record':observation,'mechanism':'The full articulated-object sweep matters in addition to the initial pose. A safer stance may preserve learned command performance; only matched tests can establish this.'});await services.read('designer',idea);proposal=await services.write('designer',{'kind':'proposal','hypothesis_record':idea,'protocol':cfg,'bounded_action':'Retest all five immutable V8 checkpoints, choose only on development, then unseal four fresh test seeds. No weight updates or verifier changes.'});await services.read('experimenter',proposal)
   models={};r['phase']='Restore immutable trained checkpoints';await publish(r,services)
   for update in [0,8,16,32,64]:
    trainer=await services.service.create_training_client_from_state(private[str(update)]['optimizer']);sampler=await trainer.save_weights_and_get_sampling_client(kind='snapshot');models[update]=sampler_payload(sampler)
   jobs=[(seed,route,[(f'checkpoint_{update}',models[update])],base['fixed_baseline'],base['fixed_recovery_baseline'],True) for update in models for seed in cfg['development_seeds']];groups=defaultdict(list);best=None;r['phase']='Matched development on revised stance';await publish(r,services)
   async for bundle in evaluate.starmap.aio(jobs,order_outputs=True):
    label=next(iter(bundle['results']));update=int(label.split('_')[-1]);groups[update].append(bundle['results'][label]);r['new_modal_rollouts']+=1;r['rollouts']+=1
    if len(groups[update])==len(cfg['development_seeds']):
     save('checkpoint-'+str(update),groups[update]);s=summary(groups[update]);cp={'update':update,'cumulative_parent_plus_updates':96+update,'checkpoint_id':digest(private[str(update)]['optimizer'])[:20],'created_at':now(),'continuous_development':s};r['checkpoints'].append(cp)
     if best is None or rank(s)>best[0]:best=(rank(s),cp)
     await publish(r,services);print('MOCHI_CLEARANCE_CHECKPOINT',json.dumps(cp),flush=True)
   selected=best[1]['update'];r['selected_checkpoint']=best[1];r['held_out_not_yet_run']=True;save('selection-freeze',r);rid=await services.write('experimenter',{'kind':'observation','development':r['checkpoints'],'selected_update':selected,'new_test_unused':True});seen=await services.read('critic',rid);verdict=await services.write('critic',{'kind':'qualified-conclusion','evidence':seen,'selection':'Frozen deterministic development ranking; tests must remain unused. The stance change is engineered, not attributed to training.'});await services.read('researcher',verdict)
   payloads=[('starting_model',models[0]),('post_trained_model',models[selected]),('classical_fixed',None)];r['phase']='Fresh paired held-out scenarios';await publish(r,services)
   bundles=[x async for x in evaluate.starmap.aio([(seed,route,payloads,base['fixed_baseline'],base['fixed_recovery_baseline'],True) for seed in cfg['held_out_seeds']],order_outputs=True)];r['new_modal_rollouts']+=len(bundles)*3;r['rollouts']+=len(bundles)*3;results={label:[b['results'][label] for b in bundles] for label,_ in payloads}
   for label,rows in results.items():save('held-out-'+label,rows)
   r['held_out']={label:summary(rows) for label,rows in results.items()};r['modal_execution_receipts']=[x['receipt'] for x in bundles];r['paired_outcomes']=[{'seed':b['seed'],'starting_full':sequence_success(b),'trained_full':sequence_success(c),'starting_arrivals':len(b['arrivals']),'trained_arrivals':len(c['arrivals']),'trained_tasks':sum(x['success'] for x in c['episode']['results'].values()),'trained_fall':c['episode']['fall']} for b,c in zip(results['starting_model'],results['post_trained_model'])];r['held_out_not_yet_run']=False;r['phase']='Isolated task and paired recovery probes';await publish(r,services)
   isolated=[x async for x in evaluate_isolated.starmap.aio([(seed,route,[(label,payload) for label,payload in payloads if payload]) for seed in cfg['held_out_seeds']],order_outputs=True)];save('isolated-bundles',isolated);r['new_modal_rollouts']+=sum(x['receipt']['physical_rollouts'] for x in isolated);r['rollouts']+=sum(x['receipt']['physical_rollouts'] for x in isolated);flat=[x|{'seed':row['seed']} for row in isolated for x in row['results']];iso={'study':cfg['study']+'-isolated','new_optimizer_updates':0,'scope':'Separate initialized task probes and shared post-task recovery states; not the continuous demo.','rollouts':sum(x['receipt']['physical_rollouts'] for x in isolated),'task_summary':{},'recovery_summary':{},'paired_recovery':[],'results':flat,'receipts':[x['receipt'] for x in isolated]}
   for label in ['starting_model','post_trained_model']:
    iso['task_summary'][label]={t:{'n':len(a:=[x for x in flat if x['domain']=='task' and x['task']==t and x['model']==label]),'successes':sum(x['result']['success'] for x in a)} for t in ['alarm','drawer','laptop','globe']};a=[x for x in flat if x['domain']=='recovery' and x['model']==label];iso['recovery_summary'][label]={'n':len(a),'successes':sum(x['result']['success'] for x in a),'fixture_contact_steps':sum(x['result']['fixture_contact_steps'] for x in a)}
   for seed in cfg['held_out_seeds']:
    for task in ['alarm','drawer','laptop','globe']:
     a=[x for x in flat if x['domain']=='recovery' and x['seed']==seed and x['task']==task]
     if len(a)!=2:continue
     b,c=sorted(a,key=lambda x:x['model']=='post_trained_model');assert b['initial_state_sha256']==c['initial_state_sha256'];iso['paired_recovery'].append({'seed':seed,'task':task,'starting_success':b['result']['success'],'trained_success':c['result']['success'],'starting_action':b['action'],'trained_action':c['action'],'starting_joint_travel_rad':b['result']['arm_joint_travel_rad'],'trained_joint_travel_rad':c['result']['arm_joint_travel_rad'],'starting_duration_s':b['result']['duration_s'],'trained_duration_s':c['result']['duration_s'],'both_valid':b['result']['success'] and c['result']['success']})
   save('isolated-report',iso);r['isolated_control_summary']={k:iso[k] for k in ['rollouts','task_summary','recovery_summary','paired_recovery']};assert r['rollouts']<=base['protocol']['maximum_modal_rollouts'];rid=await services.write('experimenter',{'kind':'observation','study':cfg['study'],'held_out':r['held_out'],'isolated_recovery':iso['recovery_summary'],'new_optimizer_updates':0,'source_training_updates':64});evidence=await services.read('critic',rid);claim=await services.decide('critic','Choose how to qualify these simulation results. Use the measured outcomes; fixed gait and IK, one training run, four fresh cases, no hardware evidence.',evidence,['bounded_simulation_improvement','insufficient_new_case_improvement'],[rid]);verdict=await services.write('critic',{'kind':'conclusion','evidence':evidence,'model_verdict':claim,'limits':'Engineering stance revision and learned weight effects are distinct. Every before/after uses the same new stance. Training is reused unchanged; no optimizer updates here. Small fixed-layout simulation pilot.'});await services.read('researcher',verdict)
  r.update(status='completed',phase='Clearance transfer and control probes complete',completed_at=now(),duration_seconds=time.perf_counter()-started);await publish(r,services);save('report',r)
 except Exception as exc:
  r.update(status='incomplete',error_type=type(exc).__name__,error=str(exc)[:200]);await publish(r,services);raise
 finally:await services.http.aclose()
if __name__=='__main__':
 with modal.enable_output():asyncio.run(main())
