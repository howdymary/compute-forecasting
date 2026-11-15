"""Matched full-universe repairs fixing only a strong225 code's overlap with shared216."""
import argparse,hashlib,json,os,pathlib,random,resource,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.revisit_frontiers import orbit
from ortools.sat.python import cp_model
OUT=ROOT/"artifacts/phase3/core_hulls_001"
def symmetries(C):
 rev=lambda w:int(format(w,"016b")[::-1],2)
 return [sorted(C),sorted(65535^w for w in C),sorted(rev(w) for w in C),sorted(65535^rev(w) for w in C)]
def add_known_goal_exclusions(model,xs,fixed,known,target=226):
 total=sum(xs.values())+len(fixed);flag=model.new_bool_var("exact_known_size")
 model.add(total==target).only_enforce_if(flag);model.add(total!=target).only_enforce_if(flag.Not());count=0
 for C in known:
  K=set(C)
  if fixed<=K and K-fixed<=set(xs):
   model.add(sum(xs[w] for w in K-fixed)<=len(K-fixed)-1).only_enforce_if(flag);count+=1
 return count
def prepare():
 check_integrity();OUT.mkdir(parents=True,exist_ok=True);info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(C) for C in info["codes"]));old=json.loads((ROOT/"artifacts/phase3/frontier8_001/plan.json").read_text())["cases"];fresh=json.loads((ROOT/"artifacts/phase3/quota_frontiers_001/plan.json").read_text())["selected"];seeds=[old[0]["words"],old[1]["words"],fresh[0]["words"],fresh[min(4,len(fresh)-1)]["words"]];assert len({orbit(C) for C in seeds})==4
 rows=[]
 for i,C in enumerate(seeds):
  p=OUT/("seed_"+str(i)+".txt");p.write_text(canonical(C));v=verify(p);assert v["cardinality"]==225
  rows.append({"words":C,"sha256":digest_words(C),"core_overlap":len(set(C)&core),"verification":v})
 plan={"source_sha":os.environ["GITHUB_SHA"],"seeds":rows,"cases":8,"wall_limit_per_case":600,"solver_workers":2,"comparators":["conditional210-core-overlap cuts in four symmetry frames","exclude explicit known226 codes only at exact size226; larger codes remain eligible"],"hypothesis":"Fix only the shared-core words present in a strong225 seed, instead of forcing a few costly pivots or retaining most of its outside words. All other compatible words are eligible. Compare conditional closure cuts with exact known-code no-goods.","scope":"Four explicit fixed-core families, not global coverage. Equal solver wall/thread budgets, not a matched native-CPU claim."}
 (OUT/"plan.json").write_text(json.dumps(plan,indent=2));print("CORE_HULL_PLAN",json.dumps({"core_overlaps":[r["core_overlap"] for r in rows],"cases":8}),flush=True)
