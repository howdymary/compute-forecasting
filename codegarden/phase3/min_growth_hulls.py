"""Expand a repair family only after exact solver closure; unknown is never impossibility."""
import argparse,ast,collections,gc,hashlib,json,os,pathlib,random,resource,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.core_hulls import add_known_goal_exclusions,symmetries
from ortools.sat.python import cp_model
OUT=ROOT/"artifacts/phase3/min_growth_hulls_001"
ENGINE=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
def prepare():
 check_integrity();OUT.mkdir(parents=True,exist_ok=True);parents=[]
 for case in [1,3,5,7]:
  p=ROOT/"artifacts/phase3/core_hulls_001"/str(case);r=json.loads((p/"report.json").read_text());assert r["source_sha"]=="e88696335e995a05c96884c69500c25643749cbe" and r["condition"]=="exact_known226_exclusion" and r["status"]=="OPTIMAL" and r["best_in_family_verified"]==225
  F=[int(w,2) for w in (p/"fixed.txt").read_text().split()];assert digest_words(F)==r["fixed_sha256"]
  last=r["solutions"][-1];C=[int(w,2) for w in (p/last["witness"]).read_text().split()];assert set(F)<=set(C);q=OUT/("parent_"+str(case)+".txt");q.write_text(canonical(C));v=verify(q);assert v["cardinality"]==225
  parents.append({"parent_case":case,"fixed":F,"words":C,"verification":v,"parent_report_sha256":hashlib.sha256((p/"report.json").read_bytes()).hexdigest(),"parent_model_sha256":r["model_sha256"],"parent_pool_sha256":r["pool_sha256"],"parent_source":r["source_sha"]})
 plan={"source_sha":os.environ["GITHUB_SHA"],"parents":parents,"cases":8,"search_wall_budget":600,"per_trial_seconds":20,"solver_workers":2,"comparators":["random single-word unfixing","adaptive unlock-ranked1/2/4-word unfixing"],"hypothesis":"A completed OPTIMAL225 family can be enlarged by unfixing core words. Carry its exclusion only for candidate size>=226, preserving feasible225 hints. On FEASIBLE/UNKNOWN restore the last closed fixed set and try another relaxation. Compare fixed/random to exhaustion-driven expansion under equal wall/thread envelopes.","scope":"Only explicit fixed-code families and their recorded relaxations. Solver completion is not an independent formal absence certificate; no global optimality claim."}
 (OUT/"plan.json").write_text(json.dumps(plan,indent=2));print("ADAPTIVE_HULL_PLAN",json.dumps({"parents":[len(p["fixed"]) for p in parents],"cases":8}),flush=True)
def attach_closed(model,xs,fixed,certs,threshold=226):
 total=sum(xs.values())+len(fixed);large=model.new_bool_var("candidate_at_least226");model.add(total>=threshold).only_enforce_if(large);model.add(total<=threshold-1).only_enforce_if(large.Not());used=[]
 for cert in certs:
  F=set(cert["fixed"]);remaining=F-fixed
  if not remaining<=set(xs):continue
  model.add(sum(xs[w] for w in remaining)+len(F&fixed)<=len(F)-1).only_enforce_if(large);used.append(cert["id"])
 return used
