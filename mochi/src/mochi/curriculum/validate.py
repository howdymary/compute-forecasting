"""No gradients: preserve the 64-update result and test closed-loop Modal control."""
import asyncio,hashlib,json,os,time
from pathlib import Path
import numpy as np
from .world import ROOT,TASKS
from .train import complete,sequence_summary,task_summary
from .checkpoints import StateSampler
from .remote_policy import app,evaluate_bundle,sampler_payload
from .remote import replay
from .resume import merged_services
from ..desk.services import DeskServices
from ..integrations import now,digest
OUT=ROOT/'artifacts/policy-validation'
def save(name,x):
 OUT.mkdir(exist_ok=True,parents=True);(OUT/(name+'.json')).write_text(json.dumps(x,indent=2))
async def main():
 import tinker
 cfg=json.loads((ROOT/'configs/policy-validation.json').read_text());source=next((ROOT/'.cache/policy-source').rglob('held-out-post_trained_model.json')).parent;original=json.loads((source/'incomplete.json').read_text());paths=json.loads((source/'checkpoint-paths.json').read_text());report={'status':'running','created_at':now(),'source_sha':os.getenv('GITHUB_SHA'),'source_run':cfg['source_run'],'extra_optimizer_updates':0,'selected_update_frozen':64,'showcase_selection':'Scenario 14001 was selected after observing its held-out success. This is an illustrative success, not a reliability estimate.','phase':'Restore fixed policies'};services=DeskServices();parent=tinker.ServiceClient(display_name='mochi-v6-closed-loop-validation');inference=StateSampler(parent);samplers={};payloads={};start=time.perf_counter()
 async def publish():
  save('progress',report);await __import__('modal').Dict.from_name('mochi-curriculum-v6-validation-progress',create_if_missing=True).put.aio('latest',report)
 try:
  for u in [0,8,16,32,64]:samplers[u]=await inference.load(paths[str(u)]['optimizer']);payloads[u]=sampler_payload(samplers[u])
  report['checkpoint_ids']={str(u):digest(paths[str(u)]['optimizer'])[:20] for u in payloads};report['phase']='Remote inference credential and snapshot probe';await publish()
  async with app.run():
   probe=await evaluate_bundle.remote.aio(12000,[('starting_model',payloads[0])],original['fixed_baseline'],probe=True);save('probe',probe)
   if len(probe['results']['starting_model']['model_decisions'])!=1:raise RuntimeError('Remote Tinker inference not established')
   report['remote_inference_probe_passed']=True;report['phase']='Closed-loop paired Modal routes';await publish();models=[('starting_model',payloads[0]),('post_trained_model',payloads[64]),('classical_fixed',None)];seeds=original['protocol']['held_out_seeds'];paired=[r async for r in evaluate_bundle.starmap.aio([(seed,models,original['fixed_baseline'],None,True,False) for seed in seeds],order_outputs=True)];save('modal-paired-routes',paired)
   report['modal_held_out']={name:sequence_summary([r['results'][name] for r in paired]) for name,_ in models};report['modal_rollouts_completed']=12;report['phase']='Checkpoint demonstration on the disclosed showcase';await publish();showcase=await evaluate_bundle.remote.aio(14001,[(str(u),payloads[u]) for u in [0,8,16,32,64]],original['fixed_baseline'],record=True);save('modal-showcase-checkpoints',showcase);report['modal_showcase']={u:sequence_summary([r]) for u,r in showcase['results'].items()};report['modal_rollouts_completed']+=5
   nav_cfg=json.loads((ROOT/'configs/walking-audit-protocol.json').read_text());report['phase']='Paired isolated walking on Modal';await publish();navigation=[r async for r in evaluate_bundle.starmap.aio([(seed,models,original['fixed_baseline'],offset,False,False) for seed,offset in zip(nav_cfg['seeds'],nav_cfg['goal_offsets'])],order_outputs=True)];save('modal-paired-navigation',navigation)
   from .walk_audit import summary as walk_summary
   report['modal_isolated_walking']={name:walk_summary([r['results'][name] for r in navigation]) for name,_ in models};report['modal_rollouts_completed']+=24
  # Original cohort remains independent of the replication and showcase.
  reference={name:json.loads((source/('held-out-'+name+'.json')).read_text()) for name in ['starting_model','post_trained_model']};report['reference_held_out']={k:sequence_summary(v) for k,v in reference.items()};report['reference_isolated_contact']=original['held_out_isolated_contact'];report['reference_paired_outcomes']=[{'seed':a['seed'],'starting_full':complete(a),'trained_full':complete(b),'starting_arrivals':len(a['arrivals']),'trained_arrivals':len(b['arrivals'])} for a,b in zip(reference['starting_model'],reference['post_trained_model'])];report['action_replay_cross_runtime']='Original open-loop replay diverged in mode. Replication instead makes fresh model decisions from the changing physical state, with each before/after/classical triplet on one Modal worker. No trajectories or states are resynchronized.'
  await services.setup();canary=await services.write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},private=True);await services.read('designer',canary,False);rid=await services.write('experimenter',{'kind':'observation','reference':report['reference_held_out'],'modal_replication':report['modal_held_out'],'walking':report['modal_isolated_walking'],'extra_optimizer_updates':0});evidence=await services.read('critic',rid);view=await services.decide('critic','Qualify the measured results, preserving every failure. A successful showcased episode is not representative reliability; the two runtime cohorts are not independent market samples.',evidence,['qualified_improvement','improvement_not_established'],[rid]);cid=await services.write('critic',{'kind':'conclusion','assessment':view,'evidence':evidence,'limits':report['action_replay_cross_runtime']});verdict=await services.read('researcher',cid);focus=await services.decide('researcher','Choose the next research question from this verdict; it will not change the frozen 64-update policy.',verdict,['robust_arrival','contact_margin'],[cid]);search=await services.search('humanoid waypoint arrival robust imitation learning compounding errors' if focus=='robust_arrival' else 'humanoid contact force margin robust manipulation');await services.write('researcher',{'kind':'hypothesis','question':focus,'sources':search,'scope':'Future investigation only; no further optimizer updates in this validation.'})
  report.update(status='completed',phase='Completed',completed_at=now(),duration_seconds=time.perf_counter()-start,services=merged_services(original['services'],services.report()));save('report',report);await publish()
 except Exception as exc:
  report.update(status='incomplete',error_type=type(exc).__name__,error=str(exc)[:240]);save('incomplete',report);await publish();raise
 finally:await services.http.aclose()
if __name__=='__main__':
 import modal
 with modal.enable_output():asyncio.run(main())
