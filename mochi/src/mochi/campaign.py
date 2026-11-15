"""Budget-matched search; freeze before holdout and changed-condition evaluation."""
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib,json,time
import numpy as np
from .simulation import Policy, PROTOCOL, PROTOCOL_SHA, evaluate, summarize, rollout

def write(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False))

def candidates(seed=42,n=12,feedback=False):
    rng=np.random.default_rng(seed)
    return [Policy(name=f'{"feedback" if feedback else "random"}-{i:02}',speed=float(rng.uniform(.04,.18)),stop_distance=float(rng.uniform(.008,.025)),approach_offset=float(rng.uniform(.04,.06)),recovery=feedback) for i in range(n)]

def rank(row):return (row['summary']['successes'],-row['summary']['mean_final_distance_m'])

def local_campaign(out):
    start=time.perf_counter();out=Path(out); seeds=PROTOCOL['development_seeds']; initial=Policy()
    rows=[]
    for p in candidates():
        results=evaluate(p,seeds);rows.append({'policy':asdict(p),'summary':summarize(results),'results':results})
    selected=max(rows,key=rank);winner=Policy(**selected['policy'])
    frozen=hashlib.sha256(json.dumps(asdict(winner),sort_keys=True).encode()).hexdigest()
    sections={}
    for label,ss,shift in [('development',seeds,False),('heldout',PROTOCOL['heldout_seeds'],False),('changed_conditions',PROTOCOL['shift_seeds'],True)]:
        a=evaluate(initial,ss,shift); b=evaluate(winner,ss,shift)
        sections[label]={'baseline':summarize(a),'selected':summarize(b),'paired_results':{'baseline':a,'selected':b}}
    # Illustration is disclosed as selected on development, not held-out evidence.
    a=sections['development']['paired_results']['baseline'];b=sections['development']['paired_results']['selected']
    demo=next((x['scenario']['seed'] for x,y in zip(a,b) if not x['success'] and y['success']),seeds[0])
    for name,p in [('baseline',initial),('selected',winner)]:write(out/f'{name}.json',rollout(p,demo,record=True))
    held=PROTOCOL['heldout_seeds'][0]; write(out/'heldout.json',rollout(winner,held,record=True))
    report={'schema':1,'run_id':datetime.now(timezone.utc).strftime('mochi-local-%Y%m%dT%H%M%SZ'),'created_at':datetime.now(timezone.utc).isoformat(),'mode':'local-conventional-search','claims':'Deterministic parameter search only. No model, Exa, past.dev, or Modal calls occurred in this local run.','protocol_sha256':PROTOCOL_SHA,'candidate_count':len(rows),'search_rollouts':len(rows)*len(seeds),'selection_rule':PROTOCOL['selection'],'selected':asdict(winner),'selected_sha256':frozen,'candidates':rows,'evaluation':sections,'demo_seed':demo,'demo_scope':'Development illustration selected for a visible baseline failure; see all paired trials for evaluation.','services':{'exa':'not executed','past':'not executed','modal':'not executed','model':'not executed'},'seconds':time.perf_counter()-start,'sources':[],'memory':[]}
    write(out/'report.json',report);return report
