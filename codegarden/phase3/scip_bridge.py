"""Feasibility-focused SCIP search on explicitly backbone-excluded unions."""
import argparse,hashlib,json,os,pathlib,random,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,pool_hash,digest_words
from supervisor import verify,check_integrity
from phase3.pool_bridge import orbit
from ortools.linear_solver import pywraplp
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case
 out=ROOT/"artifacts/phase3/scip_bridge_001"/str(case);out.mkdir(parents=True,exist_ok=True);check_integrity()
 known=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text())["codes"];baseline=next((ROOT/"artifacts/baselines").glob("arena_225_*.txt"));start={int(w,2) for w in baseline.read_text().split()};verify(baseline)
 union=set(json.loads((ROOT/"artifacts/phase3/cp_lns_001/0/plan.json").read_text())["candidate_pool"]);rng=random.Random(1180001+case//2);banned=set()
 for family in range(4):
  core=set.intersection(*(orbit(C)[family] for C in known));banned.add(rng.choice(sorted((core&union)-start-{0,65535})))
 assert all(set(O)&banned for C in known for O in orbit(C))
 pool=sorted(union-banned);target=226+case%2;inc=Incidence(16);solver=pywraplp.Solver.CreateSolver("SCIP");assert solver is not None,"SCIP backend unavailable"
 xs={w:solver.BoolVar("w"+str(w)) for w in pool};at={}
 for w,x in xs.items():
  for d in inc.desc[w]:at.setdefault(d,[]).append(x)
 for d,group in at.items():
  if len(group)>1:
   row=solver.RowConstraint(-solver.infinity(),1,"d"+str(d))
   for x in group:row.SetCoefficient(x,1)
 row=solver.RowConstraint(target,solver.infinity(),"minimum_cardinality")
 for x in xs.values():row.SetCoefficient(x,1)
 solver.SetHint(list(xs.values()),[float(w in start) for w in pool]);solver.SetTimeLimit(300000);solver.SetNumThreads(2)
 model=solver.ExportModelAsLpFormat(False);(out/"model.txt").write_text(model);(out/"pool.json").write_text(json.dumps(pool))
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"target":target,"forbidden":sorted(banned),"pool_count":len(pool),"pool_hash":pool_hash(pool),
  "model_sha256":hashlib.sha256(model.encode()).hexdigest(),"solver":solver.SolverVersion(),"seconds_limit":300,"workers":2,"best_verified":226,"best_exported":225,
  "hint":"Verified 225-word code, intentionally below target. A hint is not a feasible result.",
  "hypothesis":"A separate MILP feasibility formulation and clique/LP processing may escape the CP-SAT and local-search basin.",
  "scope":"Restricted explicit union and four backbone exclusions. Zero objective; OPTIMAL with a solution means encoded feasibility only. INFEASIBLE is restricted to this model; no global conclusion.",
  "documentation":"https://developers.google.com/optimization/mip/mip_example"}
 (out/"plan.json").write_text(json.dumps(report,indent=2));t=time.monotonic();status=solver.Solve()
 statuses={solver.OPTIMAL:"FEASIBLE_ZERO_OBJECTIVE",solver.FEASIBLE:"FEASIBLE",solver.INFEASIBLE:"INFEASIBLE",solver.UNBOUNDED:"UNBOUNDED",solver.ABNORMAL:"ABNORMAL",solver.NOT_SOLVED:"NOT_SOLVED"}
 report.update(status=statuses.get(status,str(status)),wall_seconds=time.monotonic()-t,nodes=solver.nodes(),iterations=solver.iterations(),followups=[])
 if status in [solver.OPTIMAL,solver.FEASIBLE]:
  C={w for w,x in xs.items() if x.solution_value()>.5};p=out/"candidate.txt";p.write_text(canonical(C));v=verify(p);assert v["cardinality"]>=target
  report.update(verification=v,best_exported=v["cardinality"],best_verified=max(226,v["cardinality"]))
  if len(C)==226:
   assert all(C!=set(O) for A in known for O in orbit(A))
   for k in [3,5,7,9]:
    r=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),"30","1000000000000","0"],input=p.read_text(),text=True,capture_output=True,check=True,timeout=90,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1")).stdout)
    r["pool_hash"]=pool_hash(r.pop("candidate_pool"));r.pop("neighbors")
    if r["found"]:
     A=C-set(r["removed"])|set(r["added"]);q=out/"improvement.txt";q.write_text(canonical(A));r["verification"]=verify(q);report["best_verified"]=r["verification"]["cardinality"]
    report["followups"].append(r)
    if report["best_verified"]>=227:break
 (out/"report.json").write_text(json.dumps(report,indent=2));print("SCIP_BRIDGE",json.dumps({k:report[k] for k in ["case","target","status","best_exported","best_verified","wall_seconds"]}),flush=True)
if __name__=="__main__":main()
