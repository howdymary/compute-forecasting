"""Small explicit controller calibration, not neural policy training."""
from concurrent.futures import ProcessPoolExecutor
import json
from mochi.desk.g1_tasks import rollout
from mochi.desk.tasks import Controller
from mochi.desk.g1_model import ROOT
CANDIDATES=[Controller(.20,.025,.0002),Controller(.25,.05,.0002),Controller(.30,.05,.00035)]
def run(item):
 candidate,seed=item;r=rollout('globe',seed,CANDIDATES[candidate],free_base=True,base_xy=(.065,.065));r['candidate']=candidate;return r
if __name__=='__main__':
 with ProcessPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,[(i,s)for i in range(3)for s in [9000,9001,9004,9005]]))
 out=ROOT/'web/desk/tasks/free-base-manual-calibration.json';out.write_text(json.dumps({'scope':'12 development trials of 3 hand-specified controller settings. Not Tinker training or held-out evidence.','results':results},indent=2))
 for r in results:print(r['candidate'],r['scenario']['seed'],r['success'],round(r['error_degrees'],2),round(r['balance']['max_tilt_degrees'],2),r['balance']['fall'],flush=True)