def run(case,resume=False):
 job_start=time.monotonic();job_cpu0=resource.getrusage(resource.RUSAGE_SELF);job_children0=resource.getrusage(resource.RUSAGE_CHILDREN);check_integrity();out=OUT/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((OUT/"plan.json").read_text());parent=plan["parents"][case//2];mode="random_one" if case%2==0 else "minimum_growth";rng=random.Random(1451001+case//2);inc=Incidence(16);info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(C) for C in info["codes"]));known={tuple(K) for C in info["codes"] for K in symmetries(C)}
 current=set(parent["fixed"]);C=parent["words"][:];assert pool_hash(inc.compatible_pool(current))==parent["parent_pool_sha256"];certs=[{"id":"parent_"+str(parent["parent_case"]),"fixed":sorted(current),"parent_report_sha256":parent["parent_report_sha256"]}];history=[];seen=set();batch=1;fast=0;open_trials=0;best=225;novel=None;start=time.monotonic()
 checkpoint=out/"checkpoint.json"
 if resume:
  state=json.loads(checkpoint.read_text());assert state["engine_sha256"]==ENGINE and state["case"]==case and state["best_in_family_verified"]==225;current=set(state["current_fixed"]);C=state["incumbent"];certs=state["certificates"];history=state["history"];seen={tuple(F) for F in state["seen_fixed"]};batch=state["batch"];fast=state["fast"];open_trials=state["open_trials"];rng.setstate(ast.literal_eval(state["rng_state"]))
 carried_trials=len(history);carried_closed=sum(r.get("status")=="OPTIMAL" for r in history);carried_open=open_trials;start=time.monotonic();bootstrap_wall=start-job_start
 p=out/"incumbent.txt";p.write_text(canonical(C));assert verify(p)["cardinality"]==225 and current<=set(C)
 def save():
  state={"source_sha":os.environ["GITHUB_SHA"],"engine_sha256":ENGINE,"case":case,"mode":mode,"current_fixed":sorted(current),"incumbent":C,"certificates":certs,"history":history,"seen_fixed":[list(F) for F in sorted(seen)],"batch":batch,"fast":fast,"open_trials":open_trials,"rng_state":repr(rng.getstate()),"best_in_family_verified":best,"scope":"Valid225 checkpoint and precisely scoped solver receipts; no unverified score or timeout inference."};checkpoint.write_text(json.dumps(state,indent=2));p.write_text(canonical(C))
 save()
 while time.monotonic()-start<597 and novel is None:
  remaining=600-(time.monotonic()-start)
  if remaining<3:break
  eligible=sorted(current-{0,65535})
  if not eligible:break
  k=min(batch if mode=="minimum_growth" else 1,len(eligible));removed=None
  if mode=="minimum_growth":
   owner={}
   for v in current:
    for d in inc.desc[v]:owner[d]=v
   benefit=collections.defaultdict(float)
   for w in range(65536):
    if w in core:continue
    first=-1;multiple=False
    for d in inc.desc[w]:
     b=owner.get(d,-1)
     if b>=0:
      if first<0:first=b
      elif first!=b:multiple=True;break
    if not multiple and first in current:benefit[first]+=1/max(1,len(inc.desc[w]))
   ranked=sorted(eligible,key=lambda v:(benefit[v],rng.random()))
   for attempt in range(64):
    choices=ranked[:max(k,min(len(ranked),k+attempt//4+2))]
    R=set(rng.sample(choices,k));F=current-R
    if tuple(sorted(F)) not in seen:removed=R;break
  else:
   for attempt in range(128):
    R=set(rng.sample(eligible,k));F=current-R
    if tuple(sorted(F)) not in seen:removed=R;break
  if removed is None:
   # A narrow ranked prefix is a proposal heuristic, never exhaustion evidence.
   fallback=eligible[:];rng.shuffle(fallback)
   if k==1:
    for v in fallback:
     if tuple(sorted(current-{v})) not in seen:removed={v};break
   else:
    for _ in range(256):
     R=set(rng.sample(eligible,k))
     if tuple(sorted(current-R)) not in seen:removed=R;break
  if removed is None:
   if mode=="minimum_growth" and batch>1:batch=1;continue
   break
  F=current-removed;key=tuple(sorted(F));seen.add(key);pool=inc.compatible_pool(F);trial_id=len(history);trial={"unlock_policy":mode,"id":"case"+str(case)+"_trial"+str(trial_id),"source_sha":os.environ["GITHUB_SHA"],"incumbent_sha256":digest_words(C),"fixed":sorted(F),"fixed_sha256":digest_words(F),"pool":pool,"pool_sha256":pool_hash(pool),"removed":sorted(removed),"condition":mode,"starting_fixed_count":len(current),"fixed_count":len(F),"pool_count":len(pool),"solver_workers":2,"proof_artifact":None}
  if len(pool)>8000:
   trial.update(status="POOL_MEMORY_GATE",conclusion="No search; not infeasibility");history.append(trial);open_trials+=1;batch=1;save();continue
  model=cp_model.CpModel();xs={w:model.new_bool_var("w"+str(w)) for w in pool};at={}
  for w,x in xs.items():
   for d in inc.desc[w]:at.setdefault(d,[]).append(x)
  for group in at.values():
   if len(group)>1:model.add_at_most_one(group)
  total=sum(xs.values())+len(F);model.add(total>=225);model.maximize(sum(xs.values()));trial["known_code_exclusions"]=add_known_goal_exclusions(model,xs,F,known);trial["prior_closed_set_ids"]=attach_closed(model,xs,F,certs)
  for w,x in xs.items():model.add_hint(x,int(w in C))
  assert not model.validate() and set(C)-F<=set(pool)
  trial["model_sha256"]=hashlib.sha256(model.proto.SerializeToString(deterministic=True)).hexdigest()
  if trial_id<2:(out/("trial_"+str(trial_id)+".pbtxt")).write_text(str(model.proto))
  candidates=[]
  class Export(cp_model.CpSolverSolutionCallback):
   def on_solution_callback(self):
    Q=sorted(F|{w for w,x in xs.items() if self.value(x)});q=out/("trial_"+str(trial_id)+"_candidate_"+str(len(candidates))+".txt");q.write_text(canonical(Q));v=verify(q);assert v["cardinality"]>=225
    if len(Q)==226:assert tuple(Q) not in known
    candidates.append({"words":Q,"witness":q.name,"verification":v,"solver_seconds":self.wall_time})
    if len(Q)>=226:self.stop_search()
  solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=max(.1,min(20,600-(time.monotonic()-start)));solver.parameters.num_search_workers=2;solver.parameters.random_seed=1451001+case//2+trial_id
  before=resource.getrusage(resource.RUSAGE_SELF);t=time.monotonic();status=solver.solve(model,Export());after=resource.getrusage(resource.RUSAGE_SELF);trial.update(status=solver.status_name(status),solver_wall_seconds=time.monotonic()-t,process_cpu_seconds=(after.ru_utime+after.ru_stime)-(before.ru_utime+before.ru_stime),objective_bound_added=solver.best_objective_bound,solutions=[{k:v for k,v in r.items() if k!="words"} for r in candidates],branches=solver.num_branches,conflicts=solver.num_conflicts)
  if status==cp_model.INFEASIBLE:raise RuntimeError("Contradiction: independently verified225 hint must remain feasible under conditional exclusions")
  good=[r for r in candidates if r["verification"]["cardinality"]>=226]
  if good:
   novel=good[-1];best=novel["verification"]["cardinality"];trial["conclusion"]="New independently verified construction"
  elif status==cp_model.OPTIMAL:
   assert candidates and max(r["verification"]["cardinality"] for r in candidates)==225;current=F;C=candidates[-1]["words"];certs=[cert for cert in certs if not current<=set(cert["fixed"])];certs.append({"id":trial["id"],"fixed":sorted(current),"model_sha256":trial["model_sha256"],"pool_sha256":trial["pool_sha256"]});trial["conclusion"]="Encoded family optimum225; relax next neighborhood"
   fast=fast+1 if trial["solver_wall_seconds"]<5 else 0
   if mode=="minimum_growth" and fast>=3:batch=min(4,batch*2);fast=0
  else:
   open_trials+=1;fast=0;batch=max(1,batch//2);trial["conclusion"]="No new code within budget; restore last closed fixed set and change relaxation"
  history.append(trial);(out/("trial_"+str(trial_id)+".json")).write_text(json.dumps(trial,indent=2));save();print("ADAPTIVE_HULL_TRIAL",json.dumps({k:trial.get(k) for k in ["id","fixed_count","pool_count","status","conclusion","solver_wall_seconds"]}),flush=True);gc.collect()
 steps=[]
 if novel is not None:
  A=novel["words"]
  for k,seconds in [(6,5),(7,20),(8,60),(9,120),(10,180)]:
   if len(A)>=227:break
   r=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),str(seconds),"1000000000000","0"],input=canonical(A),text=True,capture_output=True,check=True,timeout=seconds+100,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0")).stdout);r["incumbent_sha256"]=digest_words(A);r["pool_sha256"]=pool_hash(r.pop("candidate_pool"));r.pop("neighbors")
   if r["found"]:
    A=sorted(set(A)-set(r["removed"])|set(r["added"]));q=out/("augmented_"+str(k)+".txt");q.write_text(canonical(A));r["verification"]=verify(q);best=max(best,len(A))
   steps.append(r)
 cpu1=resource.getrusage(resource.RUSAGE_SELF);child1=resource.getrusage(resource.RUSAGE_CHILDREN)
 report={"new_trials":len(history)-carried_trials,"new_completed225_families":sum(r.get("status")=="OPTIMAL" for r in history)-carried_closed,"new_open_or_gated_trials":open_trials-carried_open,"bootstrap_wall_seconds":bootstrap_wall,"job_wall_seconds":time.monotonic()-job_start,"self_cpu_seconds":cpu1.ru_utime+cpu1.ru_stime-job_cpu0.ru_utime-job_cpu0.ru_stime,"children_cpu_seconds":child1.ru_utime+child1.ru_stime-job_children0.ru_utime-job_children0.ru_stime,"migration":plan["migrations"][case],"source_sha":os.environ["GITHUB_SHA"],"engine_sha256":ENGINE,"case":case,"mode":mode,"initial_fixed_count":len(parent["fixed"]),"final_closed_fixed_count":len(current),"trials":len(history),"completed225_families":sum(r.get("status")=="OPTIMAL" for r in history),"open_or_gated_trials":open_trials,"wall_seconds":time.monotonic()-start,"best_in_family_verified":best,"retained_global_best_verified":max(226,best),"novel226":{k:v for k,v in novel.items() if k!="words"} if novel else None,"polish":steps,"scope":"Only explicit nested fixed-code families. Prior completed OPTIMAL225 goal-model exclusions are carried only when total>=226, by induction. Exact known226 no-goods apply only at exact size226. Unknown/feasible timeouts do not close or rule out the child neighborhood. No global or formal absence proof; cardinality remains primary."}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("ADAPTIVE_HULL",json.dumps(report),flush=True)
 if best>=227:print("VERIFIED_227",flush=True)
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--prepare",action="store_true");ap.add_argument("--case",type=int);ap.add_argument("--resume",action="store_true");a=ap.parse_args();prepare() if a.prepare else run(a.case,a.resume)
