"""Sparse descendant-occupancy CP-SAT repairs. Optional OR-Tools dependency."""
import argparse,hashlib,json,pathlib,time
def solve(inc,pool,target,seed_code=(),seconds=30,seed=0,workers=2):
    from ortools.sat.python import cp_model
    pool=sorted(set(pool));model=cp_model.CpModel()
    variables=[model.new_bool_var("w"+str(w)) for w in pool]
    by_desc={}
    for i,w in enumerate(pool):
        for d in inc.desc[w]:by_desc.setdefault(d,[]).append(variables[i])
    for variables_at_d in by_desc.values():
        if len(variables_at_d)>1:model.add_at_most_one(variables_at_d)
    model.add(sum(variables)>=target)
    selected=set(seed_code)
    for i,w in enumerate(pool):
        if w in selected:model.add_hint(variables[i],1)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds
    solver.parameters.num_search_workers=workers;solver.parameters.random_seed=seed
    solver.parameters.log_search_progress=False
    t=time.perf_counter();status=solver.solve(model)
    name=solver.status_name(status)
    code=[w for w,v in zip(pool,variables) if solver.value(v)] if status in [cp_model.OPTIMAL,cp_model.FEASIBLE] else []
    if code:inc.occupied(code)
    raw=str(model.proto).encode("utf-8")
    return code,{"solver":"OR-Tools CP-SAT","status":name,"target":target,"seconds_limit":seconds,
      "wall_seconds":time.perf_counter()-t,"workers":workers,"seed":seed,
      "candidate_pool_sha256":hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in pool)).hexdigest(),
      "candidate_pool_size":len(pool),"descendant_constraints":len(by_desc),
      "encoded_model_text_sha256":hashlib.sha256(raw).hexdigest(),"proof_artifact":None,
      "complete":status==cp_model.INFEASIBLE,
      "conclusion":"no feasible target in this encoded pool" if status==cp_model.INFEASIBLE else
        "feasible independently verifiable witness" if code else "no conclusion before limit"}
def main():
    import importlib.util,sys
    root=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(root))
    from search import Incidence,canonical,digest_words
    from supervisor import verify
    p=argparse.ArgumentParser();p.add_argument("--start",required=True);p.add_argument("--seconds",type=float,default=30)
    p.add_argument("--global-pool",action="store_true");p.add_argument("--seed",type=int,default=0)
    p.add_argument("--output",default="codegarden/artifacts/cp_sat_run.json");a=p.parse_args()
    accepted=verify(a.start);words=pathlib.Path(a.start).read_text().splitlines()
    start=[int(w,2) for w in words];inc=Incidence(16);experiments=[];best=start
    bands=[None] if a.global_pool else [list(range(w,w+3)) for w in range(0,15,2)]
    for i,band in enumerate(bands):
        removed=start if band is None else [w for w in start if w.bit_count() in band]
        fixed=[] if band is None else [w for w in start if w not in removed]
        pool=list(range(65536)) if band is None else inc.compatible_pool(fixed)
        code,r=solve(inc,pool,len(removed)+1,removed,a.seconds,a.seed+i)
        r.update({"weight_band":band,"fixed_outside":sorted(fixed),"fixed_outside_sha256":digest_words(fixed),
                  "candidate_pool":pool,"incumbent_sha256":accepted["reports"][0]["witness_sha256"]})
        if code:
            trial=fixed+code;path=pathlib.Path(a.output).with_suffix(".candidate.txt")
            path.write_text(canonical(trial));r["verification"]=verify(path)
            if len(trial)>len(best):best=trial
        experiments.append(r)
    out=pathlib.Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    witness=out.with_suffix(".txt");witness.write_text(canonical(best))
    report={"method":"sparse_CP_SAT","experiments":experiments,"best_verification":verify(witness),
      "global_optimality_claim":False,"source":"codegarden/cp_sat.py"}
    out.write_text(json.dumps(report));print(json.dumps({"path":str(out),"verified_best":len(best),"statuses":[r["status"] for r in experiments]}))
if __name__=="__main__":main()
