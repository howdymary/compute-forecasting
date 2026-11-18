"""Foot-supported development checks and the rejected laptop-load test."""
from concurrent.futures import ProcessPoolExecutor
import json
from mochi.desk.g1_model import ROOT,SOURCE,model_xml
from mochi.desk.g1_tasks import rollout
from mochi.desk.tasks import Controller

def run(pair):return rollout(*pair,controller=Controller(.25,.025,.0003),record=pair[1]==9000,free_base=True)
if __name__=='__main__':
 pairs=[('globe',seed) for seed in range(9000,9008)]+[('laptop',9000)]
 with ProcessPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,pairs))
 public=ROOT/'web/desk/tasks'
 for r in results:
  if r['scenario']['seed']==9000:
   (public/('free-'+r['task']+'.json')).write_text(json.dumps(r,separators=(',',':')))
   (public/('free-'+r['task']+'.xml')).write_text(model_xml(r['scenario'],free_base=True).replace(str(SOURCE/'assets'),'../../../assets/robot/g1/assets'))
  r.pop('trajectory',None)
 report={'scope':'8 globe development rollouts and 1 rejected laptop stress test. Free base with foot contacts, rigid leg/waist/finger poses. No trained balance or controller selection.','results':results}
 (public/'free-base-calibration.json').write_text(json.dumps(report,indent=2))
 for r in results:print(r['task'],r['scenario']['seed'],'success',r['success'],'error',round(r['error_degrees'],2),'tilt',round(r['balance']['max_tilt_degrees'],2),'fall',r['balance']['fall'],flush=True)
