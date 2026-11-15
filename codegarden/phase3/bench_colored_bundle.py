"""Same fixed seeds/ordered pools; record completion, not timeout-as-proof."""
import hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,pool_hash
from supervisor import check_integrity,verify
check_integrity();out=ROOT/"artifacts/phase3/colored_benchmark_001";out.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_KNOWN_GOAL_CODES="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0",CODEGARDEN_ROOT_BEGIN="0",CODEGARDEN_ROOT_END="2147483647")
def run(stem,C,n,k,seconds,extra=None):
 return json.loads(subprocess.run([str(ROOT/".build"/stem),str(n),str(k),str(seconds),"1000000000000","0"],input=canonical(C,n),text=True,capture_output=True,check=True,timeout=seconds+40,env={**env,**(extra or {})}).stdout)
# Independent root-interval/shard coverage on an actual small deletion instance.
small=[0,15];a=run("bundle_novel",small,4,2,5);assert a["complete"] and not a["found"];P=a["candidate_pool"];cover=list(range(2));checks=[]
prefix=run("bundle_colored",small,4,2,5,{"CODEGARDEN_ROOT_END":"2"});assert prefix["complete"] and prefix["candidate_pool"]==P and prefix["completed_roots"]==2
for shard in range(3):
 r=run("bundle_colored",small,4,2,5,{"CODEGARDEN_ROOT_BEGIN":"2","CODEGARDEN_ROOT_SHARDS":"3","CODEGARDEN_ROOT_SHARD":str(shard)});wanted=[i for i in range(2,len(P)) if i%3==shard];assert r["complete"] and not r["found"] and r["candidate_pool"]==P and r["completed_roots"]==len(wanted);cover+=wanted;checks.append({"shard":shard,"completed_roots":r["completed_roots"],"expected_roots":wanted})
assert sorted(cover)==list(range(len(P))) and len(cover)==len(set(cover))
rows=[];plan=json.loads((ROOT/"phase3/fresh225_plan.json").read_text());contradictions=[]
for case in [0,3]:
 C=plan["cases"][case]["words"];path=out/("seed_"+str(case)+".txt");path.write_text(canonical(C));assert verify(path)["cardinality"]==225;reports={}
 for stem in ["bundle_novel","bundle_colored"]:
  begin=time.monotonic();r=run(stem,C,16,7,30);r["process_wall_seconds"]=time.monotonic()-begin
  (out/("case"+str(case)+"_"+stem+".json")).write_text(json.dumps(r,indent=2));reports[stem]=r
  if r["found"]:
   Q=sorted(set(C)-set(r["removed"])|set(r["added"]));q=out/("candidate_"+str(case)+"_"+stem+".txt");q.write_text(canonical(Q));v=verify(q);r["verification"]=v;contradictions.append({"case":case,"kernel":stem,"verification":v});print("VERIFIED_227" if len(Q)>=227 else "VERIFIED_NEW226",q,flush=True)
 a=reports["bundle_novel"];b=reports["bundle_colored"];assert a["candidate_pool"]==b["candidate_pool"]
 rows.append({"case":case,"same_ordered_pool":True,"pool_sha256":pool_hash(a["candidate_pool"]),"old_complete":a["complete"],"new_complete":b["complete"],"old_found":a["found"],"new_found":b["found"],"old_cpu":a["cpu_seconds"],"new_cpu":b["cpu_seconds"],"cpu_speed_ratio":a["cpu_seconds"]/b["cpu_seconds"] if a["complete"] and b["complete"] and not a["found"] and not b["found"] else None})
report={"source_sha":os.environ["GITHUB_SHA"],"root_partition_tests":{"actual_n4_instance":small,"pool":P,"old_complete":True,"prefix_roots":2,"tail_shards":checks,"no_gaps_or_duplicate_roots":True},"rows":rows,"verified_completion_contradictions":contradictions,"scope":"Two same-input known-closed K7fixtures with30nativeCPU caps per kernel; runtime ratio only when both complete. Changing inner closure traversal preserves candidate universe/root order. Native exhaustive algorithm tests and independent positives, not formal global absence proof."}
(out/"report.json").write_text(json.dumps(report,indent=2));print("COLORED_BENCHMARK",json.dumps(report),flush=True)
