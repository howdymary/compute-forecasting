"""Matched sparse edge-penalty versus uniform pair-conflict search."""
import hashlib,json,os,pathlib,subprocess,sys,time,resource
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical,digest_words,pool_hash
t0=time.monotonic();ru0=resource.getrusage(resource.RUSAGE_SELF);child0=resource.getrusage(resource.RUSAGE_CHILDREN);check_integrity();case=int(sys.argv[1]);out=ROOT/"artifacts/phase3/opportunity_hybrid_001"/str(case);out.mkdir(parents=True,exist_ok=True)
pr=json.loads((ROOT/"artifacts/phase3/opportunity_hybrid_001/prerequisites.json").read_text());assert pr["passed"] and len(pr["receipts"])==24
tests=json.loads((ROOT/"artifacts/phase3/opportunity_hybrid_001/literal_weight_tests.json").read_text());assert tests["passed"] and tests["kernel_sha256"]==hashlib.sha256((ROOT/"phase3/opportunity_hybrid.cpp").read_bytes()).hexdigest()
plan=json.loads((ROOT/"phase3/weighted_plan.json").read_text());C=plan["cases"][case//2]["words"];start=out/"starting.txt";start.write_text(canonical(C));starting=verify(start);assert starting["cardinality"]==225
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(C) for C in info["codes"]));rev=lambda w:int(format(w,"016b")[::-1],2);images=[sorted(core),sorted(65535^w for w in core),sorted(rev(w) for w in core),sorted(65535^rev(w) for w in core)]
cp=out/"cores.txt";cp.write_text("".join("216 "+" ".join(map(str,F))+"\n" for F in images))
known={tuple(sorted(T(C))) for C in info["codes"] for T in [lambda c:c,lambda c:[65535^w for w in c],lambda c:[rev(w) for w in c],lambda c:[65535^rev(w) for w in c]]};kp=out/"known226.txt";kp.write_text("".join("226 "+" ".join(map(str,F))+"\n" for F in sorted(known)))
mode="fixed_release8" if case%2==0 else "adaptive_release";seed=1501001+case//2
r=json.loads(subprocess.run([str(ROOT/".build/opportunity_hybrid"),"600",str(seed),"uniform",str(out/"checkpoint_raw_invalid_unless_zero.txt"),str(cp),"210",str(kp),mode],input=canonical(C),text=True,capture_output=True,check=True,timeout=900).stdout)
(out/"native.json").write_text(json.dumps(r,indent=2));best=225;solutions=[]
candidates=r["novel226_candidates"][:]
if r["exact_repair227"]:candidates.append(r["exact_repair227"])
if r["minimum_pair_conflicts"]==0:candidates.append(r["best"])
for i,Q in enumerate(candidates):
 p=out/("candidate_"+str(i)+".txt");p.write_text(canonical(Q));v=verify(p);assert v["cardinality"]>=226
 if len(Q)==226:assert tuple(sorted(Q)) not in known
 best=max(best,len(Q));solutions.append({"witness":p.name,"verification":v,"core_counts":[len(set(Q)&set(F)) for F in images]})
 if len(Q)>=227:print("VERIFIED_227",p,flush=True)
repairs=out/"checkpoint_raw_invalid_unless_zero.txt.repairs.jsonl";annotated=out/"repair_trials.jsonl";count=0;release_hist={};forced_pivots=0
with annotated.open("w") as dest:
 if repairs.exists():
  for line in repairs.read_text().splitlines():
   row=json.loads(line);release_hist[str(row["release_budget"])]=release_hist.get(str(row["release_budget"]),0)+1;forced_pivots+=row["forced_pivot"]>=0;row["fixed_sha256"]=digest_words(row["fixed"]);row["candidate_pool_sha256"]=pool_hash(sorted(row["candidate_pool"]));row["search_order_sha256"]=pool_hash(row["candidate_pool"]);row["source_sha"]=os.environ["GITHUB_SHA"];row["proof_artifact"]=None
   dest.write(json.dumps(row,separators=(",",":"))+"\n");count+=1
assert count==r["repair_trials"]
ru1=resource.getrusage(resource.RUSAGE_SELF);child1=resource.getrusage(resource.RUSAGE_CHILDREN)
report={"wall_including_controller":time.monotonic()-t0,"controller_self_cpu_seconds":ru1.ru_utime+ru1.ru_stime-ru0.ru_utime-ru0.ru_stime,"all_children_cpu_seconds":child1.ru_utime+child1.ru_stime-child0.ru_utime-child0.ru_stime,"release_histogram":release_hist,"forced_pivot_trials":forced_pivots,"repair_trials":r["repair_trials"],"repair_complete_no227":r["repair_complete"],"repair_timeouts":r["repair_timeouts"],"repair_pool_gates":r["repair_pool_gates"],"repair_cpu_seconds":r["repair_cpu_seconds"],"repair_logs_sha256":hashlib.sha256(annotated.read_bytes()).hexdigest(),"source_sha":os.environ["GITHUB_SHA"],"case":case,"pair":case//2,"mode":mode,"seed":seed,"starting_verification":starting,"starting_sha256":digest_words(C),"plan_sha256":hashlib.sha256((ROOT/"phase3/weighted_plan.json").read_bytes()).hexdigest(),"target":227,"quota":210,"minimum_pair_conflicts":r["minimum_pair_conflicts"],"cpu_seconds":r["cpu_seconds"],"iterations":r["iterations"],"edge_weight_updates":r["edge_weight_updates"],"best_method_independently_verified":best,"retained_global_best_verified":max(226,best),"novel":solutions,"scope":"Eight matched pairs with equal600nativeCPU deadlines and the same conditional core quota. Uniform pair costs in both conditions; fixed release8 versus adaptive release2/4/8/16 following exact solver status and runtime. Force an opportunity pivot when sampled, releasing all its blockers and additional clean words. Separate repair RNG; at most5accepted trials per elapsed CPU second spreads the3000-trial budget across the run. Both use the same starts/seeds and600nativeCPU caps. Positive-energy227 states remain invalid. Each COMPLETE_NO227 receipt concerns only its explicitly fixed valid subset and full compatible pool. Pool gates/timeouts are open. Repair allowance60CPU, maximum3000trials, candidate pool gate256, per-query20ms soft cap inside the600CPU envelope. No global absence proof or trained-policy claim. Positive candidates pass both protected verifiers; any later polishing is a separate experiment."}
(out/"report.json").write_text(json.dumps(report,indent=2));print("WEIGHTED_BREAKOUT",json.dumps({k:report[k] for k in ["case","mode","minimum_pair_conflicts","cpu_seconds","iterations","edge_weight_updates","repair_trials","repair_complete_no227","repair_timeouts","repair_cpu_seconds","best_method_independently_verified","retained_global_best_verified"]}|{"novel":len(solutions)}),flush=True)
