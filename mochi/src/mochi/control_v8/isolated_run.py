"""Evaluate retained before/selected weights without additional optimizer calls."""
import asyncio,json,os,time,hashlib
from pathlib import Path
import modal
from .remote import app,sampler_payload
from .isolated import evaluate_isolated
from ..curriculum.world import ROOT,TASKS
from ..integrations import digest,now
OUT=ROOT/'artifacts/control-v8-isolated'
async def main():
 import tinker
 paths=list((ROOT/'.cache/control-source').rglob('checkpoint-paths.json'));assert len(paths)==1;source=paths[0].parent;r=json.load(open(source/'report.json'));assert r['status']=='completed';private=json.load(open(paths[0]));selected=r['selected_checkpoint']['update'];
 for p,expected in (r['protocol']['frozen_physics_sha256']|r['protocol']['frozen_controller_sha256']).items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==expected,p
 service=tinker.ServiceClient(display_name='mochi-v8-isolated-evaluation');models=[]
 for label,update in [('starting_model',0),('post_trained_model',selected)]:
  trainer=await service.create_training_client_from_state(private[str(update)]['optimizer']);sampler=await trainer.save_weights_and_get_sampling_client(kind='snapshot');models.append((label,sampler_payload(sampler)))
 route=json.load(open(ROOT/'configs/desk-route-v8.json'))
 async with app.run():rows=[x async for x in evaluate_isolated.starmap.aio([(seed,route,models) for seed in r['protocol']['held_out_seeds']],order_outputs=True)]
 flat=[x|{'seed':row['seed']} for row in rows for x in row['results']];report={'study':'mochi-control-v8-isolated','source_training_run':r['workflow_run'],'source_training_sha':r['source_sha'],'evaluation_source_sha':os.getenv('GITHUB_SHA'),'workflow_run':os.getenv('GITHUB_RUN_ID'),'at':now(),'selected_update':selected,'new_optimizer_updates':0,'scope':'Separate initialized task probes and paired post-task recovery states; not the continuous demo. Same frozen V8 primitives. These use the original four test seeds after immutable checkpoint selection; they are not four additional independent full-route tests. Reference task failures exclude recovery pairs and are reported.','rollouts':sum(x['receipt']['physical_rollouts'] for x in rows),'prior_training_rollouts':r['rollouts'],'receipts':[x['receipt'] for x in rows],'results':flat,'task_summary':{},'recovery_summary':{},'paired_recovery':[]}
 for label in ['starting_model','post_trained_model']:
  report['task_summary'][label]={t:{'n':len(a:=[x for x in flat if x['domain']=='task' and x['task']==t and x['model']==label]),'successes':sum(x['result']['success'] for x in a)} for t in TASKS};a=[x for x in flat if x['domain']=='recovery' and x['model']==label];report['recovery_summary'][label]={'n':len(a),'successes':sum(x['result']['success'] for x in a),'fixture_contact_steps':sum(x['result']['fixture_contact_steps'] for x in a)}
 for seed in r['protocol']['held_out_seeds']:
  for task in TASKS:
   a=[x for x in flat if x['domain']=='recovery' and x['seed']==seed and x['task']==task]
   if len(a)!=2:continue
   b,c=sorted(a,key=lambda x:x['model']=='post_trained_model');assert b['initial_state_sha256']==c['initial_state_sha256'];report['paired_recovery'].append({'seed':seed,'task':task,'starting_success':b['result']['success'],'trained_success':c['result']['success'],'starting_action':b['action'],'trained_action':c['action'],'starting_joint_travel_rad':b['result']['arm_joint_travel_rad'],'trained_joint_travel_rad':c['result']['arm_joint_travel_rad'],'starting_duration_s':b['result']['duration_s'],'trained_duration_s':c['result']['duration_s'],'starting_hand_path_m':b['result']['hand_path_m'],'trained_hand_path_m':c['result']['hand_path_m'],'both_valid':b['result']['success'] and c['result']['success']})
 paired=[x for x in report['paired_recovery'] if x['both_valid']];report['matched_motion']={'n':len(paired),'starting_joint_travel_rad':sum(x['starting_joint_travel_rad'] for x in paired),'trained_joint_travel_rad':sum(x['trained_joint_travel_rad'] for x in paired),'starting_hand_path_m':sum(x['starting_hand_path_m'] for x in paired),'trained_hand_path_m':sum(x['trained_hand_path_m'] for x in paired)}
 assert report['rollouts']+r['rollouts']<=r['protocol']['maximum_modal_rollouts'];OUT.mkdir(parents=True,exist_ok=True);(OUT/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:report[k] for k in ['rollouts','task_summary','recovery_summary']}),flush=True)
if __name__=='__main__':
 with modal.enable_output():asyncio.run(main())
