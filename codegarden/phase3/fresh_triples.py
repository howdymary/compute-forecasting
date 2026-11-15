"""Bounded batch of explicit goal-filtered three-parent packing repairs."""
import hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import check_integrity,verify
check_integrity();case=int(sys.argv[1]);OUT=ROOT/"artifacts/phase3/fresh_triples_001";out=OUT/"workers"/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((OUT/"plan.json").read_text());assert plan["source_sha"]==os.environ["GITHUB_SHA"]
queries=[q for q in plan["queries"] if q["query"]%12==case];known=(OUT/"known226.txt").read_text().splitlines();text=str(len(queries))+" "+str(len(known))+"\n"+"\n".join(known)+"\n"
for q in queries:
 text+=" ".join(map(str,[q["query"],2,len(q["fixed"]),len(q["pool"])]))+"\n"+" ".join(map(str,q["fixed"]))+"\n"+" ".join(map(str,q["pool"]))+"\n"
(out/"queries.txt").write_text(text);t=time.monotonic();r=subprocess.run([str(ROOT/".build/triple_goal")],input=text,text=True,capture_output=True,check=True,timeout=240);(out/"native.jsonl").write_text(r.stdout);results=[json.loads(l) for l in r.stdout.splitlines()];assert len(results)<=len(queries);byid={q["query"]:q for q in queries};positive=None;best=225;polish=[]
for pos,row in enumerate(results):
 q=queries[pos];assert row["query"]==q["query"]
 row.update(fixed_sha256=q["fixed_sha256"],pool_sha256=q["pool_sha256"],ordered_pool_sha256=q["ordered_pool_sha256"],scope="This fixed code and full explicit triple-union repair pool only",proof_artifact=None)
 if row["found"]:
  C=sorted(set(q["fixed"])|set(row["added"]));path=out/"candidate.txt";path.write_text(canonical(C));v=verify(path);assert v["cardinality"]>=226 and not any(tuple(C)==tuple(map(int,l.split()[1:])) for l in known);positive={"query":q["query"],"path":path.name,"verification":v};best=len(C);print("VERIFIED_227" if best>=227 else "VERIFIED_NEW226",case,q["query"],path,flush=True)
  if best==226:
   for k,sec in [(6,10),(8,45),(10,90),(12,150)]:
    env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0",CODEGARDEN_KNOWN_GOAL_CODES="")
    z=json.loads(subprocess.run([str(ROOT/".build/bundle_colored"),"16",str(k),str(sec),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=sec+90,env=env).stdout);P=z.pop("candidate_pool");z.pop("neighbors");z["pool_sha256"]=pool_hash(P);z["starting_sha256"]=digest_words(C);(out/("polish_pool_"+str(k)+".txt")).write_text("\n".join(map(str,P))+"\n")
    if z["found"]:
     C=sorted(set(C)-set(z["removed"])|set(z["added"]));p=out/("strict_"+str(k)+".txt");p.write_text(canonical(C));z["verification"]=verify(p);assert z["verification"]["cardinality"]>=227;best=len(C);z["path"]=p.name;print("VERIFIED_227",case,p,flush=True)
    polish.append(z)
    if best>=227:break
  assert pos==len(results)-1
report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"plan_sha256":hashlib.sha256((OUT/"plan.json").read_bytes()).hexdigest(),"assigned_queries":len(queries),"attempted_queries":len(results),"not_attempted":[q["query"] for q in queries[len(results):]],"results":results,"positive":positive,"strict_followups":polish,"best_method_independently_verified":best,"retained_global_best_verified":max(226,best),"wall_seconds":time.monotonic()-t,"scope":plan["scope"]}
(out/"report.json").write_text(json.dumps(report,indent=2));print("FRESH_TRIPLES_RESULT",json.dumps({"case":case,"attempted":len(results),"complete_no_new226":sum(x["complete"] for x in results),"open":sum(x["limited"] for x in results),"positive":positive is not None,"best":best}),flush=True)