def run(case):
 check_integrity();out=OUT/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((OUT/"plan.json").read_text());item=plan["seeds"][case//2];C=set(item["words"]);info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(K) for K in info["codes"]));frames=[set(F) for F in symmetries(core)];known={tuple(K) for code in info["codes"] for K in symmetries(code)};fixed=C&core;inc=Incidence(16);pool=inc.compatible_pool(fixed);assert C-fixed<=set(pool);assert all(len(C&F)<=210 for F in frames)
 (out/"fixed.txt").write_text(canonical(fixed));(out/"pool.json").write_text(json.dumps(pool));(out/"starting.txt").write_text(canonical(C))
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"seed":1441001+case//2,"condition":"core_quota210" if case%2==0 else "exact_known226_exclusion","starting_verification":verify(out/"starting.txt"),"incumbent_sha256":digest_words(C),"fixed_count":len(fixed),"fixed_sha256":digest_words(fixed),"pool_count":len(pool),"pool_sha256":pool_hash(pool),"wall_limit_seconds":600,"solver_workers":2,"solutions":[],"best_in_family_verified":225,"retained_global_best_verified":226,"scope":"Only the full compatible universe for this explicit fixed core. Conditional core cuts rely on earlier computational closure; exact-size known-code exclusions reject only supplied226 arrays, not larger supersets. No global optimality or record inference.","proof_artifact":None}
 if len(pool)>8000:
  report["status"]="POOL_MEMORY_GATE";(out/"report.json").write_text(json.dumps(report,indent=2));print("CORE_HULL_SKIP",case,len(pool),flush=True);return
 model=cp_model.CpModel();xs={w:model.new_bool_var("w"+str(w)) for w in pool};at={}
 for w,x in xs.items():
  for d in inc.desc[w]:at.setdefault(d,[]).append(x)
 for group in at.values():
  if len(group)>1:model.add_at_most_one(group)
 total=sum(xs.values())+len(fixed);model.add(total>=225);model.maximize(sum(xs.values()))
 if case%2==0:
  for F in frames:model.add(sum(x for w,x in xs.items() if w in F)<=210-len(fixed&F))
  assert all(any(len(set(K)&F)>210 for F in frames) for K in known)
  report["known_exclusion_count"]=0
 else:report["known_exclusion_count"]=add_known_goal_exclusions(model,xs,fixed,known)
 for w,x in xs.items():model.add_hint(x,int(w in C))
 assert not model.validate();proto=model.proto.SerializeToString(deterministic=True);report["model_sha256"]=hashlib.sha256(proto).hexdigest();(out/"model.pbtxt").write_text(str(model.proto));(out/"plan.json").write_text(json.dumps(report,indent=2))
 class Export(cp_model.CpSolverSolutionCallback):
  def on_solution_callback(self):
   Q=sorted(fixed|{w for w,x in xs.items() if self.value(x)});p=out/("candidate_"+str(len(report["solutions"]))+".txt");p.write_text(canonical(Q));v=verify(p);assert v["cardinality"]>=225
   if len(Q)==226:assert tuple(Q) not in known
   report["best_in_family_verified"]=max(report["best_in_family_verified"],len(Q));report["solutions"].append({"witness":p.name,"verification":v,"wall_seconds":self.wall_time});(out/"progress.json").write_text(json.dumps(report,indent=2))
   print("CORE_HULL_FEASIBLE",json.dumps({"case":case,"size":len(Q),"hash":digest_words(Q)}),flush=True)
   if len(Q)>=226:self.stop_search()
 solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=600;solver.parameters.num_search_workers=2;solver.parameters.random_seed=1441001+case//2
 before=resource.getrusage(resource.RUSAGE_SELF);start=time.monotonic();status=solver.solve(model,Export());after=resource.getrusage(resource.RUSAGE_SELF)
 report.update(status=solver.status_name(status),wall_seconds=time.monotonic()-start,process_cpu_seconds=(after.ru_utime+after.ru_stime)-(before.ru_utime+before.ru_stime),best_objective_bound_added=solver.best_objective_bound,response_stats=solver.response_stats(),retained_global_best_verified=max(226,report["best_in_family_verified"]),polish=[])
 if status==cp_model.INFEASIBLE:raise RuntimeError("Model contradicted the independently valid225 seed; investigate, do not claim an absence result")
 for row in report["solutions"]:
  if row["verification"]["cardinality"]<226:continue
  path=out/row["witness"];A=[int(w,2) for w in path.read_text().split()]
  if len(A)>=227:break
  for k,seconds in [(6,5),(7,20),(8,60),(9,120),(10,180)]:
   r=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),str(seconds),"1000000000000","0"],input=canonical(A),text=True,capture_output=True,check=True,timeout=seconds+100,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0")).stdout);r["incumbent_sha256"]=digest_words(A);r["pool_sha256"]=pool_hash(r.pop("candidate_pool"));r.pop("neighbors")
   if r["found"]:
    A=sorted(set(A)-set(r["removed"])|set(r["added"]));p=out/("augmented_"+str(k)+".txt");p.write_text(canonical(A));r["verification"]=verify(p);report["retained_global_best_verified"]=max(report["retained_global_best_verified"],len(A))
   report["polish"].append(r)
   if len(A)>=227:break
 report["conclusion"]="New independently verified code in this family" if report["best_in_family_verified"]>=226 else "Encoded family optimum225" if status==cp_model.OPTIMAL else "No new226 within budget; family remains open"
 (out/"report.json").write_text(json.dumps(report,indent=2));print("CORE_HULL",json.dumps({k:report[k] for k in ["case","condition","fixed_count","pool_count","status","best_in_family_verified","retained_global_best_verified","wall_seconds"]}),flush=True)
 if report["retained_global_best_verified"]>=227:print("CORE_HULL_VERIFIED_227",flush=True)
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--prepare",action="store_true");ap.add_argument("--case",type=int);a=ap.parse_args();prepare() if a.prepare else run(a.case)
