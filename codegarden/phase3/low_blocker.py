"""Bounded whole-corridor repairs; scope and exhaustion stay model-specific."""
import hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
check_integrity();case=int(sys.argv[1]);OUT=ROOT/"artifacts/phase3/low_blocker_001";out=OUT/"workers"/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((OUT/"plan.json").read_text());row=plan["cases"][case];assert plan["source_sha"]==os.environ["GITHUB_SHA"];known=(OUT/"known226.txt").read_text().splitlines();queries=row["models"];text=str(len(queries))+" "+str(len(known))+"\n"+"\n".join(known)+"\n"
for q in queries:text+=" ".join(map(str,[q["query"],60,len(q["fixed"]),len(q["pool"])]))+"\n"+" ".join(map(str,q["fixed"]))+"\n"+" ".join(map(str,q["pool"]))+"\n"
(out/"queries.txt").write_text(text);t=time.monotonic();native=subprocess.run([str(ROOT/".build/low_blocker_goal")],input=text,text=True,capture_output=True,check=True,timeout=300);(out/"native.jsonl").write_text(native.stdout);results=[json.loads(l) for l in native.stdout.splitlines()];assert len(results)<=3;positive=None;best=len(row["starting_words"]);follow=[]
for i,r in enumerate(results):
 q=queries[i];assert r["query"]==q["query"];r.update(blocker_threshold=q["blocker_threshold"],fixed_sha256=q["fixed_sha256"],pool_sha256=q["pool_sha256"],ordered_pool_sha256=q["ordered_pool_sha256"],proof_artifact=None)
 r["next_decision"]="widen_after_exact_goal_model_closure" if r["complete"] else "widen_after_bounded_stagnation_open_model" if r["limited"] else "verify_positive_then_strict_polish"
 if r["found"]:
  C=sorted(set(q["fixed"])|set(r["added"]));p=out/"candidate.txt";p.write_text(canonical(C));v=verify(p);assert v["cardinality"]>=226 and not any(tuple(C)==tuple(map(int,l.split()[1:])) for l in known);best=max(best,len(C));positive={"path":p.name,"verification":v,"query":q["query"]};print("VERIFIED_227" if len(C)>=227 else "VERIFIED_NEW226",case,q["query"],p,flush=True)
  if len(C)==226:
   for k,sec in [(6,10),(8,45),(10,90),(12,150)]:
    env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0",CODEGARDEN_ROOT_BEGIN="0",CODEGARDEN_ROOT_END="65536",CODEGARDEN_KNOWN_GOAL_CODES="")
    z=json.loads(subprocess.run([str(ROOT/".build/bundle_colored"),"16",str(k),str(sec),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=sec+90,env=env).stdout);P=z.pop("candidate_pool");z.pop("neighbors");z["pool_sha256"]=pool_hash(P);z["starting_sha256"]=digest_words(C);(out/("strict_pool_"+str(k)+".txt")).write_text("\n".join(map(str,P))+"\n")
    if z["found"]:
     C=sorted(set(C)-set(z["removed"])|set(z["added"]));p=out/("strict_"+str(k)+".txt");p.write_text(canonical(C));z["verification"]=verify(p);assert z["verification"]["cardinality"]>=227;z["path"]=p.name;best=max(best,len(C));print("VERIFIED_227",case,p,flush=True)
    follow.append(z)
    if len(C)>=227:break
  assert i==len(results)-1
report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"starting_sha256":row["starting_sha256"],"plan_sha256":hashlib.sha256((OUT/"plan.json").read_bytes()).hexdigest(),"results":results,"unattempted_queries":[q["query"] for q in queries[len(results):]],"positive":positive,"strict_followups":follow,"best_method_independently_verified":best,"retained_global_best_verified":max(226,best),"wall_seconds":time.monotonic()-t,"scope":plan["scope"]}
(out/"report.json").write_text(json.dumps(report,indent=2));print("LOW_BLOCKER_RESULT",json.dumps({"case":case,"statuses":[{"b":r["blocker_threshold"],"complete":r["complete"],"limited":r["limited"],"found":r["found"]} for r in results],"positive":positive is not None,"best":best}),flush=True)
