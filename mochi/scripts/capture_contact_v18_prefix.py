"""Reexecute a recorded V17 action prefix and retain the actual arrival state."""
import argparse,gzip,hashlib,json,pickle,time
from pathlib import Path
from mochi.balanced.sequence import PhysicalStop
from mochi.smooth_v17.sequence import run
from mochi.smooth_v16.world import state
from mochi.smooth_v16.remote import physical_hash

p=argparse.ArgumentParser();p.add_argument('--seed',type=int,required=True);a=p.parse_args()
out=Path('mochi/artifacts/contact-v18-engineering')
out.mkdir(parents=True,exist_ok=True)
path=out/f'prefix-{a.seed}.json'
assert not path.exists()
path.write_text(json.dumps({'status':'started','physical_attempts':1,'seed':a.seed}))
prior=json.loads(Path('mochi/.cache/v17-finalized/held-out-selected.json').read_text())
row=next(r for r in prior if r['seed']==a.seed)
actions=[x['action'] for x in row['model_decisions']]
observed=[];saved=None;start=time.perf_counter()
def choose(w,domain,task,default,available):
 global saved
 if domain=='laptop':
  saved={'state':state(w,include_history=False),'source':'Actual physics state after reexecuting the recorded V17 decision prefix. New execution; not asserted bit-identical to original.',
         'seed':a.seed,'physical_hash':physical_hash(w),'prefix':observed}
  raw=gzip.compress(pickle.dumps(saved,protocol=5),mtime=0)
  dest=out/f'prefix-{a.seed}-laptop.pickle.gz';dest.write_bytes(raw)
  raise PhysicalStop('diagnostic_laptop_state_captured')
 action=actions[len(observed)]
 assert action in available
 observed.append({'domain':domain,'task':task,'action':action,'t':float(w.d.time)})
 print(json.dumps(observed[-1]),flush=True)
 return action
r=run(a.seed,False,choose=choose)
result={'status':'completed','physical_attempts':1,'seed':a.seed,'captured':saved is not None,'source_actions':actions,
        'observed':observed,'failure':r['failure'],'wall_seconds':time.perf_counter()-start,
        'final_object_states':r['episode']['final_object_states'],'contact_failures':r['episode']['contact_failures'],
        'scope':'Diagnostic prefix from reset; not a completed demo or new learned behavior.'}
path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
