"""Release all conflict endpoints, then expand through actual blocker closures."""
import argparse,hashlib,json,os,pathlib,random,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,digest_words,pool_hash
from phase3.refine import minimum_covers
from supervisor import verify
from ortools.sat.python import cp_model
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--seed",type=int,required=True);a=ap.parse_args();seed=a.seed;rng=random.Random(seed)
 out=ROOT/"artifacts/phase3/defect_closure_001"/str(seed);out.mkdir(parents=True,exist_ok=True)
 native=json.loads((ROOT/"artifacts/phase3/modal_pair_001/workers/3.json").read_text())["native"]
 archived=sorted(native["near_archive"],key=lambda r:(r["energy"],-r["outside_original"]))
 rng.shuffle(archived);inc=Incidence(16);rows=[];best=226;started=time.monotonic()
 for stateid,item in enumerate(archived[:4]):
  state=set(item["words"]);covers,edges=minimum_covers(inc,state);endpoints={v for edge in edges for v in edge}
  base=state-covers[0];basefile=out/("projection_"+str(stateid)+".txt");basefile.write_text(canonical(base));verify(basefile)
  owner={d:w for w in base for d in inc.desc[w]};bad={d for w in endpoints for d in inc.desc[w]}
  blockers={w:set(owner[d] for d in inc.desc[w] if d in owner) for w in range(65536) if w not in base}
  overlap={w:len(bad.intersection(inc.desc[w])) for w in blockers}
  for size in [8,16,32,64,96]:
   removed=base&endpoints
   while len(removed)<size:
    scores=[]
    for w,B in blockers.items():
     new=B-removed
     if not new or len(new)>min(6,size-len(removed)):continue
     touch=len(B&removed)
     if not touch and not overlap[w]:continue
     score=(2*touch+3*min(overlap[w],5))/(len(new)+.5)+rng.random()*.8
     scores.append((score,w))
    if not scores:
     removed.add(rng.choice(sorted(base-removed)));continue
    scores.sort(reverse=True);w=rng.choice(scores[:min(24,len(scores))])[1];removed|=blockers[w]
   fixed=sorted(base-removed);inc.occupied(fixed);full=inc.compatible_pool(fixed);keep=set(removed)|((state-set(fixed))&set(full))
   if len(full)>8000:
    rest=[w for w in full if w not in keep];rng.shuffle(rest);pool=sorted(keep|set(rest[:8000-len(keep)]))
   else:pool=full
   model=cp_model.CpModel();xs={w:model.new_bool_var("w"+str(w)) for w in pool};by={}
   for w in pool:
    for d in inc.desc[w]:by.setdefault(d,[]).append(xs[w])
   for group in by.values():
    if len(group)>1:model.add_at_most_one(group)
   model.maximize(sum(xs.values()));model.add(sum(xs.values())>=len(removed))
   for w,x in xs.items():model.add_hint(x,int(w in removed))
   solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=12;solver.parameters.num_search_workers=2;solver.parameters.random_seed=seed+stateid+size
   t=time.monotonic();status=solver.solve(model);name=solver.status_name(status)
   row={"source_sha":os.environ["GITHUB_SHA"],"seed":seed,"state_id":stateid,"near_state":sorted(state),"near_state_valid":False,
    "conflict_endpoints_all_released":sorted(endpoints),"fixed_outside":fixed,"fixed_sha256":digest_words(fixed),"removed_from_valid_projection":sorted(removed),
    "candidate_pool":pool,"candidate_pool_sha256":pool_hash(pool),"pool_before_cap":len(full),"solver":"OR-Tools CP-SAT","workers":2,"seconds_limit":12,
    "status":name,"wall_seconds":time.monotonic()-t,"objective_bound":solver.best_objective_bound,"encoded_model_sha256":hashlib.sha256(str(model.proto).encode()).hexdigest(),
    "proof_artifact":None,"conclusion":"Encoded neighborhood optimum only" if status==cp_model.OPTIMAL else "Incomplete bounded search" if status==cp_model.UNKNOWN else "Feasible bounded result"}
   if status in [cp_model.FEASIBLE,cp_model.OPTIMAL]:
    selected=[w for w,x in xs.items() if solver.value(x)];code=fixed+selected;path=out/("candidate_"+str(stateid)+"_"+str(size)+".txt");path.write_text(canonical(code))
    row["independent_verification"]=verify(path);best=max(best,len(code))
   rows.append(row);report={"best_independently_verified":best,"experiments":rows,"scope":"Only explicitly encoded neighborhoods; no global optimality","wall_seconds":time.monotonic()-started}
   (out/"report.json").write_text(json.dumps(report,indent=2));print("DEFECT_CLOSURE",json.dumps({"seed":seed,"state":stateid,"size":size,"pool":len(pool),"status":name,"best":best}),flush=True)
   if best>=227:return
if __name__=="__main__":main()
