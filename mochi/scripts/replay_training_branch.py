"""Re-run a public physical training branch; no service credentials required."""
import argparse,json
from pathlib import Path
from mochi.control_v8.recovery import restore,recover,RECOVERIES
from mochi.control_v8.manipulation import PRESSES
from mochi.curriculum.world import PROFILES
p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=Path('mochi/evidence/control-v8/training-branches.json'));p.add_argument('--seed',type=int,required=True);p.add_argument('--task',choices=['alarm','drawer','laptop','globe'],required=True);p.add_argument('--domain',choices=['task','recovery'],default='task');p.add_argument('--action',required=True);a=p.parse_args();data=json.load(open(a.data));domain='recovery' if a.domain=='recovery' else a.task;t=next(t for t in data['trials'] if t['seed']==a.seed and t['task']==a.task and t['domain']==domain);expected=next(o for o in t['outcomes'] if o['action']==a.action)['result'];w=restore(t['snapshot'])
if a.domain=='recovery':actual=recover(w,a.task,next(p for p in RECOVERIES if p.code==a.action))
else:actual=w.do_task(a.task,next(p for p in (PRESSES if a.task=='laptop' else PROFILES) if p.code==a.action))
print(json.dumps({'scope':'Original V8 training branch, not the revised clearance setup or model inference. Cross-architecture floating-point differences can affect contacts.','expected':expected,'actual':actual,'same_success':actual['success']==expected['success']},indent=2))
