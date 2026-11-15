"""Matched sparse edge-penalty versus uniform pair-conflict search."""
import gzip,hashlib,json,os,pathlib,subprocess,sys,time,resource
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical,digest_words,pool_hash
t0=time.monotonic();ru0=resource.getrusage(resource.RUSAGE_SELF);child0=resource.getrusage(resource.RUSAGE_CHILDREN);check_integrity();case=int(sys.argv[1]);out=ROOT/"artifacts/phase3/neutral_hybrid_001"/str(case);out.mkdir(parents=True,exist_ok=True)
pr=json.loads((ROOT/"artifacts/phase3/neutral_hybrid_001/prerequisites.json").read_text());assert pr["passed"] and len(pr["receipts"])==24
tests=json.loads((ROOT/"artifacts/phase3/neutral_hybrid_001/literal_weight_tests.json").read_text());assert tests["passed"] and tests["kernel_sha256"]==hashlib.sha256((ROOT/"phase3/neutral_hybrid.cpp").read_bytes()).hexdigest()
plan=json.loads((ROOT/"phase3/weighted_plan.json").read_text());C=plan["cases"][case]["words"];start=out/"starting.txt";start.write_text(canonical(C));starting=verify(start);assert starting["cardinality"]==225
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(C) for C in info["codes"]));rev=lambda w:int(format(w,"016b")[::-1],2);images=[sorted(core),sorted(65535^w for w in core),sorted(rev(w) for w in core),sorted(65535^rev(w) for w in core)]
cp=out/"cores.txt";cp.write_text("".join("216 "+" ".join(map(str,F))+"\n" for F in images))
known={tuple(sorted(T(C))) for C in info["codes"] for T in [lambda c:c,lambda c:[65535^w for w in c],lambda c:[rev(w) for w in c],lambda c:[65535^rev(w) for w in c]]};kp=out/"known226.txt";kp.write_text("".join("226 "+" ".join(map(str,F))+"\n" for F in sorted(known)))
mode="neutral_clean_swaps";seed=1501001+case
r=json.loads(subprocess.run([str(ROOT/".build/neutral_hybrid"),"600",str(seed),"uniform",str(out/"checkpoint_raw_invalid_unless_zero.txt"),str(cp),"210",str(kp),"fixed_release32","optional","0.2"],input=canonical(C),text=True,capture_output=True,check=True,timeout=900).stdout)
assert r["pivot_is_forced"] is False
bank=[]
for i,Q in enumerate(r["projection225_unverified"]):
 p=out/("projection225_"+str(i)+".txt");p.write_text(canonical(Q));v=verify(p);assert v["cardinality"]==225;bank.append({"path":p.name,"sha256":digest_words(Q),"verification":v})
assert r["neutral_rate"]==0.2 and r["neutral_moves"]<=r["neutral_attempts"]
(out/"native.json").write_text(json.dumps(r,indent=2));best=225;solutions=[]
candidates=r["novel226_candidates"][:]
if r["exact_repair227"]:candidates.append(r["exact_repair227"])
if r["minimum_pair_conflicts"]==0:candidates.append(r["best"])
for i,Q in enumerate(candidates):
 p=out/("candidate_"+str(i)+".txt");p.write_text(canonical(Q));v=verify(p);assert v["cardinality"]>=226
 if len(Q)==226:assert tuple(sorted(Q)) not in known
 best=max(best,len(Q));solutions.append({"witness":p.name,"verification":v,"core_counts":[len(set(Q)&set(F)) for F in images]})
 if len(Q)>=227:print("VERIFIED_227",p,flush=True)
repairs=out/"checkpoint_raw_invalid_unless_zero.txt.repairs.jsonl";annotated=out/"repair_trials.jsonl";count=0;release_hist={};forced_pivots=0;root_only=0;pool_below_target=0;pool_stats=[]
with annotated.open("w") as dest:
 if repairs.exists():
  for line in repairs.read_text().splitlines():
   row=json.loads(line);assert row["pivot_is_forced"] is False;assert len(row["candidate_pool"])>=row["target_added"];root_only+=row["nodes"]==1;pool_below_target+=len(row["candidate_pool"])<row["target_added"];pool_stats.append(len(row["candidate_pool"]));release_hist[str(row["release_budget"])]=release_hist.get(str(row["release_budget"]),0)+1;forced_pivots+=row["forced_pivot"]>=0;row["fixed_sha256"]=digest_words(row["fixed"]);row["candidate_pool_sha256"]=pool_hash(sorted(row["candidate_pool"]));row["search_order_sha256"]=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in row["candidate_pool"])).hexdigest();row["search_order_encoding"]="uint32_be_in_recorded_order";row["source_sha"]=os.environ["GITHUB_SHA"];row["proof_artifact"]=None
   dest.write(json.dumps(row,separators=(",",":"))+"\n");count+=1
