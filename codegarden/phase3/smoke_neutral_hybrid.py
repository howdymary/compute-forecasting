"""Exercise full CLI, serialization, repair counters and protected positive acceptance before long runs."""
import json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical
from supervisor import check_integrity,verify
check_integrity();out=ROOT/"artifacts/phase3/neutral_hybrid_001";out.mkdir(parents=True,exist_ok=True)
native=json.loads(subprocess.run([str(ROOT/".build/neutral_hybrid"),"--repair-test"],text=True,capture_output=True,check=True).stdout);assert native["passed"];(out/"repair_graph_tests.json").write_text(json.dumps(native,indent=2))
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(C) for C in info["codes"]));rev=lambda w:int(format(w,"016b")[::-1],2);images=[sorted(core),sorted(65535^w for w in core),sorted(rev(w) for w in core),sorted(65535^rev(w) for w in core)]
cp=out/"smoke_cores.txt";cp.write_text("".join("216 "+" ".join(map(str,C))+"\n" for C in images));kp=out/"smoke_known.txt";kp.write_text("")
C=json.loads((ROOT/"phase3/weighted_plan.json").read_text())["cases"][0]["words"];rows=[]
for mode in ["fixed_release32","adaptive_large"]:
 r=json.loads(subprocess.run([str(ROOT/".build/neutral_hybrid"),"1","1501001","uniform",str(out/("smoke_"+mode+"_raw_invalid_unless_zero.txt")),str(cp),"210",str(kp),mode,"optional","0.2"],input=canonical(C),text=True,capture_output=True,check=True,timeout=60).stdout);assert r["target"]==227 and r["repair_trials"]>=0 and r["repair_policy"]==mode;assert r["cpu_seconds"]>=1 or r["minimum_pair_conflicts"]==0 or bool(r["exact_repair227"])
 assert r["pivot_is_forced"] is False and r["neutral_rate"]==0.2 and r["neutral_attempts"]>0 and r["neutral_moves"]>0
 for i,Q in enumerate(r["projection225_unverified"]):
  p=out/("smoke_bank_"+mode+"_"+str(i)+".txt");p.write_text(canonical(Q));assert verify(p)["cardinality"]==225
 repairpath=out/("smoke_"+mode+"_raw_invalid_unless_zero.txt.repairs.jsonl")
 for line in repairpath.read_text().splitlines():
  row=json.loads(line);assert not row["pivot_is_forced"] and len(row["candidate_pool"])>=row["target_added"]
 positives=r["novel226_candidates"][:]
 if r["minimum_pair_conflicts"]==0:positives.append(r["best"])
 if r["exact_repair227"]:positives.append(r["exact_repair227"])
 for i,Q in enumerate(positives):
  p=out/("smoke_candidate_"+mode+"_"+str(i)+".txt");p.write_text(canonical(Q));v=verify(p)
  print("VERIFIED_CANDIDATE_SMOKE",len(Q),p,flush=True)
  if len(Q)>=227:print("VERIFIED_227_SMOKE",p,flush=True)
 rows.append({k:r[k] for k in ["seed","weighted","repair_policy","cpu_seconds","iterations","minimum_pair_conflicts","repair_trials","repair_complete","repair_timeouts","repair_cpu_seconds"]})
(out/"smoke.json").write_text(json.dumps({"passed":True,"rows":rows,"graph_tests":native},indent=2));print("HYBRID_SMOKE_PASSED",json.dumps(rows),flush=True)
