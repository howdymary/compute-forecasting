"""Whole weight-band reoptimization and matched-size random controls."""
import argparse,hashlib,json,os,pathlib,random,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from ortools.sat.python import cp_model
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);a=ap.parse_args();case=a.case;lo,hi=[(3,7),(5,9),(7,11),(9,13)][case//2]
 out=ROOT/"artifacts/phase3/weight_band_001"/str(case);out.mkdir(parents=True,exist_ok=True);check_integrity()
 base=ROOT/"artifacts/phase3/weight_band_001/preflight/baseline.txt";accepted=verify(base);C={int(w,2) for w in base.read_text().split()};assert len(C)==226
 removed={w for w in C if lo<=w.bit_count()<=hi};condition="weight_band" if case%2==0 else "matched_size_random"
 if case%2:removed=set(random.Random(1170001+case//2).sample(sorted(C),len(removed)))
 fixed=C-removed;inc=Incidence(16);pool=inc.compatible_pool(fixed);assert removed<=set(pool)
 (out/"fixed.txt").write_text(canonical(fixed));(out/"pool.json").write_text(json.dumps(pool));(out/"starting.txt").write_text(canonical(C))
 model=cp_model.CpModel();xs={w:model.new_bool_var("w"+str(w)) for w in pool};at={}
 for w,x in xs.items():
  for d in inc.desc[w]:at.setdefault(d,[]).append(x)
 for group in at.values():
  if len(group)>1:model.add_at_most_one(group)
 target=len(removed)+1;model.add(sum(xs.values())>=target);model.maximize(sum(xs.values()))
 for w,x in xs.items():model.add_hint(x,int(w in removed))
 assert not model.validate()
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"condition":condition,"seed":1170001+case//2,"weight_band":[lo,hi],"removed_count":len(removed),
  "fixed_count":len(fixed),"fixed_sha256":digest_words(fixed),"incumbent_verification":accepted,"pool_count":len(pool),"pool_sha256":pool_hash(pool),
  "target_added":target,"model_sha256":hashlib.sha256(str(model.proto).encode()).hexdigest(),"solutions":[],"seconds_limit":300,"workers":2,
  "hypothesis":"Deletion descendant weights lie in [wt(x)-2,wt(x)], so conflicts occur only between weight layers at distance at most two. Reoptimize an entire multi-layer band rather than a bounded k-exchange. Random controls remove the same number of incumbent words.",
  "scope":"Every binary 16-bit word compatible with the explicitly fixed outside code is eligible. No component, symmetry, dominance or learned cuts; a timeout is not local optimality.",
  "proof_artifact":None}
 (out/"plan.json").write_text(json.dumps(report,indent=2))
 class Export(cp_model.CpSolverSolutionCallback):
  def on_solution_callback(self):
   Q=fixed|{w for w,x in xs.items() if self.value(x)};p=out/("candidate_"+str(len(report["solutions"]))+".txt");p.write_text(canonical(Q));v=verify(p)
   assert v["cardinality"]>226
   report["solutions"].append({"witness":p.name,"verification":v,"solver_seconds":self.wall_time})
   (out/"progress.json").write_text(json.dumps(report,indent=2));self.stop_search()
 solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=300;solver.parameters.num_search_workers=2;solver.parameters.random_seed=1170001+case//2
 t=time.monotonic();status=solver.solve(model,Export());report.update(status=solver.status_name(status),wall_seconds=time.monotonic()-t,best_objective_bound=solver.best_objective_bound,
  conflicts=solver.num_conflicts,branches=solver.num_branches,response_stats=solver.response_stats(),best_verified=max([226]+[x["verification"]["cardinality"] for x in report["solutions"]]),
  conclusion="Encoded fixed-outside strict-improvement infeasible" if status==cp_model.INFEASIBLE else "Verified strict improvement" if report["solutions"] else "No improvement within budget; neighborhood open")
 (out/"report.json").write_text(json.dumps(report,indent=2));print("WEIGHT_BAND",json.dumps({k:report[k] for k in ["case","condition","removed_count","pool_count","status","best_verified","wall_seconds"]}),flush=True)
if __name__=="__main__":main()
