"""Optimize complete multi-family unions with a feasible incumbent hint."""
import argparse,collections,hashlib,json,os,pathlib,random,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,pool_hash,digest_words
from supervisor import verify
def main():
 from ortools.sat.python import cp_model
 p=argparse.ArgumentParser();p.add_argument("--case",type=int,required=True);a=p.parse_args()
 out=ROOT/"artifacts/phase3/fusion_001"/("case_"+str(a.case));out.mkdir(parents=True,exist_ok=True)
 baseline=[int(w,2) for w in (ROOT/"artifacts/best_code.txt").read_text().splitlines()];accepted=verify(ROOT/"artifacts/best_code.txt")
 parents=[];arena=set()
 for path in sorted((ROOT/"artifacts/baselines").glob("arena_*.txt")):
  checked=verify(path);words=[int(w,2) for w in path.read_text().splitlines()];arena.update(words)
  parents.append({"path":str(path.relative_to(ROOT.parent)),"sha256":checked["reports"][0]["witness_sha256"],"cardinality":checked["cardinality"]})
 projected=set()
 folder=ROOT/"artifacts/phase3/short_polish_001"
 if folder.exists():
  for path in sorted(folder.rglob("worker_*.txt")):
   checked=verify(path);projected.update(int(w,2) for w in path.read_text().splitlines())
   parents.append({"path":str(path.relative_to(ROOT.parent)),"sha256":checked["reports"][0]["witness_sha256"],"cardinality":checked["cardinality"]})
 raw=set()
 for seed in [950002,950003]:
  r=json.loads((ROOT/"artifacts/phase3/infeasible_probe_003"/("probe_"+str(seed))/"report.json").read_text())
  for experiment in r["experiments"]:
   if experiment["mode"]=="pairbreak" and experiment["minimum_pair_energy"]<=3:
    for state in experiment.get("near_archive",[]):raw.update(state["words"])
 inc=Incidence(16)
 if a.case==0:pool=arena;definition="All words from all five independently verified arena families; no outside fixed words"
 elif a.case==1:pool=arena|projected;definition="Arena families plus all independently verified short-run projections/polishes"
 elif a.case==2:pool=arena|projected|raw;definition="Add word candidates from explicitly invalid low-conflict states; those parent states are not accepted codes"
 else:
  pool=arena|projected|raw;blockers=inc.blockers(baseline);rng=random.Random(991003);extra=[w for w in range(65536) if w not in pool]
  rng.shuffle(extra);extra.sort(key=lambda w:(blockers[w].bit_count(),inc.sizes[w]))
  pool.update(extra[:max(0,3000-len(pool))]);definition="Multi-family union plus lowest-blocker opportunity words up to 3000 candidates; ties seeded 991003"
 pool=sorted(pool);assert set(baseline)<=set(pool)
 model=cp_model.CpModel();vv={w:model.new_bool_var("w"+str(w)) for w in pool};children=collections.defaultdict(list)
 for w,v in vv.items():
  for d in inc.desc[w]:children[d].append(v)
 for variables in children.values():
  if len(variables)>1:model.add_at_most_one(variables)
 model.add(sum(vv.values())>=len(baseline));model.maximize(sum(vv.values()))
 for w,v in vv.items():model.add_hint(v,int(w in set(baseline)))
 solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=120;solver.parameters.num_search_workers=2;solver.parameters.random_seed=991000+a.case
 start=time.perf_counter();cput=time.process_time();status=solver.solve(model);code=baseline
 if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:code=[w for w,v in vv.items() if solver.value(v)]
 path=out/"worker_fusion.txt";path.write_text(canonical(code));checked=verify(path)
 report={"source_sha":os.environ["GITHUB_SHA"],"case":a.case,"definition":definition,"parents":parents,"fixed_outside":[],
  "candidate_pool":pool,"candidate_pool_sha256":pool_hash(pool),"encoded_model_sha256":hashlib.sha256(model.proto.SerializeToString()).hexdigest(),
  "objective":"Maximize code cardinality; complete independently feasible baseline hint, no strict-improvement feasibility constraint",
  "solver_status":solver.status_name(status),"solver_bound":solver.best_objective_bound,"wall_seconds":time.perf_counter()-start,"cpu_seconds":time.process_time()-cput,
  "wall_cap_seconds":120,"workers":2,"baseline_cardinality":len(baseline),"best_independent_verification":checked,
  "proof_artifact":None,"global_optimality_claim":False}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("FUSION "+json.dumps({"case":a.case,"pool":len(pool),"status":report["solver_status"],"bound":report["solver_bound"],"best_verified":checked["cardinality"]}),flush=True)
if __name__=="__main__":main()
