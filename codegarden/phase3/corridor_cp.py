"""Switch unresolved whole-corridor models to feasibility CP-SAT with uncut controls."""
import gzip,hashlib,json,os,pathlib,resource,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash,Incidence
from supervisor import verify,check_integrity
from phase3.core_hulls import add_known_goal_exclusions
from ortools.sat.python import cp_model
check_integrity();case=int(sys.argv[1]);pair=case//2;learned=bool(case%2);OUT=ROOT/"artifacts/phase3/corridor_cp_001";out=OUT/"workers"/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((OUT/"plan.json").read_text());assert plan["source_sha"]==os.environ["GITHUB_SHA"];row=plan["families"][pair];fixed=set(row["fixed"]);P=row["pool"];C=set(row["hint_words"]);high=set(row["outside_high"]);known={tuple(map(int,l.split()[1:])) for l in (OUT/"known226.txt").read_text().splitlines()};inc=Incidence(16);occupied=inc.occupied(fixed);assert len(P)==len(set(P)) and not fixed&set(P) and all(not occupied&inc.masks[w] for w in P)
(out/"fixed.txt").write_text(canonical(fixed));(out/"pool.txt").write_text("\n".join(map(str,P))+"\n");(out/"hint.txt").write_text(canonical(C));hintv=verify(out/"hint.txt");(out/"environment.txt").write_text(subprocess.run([sys.executable,"-m","pip","freeze"],text=True,capture_output=True,check=True).stdout)
model=cp_model.CpModel();xs={w:model.new_bool_var("w"+str(w)) for w in P};at={}
for w,x in xs.items():
 for d in inc.desc[w]:at.setdefault(d,[]).append(x)
for group in at.values():
 if len(group)>1:model.add_at_most_one(group)
total=sum(xs.values())+len(fixed);model.add(total>=226);excluded=add_known_goal_exclusions(model,xs,fixed,known,target=226)
if learned:model.add(sum(xs[w] for w in high)>=1)
for w in C-fixed:model.add_hint(xs[w],1)
assert not model.validate();binary=model.proto.SerializeToString(deterministic=True);text=str(model.proto).encode();z=gzip.compress(text,mtime=0);(out/"model.pbtxt.gz").write_bytes(z);seed=1540001+pair
report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"pair":pair,"source_parent":row["source_parent"],"blocker_threshold":row["blocker_threshold"],"condition":"conditional_high_blocker_requirement" if learned else "uncut_control","fixed_sha256":digest_words(fixed),"pool_sha256":pool_hash(P),"fixed_count":len(fixed),"pool_count":len(P),"hint_verification":hintv,"partial_positive_hint_only":True,"hint_can_be_infeasible":True,"outside_high_sha256":pool_hash(high),"conditional_cut_applied":learned,"known_exact226_exclusions":excluded,"target_minimum_total":226,"objective":None,"artificial_upper_bound":None,"model_sha256":hashlib.sha256(binary).hexdigest(),"model_text_sha256":hashlib.sha256(text).hexdigest(),"model_gzip_sha256":hashlib.sha256(z).hexdigest(),"solver_seed":seed,"solver_wall_limit_seconds":150,"solver_workers":2,"solutions":[],"best_seed_verified":len(C),"best_method_independently_verified":len(C),"retained_global_best_verified":226,"proof_artifact":None,"scope":plan["scope"]}
(out/"plan.json").write_text(json.dumps(report,indent=2))
class Export(cp_model.CpSolverSolutionCallback):
 def on_solution_callback(self):
  Q=sorted(fixed|{w for w,x in xs.items() if self.value(x)});p=out/"candidate.txt";p.write_text(canonical(Q));v=verify(p);assert v["cardinality"]>=226 and tuple(Q) not in known;violates=not bool(set(Q)&high)
  report["solutions"].append({"path":p.name,"verification":v,"solver_seconds":self.wall_time,"conditional_cut_violated":violates});report["best_method_independently_verified"]=max(len(C),len(Q));report["retained_global_best_verified"]=max(226,len(Q));(out/"progress.json").write_text(json.dumps(report,indent=2));print("VERIFIED_227" if len(Q)>=227 else "VERIFIED_NEW226",case,p,flush=True)
  if violates:print("CUT_CONTRADICTION_RETAINED",case,p,flush=True)
  self.stop_search()
solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=150;solver.parameters.num_search_workers=2;solver.parameters.random_seed=seed;solver.parameters.repair_hint=True;solver.parameters.hint_conflict_limit=1000
before=resource.getrusage(resource.RUSAGE_SELF);t=time.monotonic();status=solver.solve(model,Export());after=resource.getrusage(resource.RUSAGE_SELF)
report.update(status=solver.status_name(status),solver_wall_seconds=time.monotonic()-t,solver_process_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,response_stats=solver.response_stats(),conclusion="Encoded goal-model infeasible, conditional native assumptions in treatment only" if status==cp_model.INFEASIBLE else "No result within budget; model open" if status==cp_model.UNKNOWN else "Verified positive" if report["solutions"] else "Invalid or unexpected solver status")
follow=[]
if report["solutions"] and report["solutions"][0]["verification"]["cardinality"]==226:
 C=sorted(int(w,2) for w in (out/"candidate.txt").read_text().split())
 for k,sec in [(6,10),(8,45),(10,90),(12,150)]:
  env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0",CODEGARDEN_ROOT_BEGIN="0",CODEGARDEN_ROOT_END="65536",CODEGARDEN_KNOWN_GOAL_CODES="")
  r=json.loads(subprocess.run([str(ROOT/".build/bundle_colored"),"16",str(k),str(sec),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=sec+90,env=env).stdout);pp=r.pop("candidate_pool");r.pop("neighbors");r["pool_sha256"]=pool_hash(pp);r["starting_sha256"]=digest_words(C);(out/("strict_pool_"+str(k)+".txt")).write_text("\n".join(map(str,pp))+"\n")
  if r["found"]:
   C=sorted(set(C)-set(r["removed"])|set(r["added"]));p=out/("strict_"+str(k)+".txt");p.write_text(canonical(C));r["verification"]=verify(p);assert r["verification"]["cardinality"]>=227;r["path"]=p.name;report["best_method_independently_verified"]=len(C);report["retained_global_best_verified"]=len(C);print("VERIFIED_227",case,p,flush=True)
  follow.append(r)
  if len(C)>=227:break
report["strict_followups"]=follow;(out/"report.json").write_text(json.dumps(report,indent=2));print("CORRIDOR_CP_RESULT",json.dumps({k:report[k] for k in ["case","condition","blocker_threshold","status","pool_count","best_method_independently_verified","solver_wall_seconds","solver_process_cpu_seconds"]}),flush=True)
if status==cp_model.MODEL_INVALID:raise RuntimeError("CP model invalid")
