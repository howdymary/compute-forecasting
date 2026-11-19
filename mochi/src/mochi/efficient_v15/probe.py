"""Bounded local engineering branches, never stitched into a demonstration."""
import argparse
import fcntl
import hashlib
import json
import pickle
import shutil
import time
from pathlib import Path

from ..curriculum.world import ROOT
from ..balanced.sequence import PhysicalStop
from ..terrain_v12.development import restore as old_restore
from .world import EfficientWorld
from .steps import StepCounter
from .sequence import leg, run

OUT=ROOT/'artifacts/efficient-v15-engineering'


def reserve(args):
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'ledger.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=OUT/'ledger.json'
        ledger=json.loads(path.read_text()) if path.exists() else {}
        assert args.id not in ledger and len(ledger)<24
        assert sum(r.get('wall_seconds',540 if r['status']=='reserved' else 0) for r in ledger.values())<5400
        ledger[args.id]={'status':'reserved','arguments':vars(args)}
        path.write_text(json.dumps(ledger,indent=2)+'\n')


def finish(ident,result):
    with (OUT/'ledger.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=OUT/'ledger.json'
        ledger=json.loads(path.read_text())
        ledger[ident].update(result)
        path.write_text(json.dumps(ledger,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--id',required=True)
    p.add_argument('--profile',choices=['W0','W3','W4'],default='W0')
    p.add_argument('--task',choices=['laptop','globe','full','globe-contact'],default='laptop')
    p.add_argument('--contact-profile',choices=['A','G0','G1'],default='A')
    p.add_argument('--state')
    p.add_argument('--save-supported',action='store_true')
    p.add_argument('--seed',type=int,default=41001)
    a=p.parse_args()
    reserve(a)
    from .policy import WALKS,NAVIGATION
    source=OUT/'source'/a.id
    source.mkdir(parents=True,exist_ok=False)
    hashes={}
    for path in Path(__file__).parent.glob('*.py'):
        hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copy2(path,source/path.name)
    provenance={'walk':WALKS[a.profile],'navigation':vars(NAVIGATION[a.profile]),'source_sha256':hashes}
    started=time.perf_counter()
    if a.task=='full':
        def choose(w,domain,task,default,choices):
            if domain=='globe':
                return a.contact_profile
            return a.profile if domain=='walk' and task!='alarm' else default
        row=run(a.seed,choose=choose)
    elif a.task=='globe-contact':
        from .world import restore
        from .policy import execute
        assert a.state
        w=restore(pickle.loads((OUT/a.state).read_bytes()),record=True)
        start=float(w.d.time)
        failure=None
        try:
            result=execute(w,'globe','globe',a.contact_profile)
        except PhysicalStop as exc:
            result={}
            failure=str(exc)
        row={'study':'mochi-efficient-v15-engineering','scope':'Exact saved-state globe-contact diagnostic, not a continuous demo.',
             'failure':failure,'success':result.get('success',False),'result':result,
             'duration_s':float(w.d.time)-start,'episode':w.episode()}
    else:
        source=ROOT/'artifacts/directional-v14/states'/('full-directional-1-'+('drawer' if a.task=='laptop' else 'laptop')+'.pickle')
        w=old_restore(pickle.loads(source.read_bytes()),record=True)
        w.__class__=EfficientWorld
        w.step_counter=StepCounter()
        w.efficiency_segment='initialization'
        w.frames=[]
        w.capture()
        w.measurements=[]
        w.next_measurement=float(w.d.time)
        w.direction_samples=[]
        w.next_direction_sample=float(w.d.time)
        start=float(w.d.time)
        result=None
        failure=None
        try:
            result=leg(w,a.task,a.profile)
        except PhysicalStop as exc:
            failure=str(exc)
        row={'study':'mochi-efficient-v15-engineering','scope':'Saved-state navigation diagnostic; not a continuous sequence or trained gain.',
             'failure':failure,'success':failure is None,'arrivals':result,'profile':a.profile,
             'duration_s':float(w.d.time)-start,'episode':w.episode()}
        if a.save_supported and failure is None:
            from .world import state
            path=OUT/(a.id+'-supported.pickle')
            assert not path.exists()
            path.write_bytes(pickle.dumps(state(w)))
    row['provenance']=provenance
    (OUT/(a.id+'.json')).write_text(json.dumps(row,separators=(',',':')))
    result={'status':'completed','failure':row['failure'],'success':row.get('success',row.get('complete_sequence_success')),
            'steps':row['episode']['steps'],'wall_seconds':time.perf_counter()-started}
    finish(a.id,result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
