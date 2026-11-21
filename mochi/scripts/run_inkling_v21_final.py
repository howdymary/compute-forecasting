from concurrent.futures import ThreadPoolExecutor,as_completed
import datetime,hashlib,json,os,subprocess
from pathlib import Path
r=Path('mochi');out=r/'artifacts/inkling-v21';f=json.loads((out/'selection-freeze.json').read_text())
for n,h in f['frozen_sha256'].items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h,n
assert not (out/'final-execution-started.json').exists()
(out/'final-execution-started.json').write_text(json.dumps({'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'held_out_opened':True,'selection_sha256':hashlib.sha256((out/'selection-freeze.json').read_bytes()).hexdigest()},indent=2)+'\n')
env=os.environ.copy();env.update(PYTHONPATH='mochi/src',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
jobs=[]
for seed in f['held_out_seeds']:
 for label in ['parent','clearance']:
  jobs.append((f'fresh-{label}-{seed}',seed,'P5',label=='clearance'))
for seed in f['extra_p6_control_seeds']:jobs.append((f'fresh-p6-control-{seed}',seed,'P6',False))
def one(job):
 name,seed,profile,candidate=job
 cmd=['mochi/.venv/bin/python','-u','-m','mochi.inkling_v21.experiment','--id',name,'--mode','full','--seed',str(seed),'--laptop-action',profile]
 if candidate:cmd+=['--candidate','mochi/configs/inkling-v21-selected.json']
 with (out/(name+'.log')).open('w') as log:p=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 meta=json.loads((out/'physics'/(name+'.metadata.json')).read_text())
 result={k:meta.get(k) for k in ['id','status','complete','qualified','steps','seconds','failure','error','wall_seconds']}
 print(json.dumps(result),flush=True);return result
with ThreadPoolExecutor(max_workers=4) as pool:
 results=[future.result() for future in as_completed([pool.submit(one,j) for j in jobs])]
(out/'final-execution.json').write_text(json.dumps(results,indent=2)+'\n')
print('FINAL_INKLING_EVALUATION_COMPLETE',flush=True)
