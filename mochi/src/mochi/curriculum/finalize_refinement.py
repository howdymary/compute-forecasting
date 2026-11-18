"""Evaluation-only recovery from saved V7 states; zero new gradient updates."""
import asyncio,json,os,time,shutil
import numpy as np
import modal
from .world import ROOT,TASKS,PROFILES
from .train import complete,sequence_summary,task_summary
from .remote import app as physics_app,contact_trial
from .remote_policy import app as policy_app,evaluate_bundle,sampler_payload
from .features import CachedSelector
from .resume import merged_services
from ..desk.services import DeskServices
from ..integrations import now,digest
OUT=ROOT/'artifacts/refinement-v7'
def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/(name+'.json')).write_text(json.dumps(value,indent=2))
async def main():
 import tinker
 from tinker_cookbook import model_info,renderers
 from tinker_cookbook.recipes.decisions import DecisionRenderer
 cfg=json.loads((ROOT/'configs/refinement-evaluation.json').read_text());source=next((ROOT/'.cache/refinement-source').rglob('incomplete.json')).parent
 shutil.copytree(source,OUT,dirs_exist_ok=True);report=json.loads((source/'incomplete.json').read_text());paths=json.loads((source/'checkpoint-paths.json').read_text());prior_services=report['services'];protocol=report['protocol'];selected=report['selected_checkpoint']['update'];assert selected==96 and report['optimizer_updates_completed']==96
 report.update(status='running',phase='Restore saved states for inference',recovery={'prior_evaluation_attempts':cfg.get('prior_evaluation_attempts',[]),'training_run':cfg['source_run'],'evaluation_run':os.getenv('GITHUB_RUN_ID'),'evaluation_source_sha':os.getenv('GITHUB_SHA'),'extra_optimizer_updates':0,'reason':'Final full training checkpoint was saved; free storage limit then closed the original service client. Use fresh inference clients on the immutable saved states.','original_error_type':report.pop('error_type',None),'original_error':report.pop('error',None)})
 services=DeskServices();clients=[];snapshots={};selectors={};start=time.perf_counter()
 async def publish():
  report['services']=merged_services(prior_services,services.report());save('progress',report);await modal.Dict.from_name('mochi-curriculum-v7-progress',create_if_missing=True).put.aio('latest',report)
 try:
  # Restore each full state into a fresh client, then make an in-memory
  # inference snapshot. The live API rejects full-state paths for direct
  # sampling despite an upstream example. No persistent checkpoint is written.
  for u in [0,selected]:
   service=tinker.ServiceClient(display_name='mochi-v7-readonly-'+str(u));clients.append(service);restored=await service.create_training_client_from_state(paths[str(u)]['optimizer']);snapshots[u]=await restored.save_weights_and_get_sampling_client(kind='snapshot');selectors[u]=CachedSelector()
  renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'),snapshots[0].get_tokenizer()));models=[('starting_model',sampler_payload(snapshots[0])),('post_trained_model',sampler_payload(snapshots[selected])),('classical_fixed',None)];fixed=report['fixed_baseline'];test_seeds=protocol['held_out_seeds']
  async with physics_app.run(),policy_app.run():
   report['phase']='Read-only saved-state inference probe';await publish();probe=await evaluate_bundle.remote.aio(12000,models[:2],fixed,record=False,probe=True,encoded=True);save('recovery-probe',probe)
   assert all(len(r['model_decisions'])==1 for r in probe['results'].values());report['rollouts']+=2;report['recovery']['saved_state_inference_probe_passed']=True;report['phase']='Fresh paired Modal routes';await publish()
   paired=[r async for r in evaluate_bundle.starmap.aio([(seed,models,fixed,None,True,False,True) for seed in test_seeds],order_outputs=True)];report['rollouts']+=len(paired)*len(models);save('paired-held-out-routes',paired);result={name:[r['results'][name] for r in paired] for name,_ in models}
   for name,group in result.items():save('held-out-'+('classical' if name=='classical_fixed' else name),group)
   report['held_out']={k:sequence_summary(v) for k,v in result.items()};report['evaluation_runtime']='All checkpoint and held-out physics executes on Modal. Each held-out before/after/classical triplet shares one worker.';report['phase']='Fresh isolated contact tasks';await publish()
   jobs=[(seed,t,p.code,False) for seed in test_seeds for t in TASKS for p in PROFILES];isolated=[r async for r in contact_trial.starmap.aio(jobs,order_outputs=True)];report['rollouts']+=len(isolated);save('held-out-isolated-outcomes',isolated);picked_groups={}
   for name,u in [('starting_model',0),('post_trained_model',selected)]:
    picked=[]
    for seed in test_seeds:
     for task in TASKS:
      cell=[r for r in isolated if r['seed']==seed and r['result']['task']==task];action,_=await selectors[u](snapshots[u],renderer,cell[0]['observation']);picked.append(next(r for r in cell if r['result']['profile']['code']==action))
    picked_groups[name]=picked
   picked_groups['fixed_profiles']=[r for r in isolated if r['result']['profile']['code']==fixed[r['result']['task']]];report['held_out_isolated_contact']={k:task_summary(v) for k,v in picked_groups.items()};save('held-out-isolated-evaluation',picked_groups)
   from .walk_audit import summary as walk_summary
   offsets=json.loads((ROOT/'configs/walking-audit-protocol.json').read_text())['goal_offsets'];report['phase']='Fresh paired isolated walking';await publish();navigation=[r async for r in evaluate_bundle.starmap.aio([(16500+i,models,fixed,offset,False,False,True) for i,offset in enumerate(offsets)],order_outputs=True)];report['rollouts']+=len(navigation)*len(models);save('paired-held-out-navigation',navigation);nav={name:[r['results'][name] for r in navigation] for name,_ in models};report['held_out_isolated_walking']={k:walk_summary(v) for k,v in nav.items()};save('held-out-navigation',nav)
   report['modal_execution_receipts']=[r['receipt'] for r in paired+navigation];report['paired_outcomes']=[{'seed':a['seed'],'starting_full':complete(a),'trained_full':complete(b),'starting_tasks':sum(x['success'] for x in a['episode']['results'].values()),'trained_tasks':sum(x['success'] for x in b['episode']['results'].values()),'starting_arrivals':len(a['arrivals']),'trained_arrivals':len(b['arrivals']),'trained_fall':b['episode']['fall']} for a,b in zip(result['starting_model'],result['post_trained_model'])];delta=np.array([int(r['trained_full'])-int(r['starting_full']) for r in report['paired_outcomes']]);boot=delta[np.random.default_rng(8312).integers(0,len(delta),(10000,len(delta)))].mean(1);report['paired_full_success_gain']={'n':len(delta),'percentage_points':float(delta.mean()*100),'bootstrap_95_percentage_points':(np.quantile(boot,[.025,.975])*100).tolist()};report['held_out_not_yet_run']=False
  report['phase']='Verified memory criticism';await publish();await services.setup();canary=await services.write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},private=True);await services.read('designer',canary,False)
  calibration=json.loads((ROOT/'evidence/gait-calibration/results.json').read_text());rid=await services.write('experimenter',{'kind':'observation','held_out':report['held_out'],'walking':report['held_out_isolated_walking'],'contact':report['held_out_isolated_contact'],'optimizer_updates_completed':selected,'rejected_gait_calibration':{'recording_sha256':calibration['recording_sha256'],'decision':calibration['decision']}});evidence=await services.read('critic',rid);view=await services.decide('critic','Qualify walking, contact and full-route changes separately. Retain the worse update-96 development outcome relative to update 64. Cadence trials were engineering-only and are not promoted.',evidence,['qualified_improvement','improvement_not_established'],[rid]);cid=await services.write('critic',{'kind':'conclusion','assessment':view,'evidence':evidence,'limits':'One small simulation study; native gait, balance and IK fixed. No causal memory or search ablation. Gait modulation was not trained or promoted.'});verdict=await services.read('researcher',cid);focus=await services.decide('researcher','Choose the next unresolved problem. This cannot change the frozen policy or test results.',verdict,['laptop_contact_stability','locomotion_robustness'],[cid]);search=await services.search('humanoid laptop closing manipulation contact force balance stability' if focus=='laptop_contact_stability' else 'humanoid locomotion waypoint stopping imitation learning compounding errors');hid=await services.write('researcher',{'kind':'hypothesis','focus':focus,'sources':search,'scope':'Future investigation only; zero additional optimizer updates in evaluation recovery.'});await services.read('designer',hid)
  report.update(status='completed',phase='Completed',completed_at=now(),evaluation_duration_seconds=time.perf_counter()-start);save('report',report);await publish();save('report',report)
 except Exception as exc:
  report.update(status='incomplete',error_type=type(exc).__name__,error=str(exc)[:240]);save('evaluation-incomplete',report);await publish();raise
 finally:await services.http.aclose()
if __name__=='__main__':
 with modal.enable_output():asyncio.run(main())
