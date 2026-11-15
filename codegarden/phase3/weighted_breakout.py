"""Matched sparse edge-penalty versus uniform pair-conflict search."""
import hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical,digest_words,pool_hash
check_integrity();case=int(sys.argv[1]);out=ROOT/"artifacts/phase3/weighted_breakout_001"/str(case);out.mkdir(parents=True,exist_ok=True)
pr=json.loads((ROOT/"artifacts/phase3/weighted_breakout_001/prerequisites.json").read_text());assert pr["passed"] and len(pr["receipts"])==24
tests=json.loads((ROOT/"artifacts/phase3/weighted_breakout_001/literal_weight_tests.json").read_text());assert tests["passed"] and tests["kernel_sha256"]==hashlib.sha256((ROOT/"phase3/weighted_breakout.cpp").read_bytes()).hexdigest()
plan=json.loads((ROOT/"phase3/weighted_plan.json").read_text());C=plan["cases"][case//2]["words"];start=out/"starting.txt";start.write_text(canonical(C));starting=verify(start);assert starting["cardinality"]==225
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(C) for C in info["codes"]));rev=lambda w:int(format(w,"016b")[::-1],2);images=[sorted(core),sorted(65535^w for w in core),sorted(rev(w) for w in core),sorted(65535^rev(w) for w in core)]
cp=out/"cores.txt";cp.write_text("".join("216 "+" ".join(map(str,F))+"\n" for F in images))
known={tuple(sorted(T(C))) for C in info["codes"] for T in [lambda c:c,lambda c:[65535^w for w in c],lambda c:[rev(w) for w in c],lambda c:[65535^rev(w) for w in c]]};kp=out/"known226.txt";kp.write_text("".join("226 "+" ".join(map(str,F))+"\n" for F in sorted(known)))
mode="uniform" if case%2==0 else "weighted";seed=1501001+case//2
r=json.loads(subprocess.run([str(ROOT/".build/weighted_breakout"),"600",str(seed),mode,str(out/"checkpoint_raw_invalid_unless_zero.txt"),str(cp),"210",str(kp)],input=canonical(C),text=True,capture_output=True,check=True,timeout=900).stdout)
(out/"native.json").write_text(json.dumps(r,indent=2));best=225;solutions=[]
candidates=r["novel226_candidates"][:]
if r["minimum_pair_conflicts"]==0:candidates.append(r["best"])
for i,Q in enumerate(candidates):
 p=out/("candidate_"+str(i)+".txt");p.write_text(canonical(Q));v=verify(p);assert v["cardinality"]>=226
 if len(Q)==226:assert tuple(sorted(Q)) not in known
 best=max(best,len(Q));solutions.append({"witness":p.name,"verification":v,"core_counts":[len(set(Q)&set(F)) for F in images]})
 if len(Q)>=227:print("VERIFIED_227",p,flush=True)
report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"pair":case//2,"mode":mode,"seed":seed,"starting_verification":starting,"starting_sha256":digest_words(C),"plan_sha256":hashlib.sha256((ROOT/"phase3/weighted_plan.json").read_bytes()).hexdigest(),"target":227,"quota":210,"minimum_pair_conflicts":r["minimum_pair_conflicts"],"cpu_seconds":r["cpu_seconds"],"iterations":r["iterations"],"edge_weight_updates":r["edge_weight_updates"],"best_method_independently_verified":best,"retained_global_best_verified":max(226,best),"novel":solutions,"scope":"Eight matched pairs with equal600nativeCPU deadlines and the same conditional core quota. Dynamic sparse edge penalties and forgetting versus uniform pair costs; strongest-removal strategy shared. Positive-energy227 states remain invalid. No absence proof or trained-policy claim. Positive candidates pass both protected verifiers; any later polishing is a separate experiment."}
(out/"report.json").write_text(json.dumps(report,indent=2));print("WEIGHTED_BREAKOUT",json.dumps({k:report[k] for k in ["case","mode","minimum_pair_conflicts","cpu_seconds","iterations","edge_weight_updates","best_method_independently_verified","retained_global_best_verified"]}|{"novel":len(solutions)}),flush=True)
