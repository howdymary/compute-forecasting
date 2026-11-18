"""Real fixed-follower tests and source-verified research handoffs. Zero updates."""
import asyncio,json,os,time
from pathlib import Path
import numpy as np
from .remote import app,sequence_pair,navigation_probe
from ..desk.services import DeskServices
ROOT=Path(__file__).resolve().parents[3]
async def main():
 out=ROOT/'artifacts/planning';out.mkdir(parents=True,exist_ok=True);route=json.loads((ROOT/'configs/desk-route-v1.json').read_text());cfg=json.loads((ROOT/'configs/planning-baseline.json').read_text());services=DeskServices();report={'study':'mochi-route-planning-v1','source_sha':os.getenv('GITHUB_SHA'),'optimizer_updates':0,'route_version':route['version'],'protocol':cfg,'started_at':time.time()}
 def save():
  (out/'baseline-report.json').write_text(json.dumps(report,indent=2,default=lambda x:x.item() if hasattr(x,'item') else str(x)))
 try:
  await services.setup();private=await services.write('critic',{'kind':'access-canary','synthetic':'MOCHI_PRIVATE_CANARY'},private=True);await services.read('researcher',private,allowed=False)
  source=await services.search('humanoid robot waypoint tracking final heading alignment stopping drift manipulation approach stance contact force stability')
  rid=await services.write('researcher',{'kind':'hypothesis','experiment_id':report['study'],'route_version':route['version'],'finding':'Old pelvis paths about 2m versus a 1.1m waypoint line. Nominal laptop stance failed all eight profiles on two calibration seeds. Alignment-mode latching and measured stop drift are engineering changes, not trained weights.','external_sources':source,'scope':'Search is evidence for inspection, not proof of improvement.'});research=await services.read('designer',rid)
  choice=await services.decide('designer','Pick one extra physical navigation probe. Both options are training-only; do not open held-out scenarios.',research,['repeat_stop_probe','turn_clearance_probe'],[rid]);pid=await services.write('designer',{'kind':'experiment-plan','route_version':route['version'],'probe':choice,'input_source_ids':[rid],'primary_calibration_seed':cfg['seeds'][0]});plan=await services.read('experimenter',pid)
  async with app.run():
   rows=[r async for r in sequence_pair.starmap.aio([(s,route,cfg['fixed_profiles']) for s in cfg['seeds']],order_outputs=True)]
   for r in rows:assert r['old']['episode']['trajectory']['frames'][0]==r['new']['episode']['trajectory']['frames'][0]
   report['pairs']=rows;report['modal_rollouts']=len(rows)*2;save()
   probe=await navigation_probe.remote.aio(plan['probe']);report['probe']=probe;report['modal_rollouts']+=1;save()
  summary={}
  for method in ['old','new']:
   group=[r[method] for r in rows];summary[method]={'arrivals':sum(len(r['arrivals']) for r in group),'arrival_opportunities':len(group)*(5 if method=='old' else 4),'falls':sum(r['episode']['fall'] for r in group),'tasks':{t:sum(r['episode']['results'].get(t,{}).get('success',False) for r in group) for t in ['alarm','drawer','laptop','globe']}}
  eid=await services.write('experimenter',{'kind':'observation','experiment_id':report['study'],'route_version':route['version'],'summary':summary,'probe':{'kind':plan['probe'],'arrivals':probe['arrivals'],'stop_trials':probe['stop_trials']},'optimizer_updates':0});evidence=await services.read('critic',eid)
  verdict=await services.decide('critic','Assess FULL FOUR-TASK physical feasibility, not arrival alone. All four tasks must pass on every calibration route for this gate. Storage is blocked regardless. Retain failures; do not attribute engineering changes to weights.',evidence,['feasibility_demonstrated_on_calibration','more_controller_work_needed'],[eid]);cid=await services.write('critic',{'kind':'conclusion','experiment_id':report['study'],'route_version':route['version'],'verdict':verdict,'summary':summary,'training_gate':'No optimization. Org is at 100 free checkpoints; preserve saved states. Model comparison B versus C has not run.'});await services.read('researcher',cid)
  report.update(status='completed',services=services.report(),summary=summary);save();print('BASELINE_SUMMARY',json.dumps(summary),flush=True)
 except Exception as e:report.update(status='failed',error_type=type(e).__name__,services=services.report());save();raise
 finally:await services.http.aclose()
if __name__=='__main__':asyncio.run(main())
