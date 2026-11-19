import fcntl,json,time
from contextlib import contextmanager
from ..curriculum.world import ROOT

OUT=ROOT/'artifacts/terrain-v12'

@contextmanager
def ledger():
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'ledger.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        p=OUT/'ledger.json';data=json.loads(p.read_text()) if p.exists() else {'study':'mochi-terrain-v12','local_rollouts':0,'attempts':{}}
        yield data
        p.write_text(json.dumps(data,indent=2)+'\n')

def reserve(ident,parameters):
    cap=json.loads((ROOT/'configs/terrain-v12.json').read_text())['bounds']['local_rollouts']
    with ledger() as data:
        if ident in data['attempts']:raise ValueError('Immutable attempt ID already exists')
        if data['local_rollouts']>=cap:raise RuntimeError('V12 local rollout cap reached')
        data['local_rollouts']+=1;data['attempts'][ident]={'status':'reserved','parameters':parameters,'at_unix':time.time()}

def finish(ident,result):
    with ledger() as data:data['attempts'][ident].update(result)
