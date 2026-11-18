"""Local development checks, not training or a held-out performance claim."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import json
from mochi.desk.g1_tasks import rollout
from mochi.desk.g1_model import ROOT,model_xml,SOURCE

def run(pair):return rollout(*pair,record=pair[1]==9000)
if __name__=='__main__':
 pairs=[(task,seed) for task in ['laptop','globe'] for seed in range(9000,9008)]
 with ProcessPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,pairs))
 public=ROOT/'web/desk/tasks'
 for r in results:
  if r['scenario']['seed']==9000:
   (public/(r['task']+'.json')).write_text(json.dumps(r,separators=(',',':')))
   (public/(r['task']+'.xml')).write_text(model_xml(r['scenario']).replace(str(SOURCE/'assets'),'../../../assets/robot/g1/assets'))
  r.pop('trajectory',None)
 report={'scope':'16 local development rollouts with a hand-configured feedback controller. No training, held-out evaluation, or policy-improvement claim.','results':results}
 (public/'calibration.json').write_text(json.dumps(report,indent=2))
 for task in ['laptop','globe']:
  rs=[r for r in results if r['task']==task];print(task,sum(r['success'] for r in rs),'/',len(rs),'errors',[round(r['error_degrees'],2) for r in rs],flush=True)
