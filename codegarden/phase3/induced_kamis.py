"""Memory-profiled heuristic search with durable validated checkpoints after each round."""
import hashlib,json,os,pathlib,resource,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import check_integrity,verify
check_integrity();case=int(sys.argv[1]);OUT=ROOT/"artifacts/phase3/induced_kamis_001";out=OUT/"workers"/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((OUT/"plan.json").read_text());row=plan["cases"][case];assert plan["source_sha"]==os.environ["GITHUB_SHA"];b=row["blocker_union"];poolpath=OUT/("pool_"+str(b)+".txt");P=list(map(int,poolpath.read_text().split()));assert pool_hash(P)==next(p for p in plan["pools"] if p["blocker_union"]==b)["pool_sha256"]
graph=ROOT/(".build/induced_"+str(case)+".graph");t=time.monotonic();r=subprocess.run([str(ROOT/".build/induced_graph"),"16",str(poolpath),str(graph)],text=True,capture_output=True,timeout=180);profile=next((json.loads(l.split("GRAPH_PROFILE ",1)[1]) for l in r.stderr.splitlines() if "GRAPH_PROFILE " in l),{});report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"mode":row["mode"],"pool_sha256":pool_hash(P),"pool_count":len(P),"graph_profile":profile,"graph_build_seconds":time.monotonic()-t,"rounds":[],"scope":plan["scope"],"best_method_independently_verified":None,"retained_global_best_verified":226,"novel226":False,"strict_followups":[]}
def save():(out/"report.json").write_text(json.dumps(report,indent=2))
if r.returncode:
 report.update(status="MEMORY_GATE_OR_GRAPH_FAILURE",graph_returncode=r.returncode);save();print("INDUCED_KAMIS_GATED",case,json.dumps(profile),flush=True);sys.exit(0)
h=hashlib.sha256()
with graph.open("rb") as stream:
 while block:=stream.read(1<<20):h.update(block)
report["graph_sha256"]=h.hexdigest();known={tuple(map(int,l.split()[1:])) for l in (OUT/"known226.txt").read_text().splitlines()};warm=OUT/("seed_"+str(row["warm_parent"])+".txt") if row["warm_parent"] is not None else None
def limit():resource.setrlimit(resource.RLIMIT_AS,(6*1024**3,6*1024**3))
for roundid in range(2):
 selected=out/("selected_"+str(roundid)+".txt");log=out/("solver_"+str(roundid)+".txt");binary=ROOT/".build/kamis-upstream"/("redumis" if row["mode"]=="evolutionary_cold" else "codegarden_pool_warm");seed=row["seed"]+roundid*100;env=dict(os.environ,OMP_NUM_THREADS="1",CODEGARDEN_POOL_WORDS=str(poolpath))
 if warm is not None:env["CODEGARDEN_START_CODES"]=str(warm)
 command=[str(binary),str(graph),"--seed",str(seed),"--time_limit","300","--output",str(selected),"--console_log"];begin=time.monotonic()
 with log.open("w") as sink:
  try:r=subprocess.run(command,stdout=sink,stderr=subprocess.STDOUT,env=env,timeout=390,preexec_fn=limit);status="RETURNED";code=r.returncode
  except subprocess.TimeoutExpired:status="TIMEOUT";code=None
 item={"round":roundid,"seed":seed,"seconds_limit":300,"wall_seconds":time.monotonic()-begin,"status":status,"returncode":code,"log":log.name,"starting_sha256":hashlib.sha256(warm.read_bytes()).hexdigest() if warm else None};novel=False;C=None
 if code==0 and selected.exists():
  tokens=selected.read_text().split();assert len(tokens)==len(P) and set(tokens)<={"0","1"};C=sorted(P[i] for i,v in enumerate(tokens) if v=="1");path=out/("witness_"+str(roundid)+".txt");path.write_text(canonical(C));v=verify(path);item["path"]=path.name;item["verification"]=v;novel=len(C)==226 and tuple(C) not in known;item["novel_against152known226arrays"]=novel;report["novel226"]|=novel;report["best_method_independently_verified"]=max(report["best_method_independently_verified"] or 0,len(C));report["retained_global_best_verified"]=max(226,report["best_method_independently_verified"])
  if warm is not None:warm=path
  print("VERIFIED_227" if len(C)>=227 else "VERIFIED_NEW226" if novel else "INDUCED_KAMIS_CHECKPOINT",case,roundid,len(C),path,flush=True)
 report["rounds"].append(item);report["status"]="RUNNING";save()
 if code!=0 or C is None:
  report["status"]="PROCESS_FAILURE_OR_NO_OUTPUT_STOPPED";save();break
 if C is not None and len(C)>=227:break
 if novel:
  for k,sec in [(6,10),(8,45),(10,90),(12,150)]:
   ee=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0",CODEGARDEN_ROOT_BEGIN="0",CODEGARDEN_ROOT_END="65536",CODEGARDEN_KNOWN_GOAL_CODES="")
   z=json.loads(subprocess.run([str(ROOT/".build/bundle_colored"),"16",str(k),str(sec),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=sec+90,env=ee).stdout);Q=z.pop("candidate_pool");z.pop("neighbors");z["pool_sha256"]=pool_hash(Q);z["starting_sha256"]=digest_words(C);(out/("strict_pool_"+str(roundid)+"_"+str(k)+".txt")).write_text("\n".join(map(str,Q))+"\n")
   if z["found"]:
    C=sorted(set(C)-set(z["removed"])|set(z["added"]));path=out/("strict_"+str(roundid)+"_"+str(k)+".txt");path.write_text(canonical(C));z["verification"]=verify(path);assert z["verification"]["cardinality"]>=227;z["path"]=path.name;report["best_method_independently_verified"]=len(C);report["retained_global_best_verified"]=len(C);print("VERIFIED_227",case,path,flush=True)
   report["strict_followups"].append(z);save()
   if len(C)>=227:break
 if report["retained_global_best_verified"]>=227:break
if report["status"]=="RUNNING":report["status"]="COMPLETED_BOUNDED_ROUNDS"
save();print("INDUCED_KAMIS_RESULT",json.dumps({"case":case,"mode":row["mode"],"pool":len(P),"best":report["best_method_independently_verified"],"novel226":report["novel226"],"rounds":len(report["rounds"])}),flush=True)
