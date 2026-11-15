"""Matched wide exact packing models, with or without source-audited local closure cuts."""
import gzip,hashlib,json,os,pathlib,random,resource,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.core_hulls import add_known_goal_exclusions,symmetries
from phase3.fresh_cp_model import add_closed_overlap_cuts
from ortools.sat.python import cp_model
start=time.monotonic();ru0=resource.getrusage(resource.RUSAGE_SELF);ch0=resource.getrusage(resource.RUSAGE_CHILDREN);check_integrity();case=int(sys.argv[1]);pair=case//2;learned=bool(case%2);out=ROOT/"artifacts/phase3/fresh_cp_001"/str(case);out.mkdir(parents=True,exist_ok=True)
(out/"environment.txt").write_text(subprocess.run([sys.executable,"-m","pip","freeze"],text=True,capture_output=True,check=True).stdout)
planpath=ROOT/"phase3/fresh_cp_plan.json";plan=json.loads(planpath.read_text());row=plan["seeds"][pair];C=row["words"][:];sourceC=C[:];normalization=[]
for w in C[:]:
 if w.bit_count()<=2 and w!=0:C.remove(w);C.append(0);normalization.append([w,0])
 if w.bit_count()>=14 and w!=65535:C.remove(w);C.append(65535);normalization.append([w,65535])
C=sorted(C);hintpath=out/"hint225.txt";hintpath.write_text(canonical(C));hintv=verify(hintpath);assert hintv["cardinality"]==225
seed=1518001+pair;others=[w for w in C if w not in [0,65535]];random.Random(seed).shuffle(others);fixed=set([0,65535]+others[:62]);assert len(fixed)==64 and fixed<=set(C)
fixedpath=out/"fixed.txt";fixedpath.write_text(canonical(fixed));fixedv=verify(fixedpath)
inc=Incidence(16);pool=inc.compatible_pool(fixed);profile=row["profile64"];assert digest_words(fixed)==profile["fixed_sha256"] and digest_words(C)==profile["hint_sha256"] and pool_hash(pool)==profile["pool_sha256"] and len(pool)==profile["pool_count"]
assert len(pool)<=12000 and set(C)-fixed<=set(pool) and not fixed&set(pool);(out/"candidate_pool.txt").write_text("\n".join(map(str,pool))+"\n")
cuts=json.loads((out.parent/"cuts.json").read_text());assert cuts["passed"] and cuts["source_sha"]==os.environ["GITHUB_SHA"] and len(cuts["sets"])==24
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known={tuple(K) for B in info["codes"] for K in symmetries(B)}
model=cp_model.CpModel();xs={w:model.new_bool_var("w"+str(w)) for w in pool};at={}
for w,x in xs.items():
 for d in inc.desc[w]:at.setdefault(d,[]).append(x)
for group in at.values():
 if len(group)>1:model.add_at_most_one(group)
