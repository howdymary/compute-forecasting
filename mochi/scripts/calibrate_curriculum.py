"""Reproduce one manual engineering calibration, without any trained selector."""
import argparse,hashlib,json
from pathlib import Path
from mochi.curriculum.remote import Runner
from mochi.curriculum.world import World,ROOT
from mochi.curriculum.train import sequence_summary
p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=12001);a=p.parse_args();r=Runner();status=r.reset(a.seed,True);profiles={'alarm':'B','drawer':'B','laptop':'C','globe':'B'}
for i in range(500):
 if status['mode']=='done':break
 obs=status['observation'];action=World.teacher_move(obs) if status['mode']=='walk' else profiles[obs['domain']];status=r.advance(action)
summary=sequence_summary([{'episode':r.w.episode(),'arrivals':r.arrivals}]);episode=r.w.episode();episode['kind']='manual engineering calibration';episode['trained_optimizer_updates']=0;episode['profiles']=profiles;episode['summary']=summary
out=ROOT/'artifacts/curriculum';out.mkdir(exist_ok=True,parents=True);(out/'calibration-sequence.json').write_text(json.dumps(episode,separators=(',',':')));print(json.dumps(summary),flush=True)
