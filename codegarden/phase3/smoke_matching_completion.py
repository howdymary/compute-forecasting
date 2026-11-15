"""Full CLI/protocol and independent positive verification before300CPU workers."""
import json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical
from supervisor import check_integrity,verify
check_integrity();out=ROOT/"artifacts/phase3/matching_completion_001";out.mkdir(parents=True,exist_ok=True)
t=json.loads(subprocess.run([str(ROOT/".build/matching_completion"),"--test"],text=True,capture_output=True,check=True).stdout);assert t["passed"];(out/"matching_tests.json").write_text(json.dumps(t,indent=2))
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(C) for C in info["codes"]));rev=lambda w:int(format(w,"016b")[::-1],2);images=[sorted(core),sorted(65535^w for w in core),sorted(rev(w) for w in core),sorted(65535^rev(w) for w in core)]
cp=out/"smoke_cores.txt";cp.write_text("".join("216 "+" ".join(map(str,C))+"\n" for C in images));kp=out/"smoke_known.txt";kp.write_text("");p=json.loads((ROOT/"phase3/union_external_plan.json").read_text())["cases"][0];A=p["a"]["words"];B=p["b"]["words"];rows=[]
for adaptive in [0,1]:
 r=json.loads(subprocess.run([str(ROOT/".build/matching_completion"),"1","1517001",str(adaptive),str(out/("smoke_"+str(adaptive)+".txt")),str(kp),str(cp)],input=canonical(A)+canonical(B),text=True,capture_output=True,check=True,timeout=60).stdout)
 for i,C in enumerate([r["best"]]+r["novel226_candidates"]+r["bank225_unverified"]):
  path=out/("smoke_candidate_"+str(adaptive)+"_"+str(i)+".txt");path.write_text(canonical(C));v=verify(path);assert v["cardinality"]>=225
  if len(C)>=227:print("VERIFIED_227_SMOKE",path,flush=True)
 assert r["best_size_unverified"]>=225 and r["cycles"]>0 and r["sample_occurrences"]>0
 rows.append({k:r[k] for k in ["adaptive","best_size_unverified","cycles","matching_calls","search_cpu_seconds"]})
(out/"smoke.json").write_text(json.dumps({"passed":True,"matching_tests":t,"rows":rows},indent=2));print("MATCHING_COMPLETION_SMOKE",json.dumps(rows),flush=True)