total=sum(xs.values())+len(fixed);model.add(total>=225);model.add(total<=227);model.maximize(total);known_count=add_known_goal_exclusions(model,xs,fixed,known,target=226)
applied=add_closed_overlap_cuts(model,xs,fixed,cuts["sets"],baseline=225) if learned else []
for w,x in xs.items():model.add_hint(x,int(w in C))
validation=model.validate();assert not validation,validation
binary=model.proto.SerializeToString(deterministic=True);text=str(model.proto).encode();z=gzip.compress(text,mtime=0);(out/"model.pbtxt.gz").write_bytes(z)
report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"pair":pair,"condition":"conditional_K8_overlap_cuts" if learned else "uncut_control","seed":seed,"starting_source_guided_case":row["source_case"],"source225_sha256":digest_words(sourceC),"normalization":normalization,"hint_sha256":digest_words(C),"hint_verification":hintv,"fixed_count":len(fixed),"fixed_sha256":digest_words(fixed),"fixed_verification":fixedv,"pool_count":len(pool),"pool_sha256":pool_hash(pool),"pool_restriction":"All65536words compatible with this fixed64, no candidate subsampling","incidences":sum(len(inc.desc[w]) for w in pool),"model_sha256":hashlib.sha256(binary).hexdigest(),"model_text_sha256":hashlib.sha256(text).hexdigest(),"model_gzip_sha256":hashlib.sha256(z).hexdigest(),"cuts_source_sha256":hashlib.sha256((out.parent/"cuts.json").read_bytes()).hexdigest(),"conditional_cuts":applied,"known_exact226_exclusions":known_count,"solver_wall_limit_seconds":150,"solver_workers":2,"solutions":[],"best_seed_verified":225,"solver_best_verified":None,"retained_global_best_verified":226,"proof_artifact":None}
(out/"plan.json").write_text(json.dumps(report,indent=2));seen=set();count225=0;count226=0;best=225
def accept(Q,elapsed):
 global count225,count226,best
 h=digest_words(Q)
 if h in seen:return
 if len(Q)==225 and count225:return
 if len(Q)==226 and count226>=8:return
 seen.add(h);path=out/("candidate_"+str(len(report["solutions"]))+".txt");path.write_text(canonical(Q));v=verify(path);assert 225<=v["cardinality"]<=227
 if len(Q)==226:assert tuple(sorted(Q)) not in known;count226+=1
 if len(Q)==225:count225+=1
 violations=[i for i,row in enumerate(cuts["sets"]) if len(set(Q)&set(row["words"]))>row["limit"]] if len(Q)>=226 else []
 if violations:print("CUT_CONTRADICTION",case,len(Q),violations,flush=True)
 report["solutions"].append({"path":path.name,"verification":v,"solver_seconds":elapsed,"conditional_cut_violations":violations});best=max(best,len(Q));report["solver_best_verified"]=max(report["solver_best_verified"] or 0,len(Q));report["retained_global_best_verified"]=max(226,best);(out/"progress.json").write_text(json.dumps(report,indent=2))
 print("FRESH_CP_FEASIBLE",case,len(Q),h,flush=True)
 if len(Q)>=226:print("VERIFIED_227" if len(Q)>=227 else "VERIFIED_NEW226",path,flush=True)
class Export(cp_model.CpSolverSolutionCallback):
 def on_solution_callback(self):
  Q=sorted(fixed|{w for w,x in xs.items() if self.value(x)});accept(Q,self.wall_time)
  if len(Q)>=227:self.stop_search()
solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=150;solver.parameters.num_search_workers=2;solver.parameters.random_seed=seed
before=resource.getrusage(resource.RUSAGE_SELF);t=time.monotonic();status=solver.solve(model,Export());after=resource.getrusage(resource.RUSAGE_SELF)
if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:accept(sorted(fixed|{w for w,x in xs.items() if solver.value(x)}),time.monotonic()-t)
report.update(status=solver.status_name(status),solver_wall_seconds=time.monotonic()-t,solver_process_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,best_objective_bound_total=solver.best_objective_bound if status in [cp_model.OPTIMAL,cp_model.FEASIBLE] else None,response_stats=solver.response_stats(),best_method_independently_verified=best,retained_global_best_verified=max(226,best),wall_including_model_and_verification=time.monotonic()-start,scope="Four paired wide fixed64packing families on new225seeds. Same fixed set/full pool/hint/seed,150solver-wall/two-worker caps; actual processCPU recorded, not a matched-native-CPU claim. Control has only exact-known226goal exclusions; treatment adds source-audited unfiltered K8overlap caps, conditional on size>=226.225hints remain eligible and larger supersets of known226remain eligible. Every positive uses both unchanged protected verifiers. A timeout is open; OPTIMAL225only concerns this encoded fixed family/goal model and treatment evidence assumptions, never global optimality. No Tinker or global-record claim.")
if status in [cp_model.INFEASIBLE,cp_model.MODEL_INVALID]:report["contradiction"]="Model contradicted the independently verified feasible225hint or was invalid; do not treat as absence"
ru=resource.getrusage(resource.RUSAGE_SELF);ch=resource.getrusage(resource.RUSAGE_CHILDREN);report["controller_and_solver_self_cpu_seconds"]=ru.ru_utime+ru.ru_stime-ru0.ru_utime-ru0.ru_stime;report["verifier_children_cpu_seconds"]=ch.ru_utime+ch.ru_stime-ch0.ru_utime-ch0.ru_stime
(out/"report.json").write_text(json.dumps(report,indent=2));print("FRESH_CP_RESULT",json.dumps({k:report[k] for k in ["case","condition","status","pool_count","solver_best_verified","best_method_independently_verified","retained_global_best_verified","best_objective_bound_total","solver_wall_seconds","solver_process_cpu_seconds"]}),flush=True)
if status in [cp_model.INFEASIBLE,cp_model.MODEL_INVALID]:raise RuntimeError(report["contradiction"])