assert count==r["repair_trials"]
compressed_logs=[]
for path in [repairs,annotated]:
 if path.exists():
  raw=path.read_bytes();z=gzip.compress(raw,mtime=0);dest=path.with_name(path.name+".gz");dest.write_bytes(z);compressed_logs.append({"path":dest.name,"raw_sha256":hashlib.sha256(raw).hexdigest(),"gzip_sha256":hashlib.sha256(z).hexdigest(),"raw_bytes":len(raw),"gzip_bytes":len(z)})
ru1=resource.getrusage(resource.RUSAGE_SELF);child1=resource.getrusage(resource.RUSAGE_CHILDREN)
report={"pivot_is_forced":False,"pool_below_target":pool_below_target,"root_only_queries":root_only,"candidate_pool_min":min(pool_stats) if pool_stats else None,"candidate_pool_max":max(pool_stats) if pool_stats else None,"candidate_pool_mean":sum(pool_stats)/len(pool_stats) if pool_stats else None,"neutral_rate":r["neutral_rate"],"neutral_attempts":r["neutral_attempts"],"neutral_moves":r["neutral_moves"],"projection225_bank":bank,"comparison_control":{"source":"c5fa351f79f7f73e11aef7d4df91b4e68c42c264","run":43731873426,"case":2*case,"same_seed_start_budget_policy":True,"historical_not_simultaneous_control":True},"compressed_logs":compressed_logs,"wall_including_controller":time.monotonic()-t0,"controller_self_cpu_seconds":ru1.ru_utime+ru1.ru_stime-ru0.ru_utime-ru0.ru_stime,"all_children_cpu_seconds":child1.ru_utime+child1.ru_stime-child0.ru_utime-child0.ru_stime,"release_histogram":release_hist,"forced_pivot_trials":forced_pivots,"repair_trials":r["repair_trials"],"repair_complete_no227":r["repair_complete"],"repair_timeouts":r["repair_timeouts"],"repair_pool_gates":r["repair_pool_gates"],"repair_cpu_seconds":r["repair_cpu_seconds"],"repair_logs_sha256":hashlib.sha256(annotated.read_bytes()).hexdigest(),"source_sha":os.environ["GITHUB_SHA"],"case":case,"pair":case,"mode":mode,"seed":seed,"starting_verification":starting,"starting_sha256":digest_words(C),"plan_sha256":hashlib.sha256((ROOT/"phase3/weighted_plan.json").read_bytes()).hexdigest(),"target":227,"quota":210,"minimum_pair_conflicts":r["minimum_pair_conflicts"],"cpu_seconds":r["cpu_seconds"],"iterations":r["iterations"],"edge_weight_updates":r["edge_weight_updates"],"best_method_independently_verified":best,"retained_global_best_verified":max(226,best),"novel":solutions,"scope":"Eight600-native-CPU neutral-clean-swap runs, uniform pair costs, conditional corequota210, optional-pivot fixed32 repair. At most20percent iterations attempt a unique-blocker clean swap preserving pair energy exactly; reverse taboo50. Historical controls are corresponding even-numbered optional-hybrid runs, same parents/seeds/budgets, not simultaneous or independent fresh seeds. Exact repair remains bounded by300CPU total,2048candidate gate and250ms soft queries. Projections225are independently verified support artifacts; no structural novelty or227claim without separate checks. Timeouts/gates remain open. Positive pair energy is invalid."}
(out/"report.json").write_text(json.dumps(report,indent=2));print("WEIGHTED_BREAKOUT",json.dumps({k:report[k] for k in ["case","mode","minimum_pair_conflicts","cpu_seconds","iterations","edge_weight_updates","repair_trials","repair_complete_no227","repair_timeouts","repair_cpu_seconds","best_method_independently_verified","retained_global_best_verified"]}|{"novel":len(solutions)}),flush=True)
