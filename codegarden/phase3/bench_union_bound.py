"""Same-input finite-fixture regression and performance comparison for safe matching pruning."""
import hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical,pool_hash
check_integrity();OUT=ROOT/"artifacts/phase3/union_bound_benchmark_001";OUT.mkdir(parents=True,exist_ok=True)
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known=set()
def rev(w):return int(format(w,"016b")[::-1],2)
for C in info["codes"]:
 for c in [0,65535]:
  for r in [False,True]:known.add(tuple(sorted((rev(w) if r else w)^c for w in C)))
kp=OUT/"known.txt";kp.write_text("".join("226 "+" ".join(map(str,C))+"\n" for C in sorted(known)))
plan=json.loads((ROOT/"phase3/union_external_plan.json").read_text());rows=[]
for case in [0,7]:
 p=plan["cases"][case];A=p["a"]["words"];B=p["b"]["words"]
 for label,C in [("a",A),("b",B)]:
  path=OUT/("case"+str(case)+"_"+label+".txt");path.write_text(canonical(C));assert verify(path)["cardinality"]==225
 data=canonical(A)+canonical(B);results={}
 for name in ["old","bounded"]:
  if name=="old":args=[str(ROOT/".build/union_external2"),"30",str(kp),"5","5"]
  else:
   pool=results["old"]["levels"][0]["search_order"];path=OUT/("expected_"+str(case)+".txt");path.write_text(str(len(pool))+" "+" ".join(map(str,pool)));args=[str(ROOT/".build/union_external3"),"30",str(kp),"5","5","0",str(path)]
  t=time.monotonic();r=json.loads(subprocess.run(args,input=data,text=True,capture_output=True,check=True,timeout=60).stdout);r["process_wall_seconds"]=time.monotonic()-t;results[name]=r;(OUT/("case"+str(case)+"_"+name+".json")).write_text(json.dumps(r,indent=2))
 old=results["old"];new=results["bounded"];assert not old["found227_unverified"] and not new["found227_unverified"]
 assert old["levels"][0]["candidate_pool"]==new["levels"][0]["candidate_pool"] and old["levels"][0]["search_order"]==new["levels"][0]["search_order"]
 complete=old["levels"][0]["complete"] and new["levels"][0]["complete"]
 rows.append({"case":case,"both_complete":complete,"same_candidate_pool":True,"candidate_pool_sha256":pool_hash(old["levels"][0]["candidate_pool"]),"old_cpu":old["cpu_seconds"],"bounded_cpu":new["cpu_seconds"],"old_wall":old["process_wall_seconds"],"bounded_wall":new["process_wall_seconds"],"old_matching_calls":old["matching_calls"],"bounded_matching_calls":new["matching_calls"],"cheap_bound_prunes":new["cheap_matching_bound_prunes"],"cpu_speed_ratio_if_both_complete":old["cpu_seconds"]/max(.000001,new["cpu_seconds"]) if complete else None})
report={"source_sha":os.environ["GITHUB_SHA"],"kernels":{name:hashlib.sha256((ROOT/"phase3"/name).read_bytes()).hexdigest() for name in ["union_external2.cpp","union_external3.cpp"]},"rows":rows,"scope":"Two known-closed finite fixtures, same target227, same pool/order,30nativeCPU caps. Ratios apply only when both encoded searches finish. Bootstrap is included in process wall, not in the native timer. No primary cardinality gain or adaptive-policy generalization is claimed."}
(OUT/"report.json").write_text(json.dumps(report,indent=2));print("UNION_BOUND_BENCHMARK",json.dumps(rows),flush=True)
