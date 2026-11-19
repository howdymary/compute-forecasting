import fcntl,json,time
from contextlib import contextmanager
from ..curriculum.world import ROOT

OUT=ROOT/'artifacts/balance-v11'

@contextmanager
def ledger():
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'ledger.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=OUT/'ledger.json';data=json.loads(path.read_text()) if path.exists() else {'study':'mochi-balanced-v11','local_rollouts':0,'attempts':{}}
        yield data
        path.write_text(json.dumps(data,indent=2)+'\n')

def reserve(ident,parameters):
    cfg=json.loads((ROOT/'configs/balance-v11.json').read_text())
    with ledger() as data:
        if ident in data['attempts']:raise ValueError('Experiment ID already exists; preserve the original attempt')
        if data['local_rollouts']>=cfg['bounds']['local_rollouts']:raise RuntimeError('Local rollout ceiling reached')
        data['local_rollouts']+=1;data['attempts'][ident]={'status':'reserved','parameters':parameters,'at_unix':time.time()}

def finish(ident,result):
    with ledger() as data:data['attempts'][ident].update(result)
