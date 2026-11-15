"""Search a disjoint radius10neutral shard; protect all witness acceptance externally."""
import hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import check_integrity,verify
check_integrity();case=int(sys.argv[1]);OUT=ROOT/"artifacts/phase3/neutral10_goal_001";out=OUT/"workers"/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((OUT/"plan.json").read_text());assert plan["source_sha"]==os.environ["GITHUB_SHA"] and hashlib.sha256((ROOT/"phase3/bundle_neutral_goal.cpp").read_bytes()).hexdigest()==plan["kernel_sha256"]
C=[int(w,2) for w in (OUT/"starting.txt").read_text().split()];assert digest_words(C)==plan["starting_sha256"]
P=list(map(int,(OUT/"candidate_pool.txt").read_text().split()));known={tuple(map(int,line.split()[1:])) for line in (OUT/"known226.txt").read_text().splitlines()}
env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="8",CODEGARDEN_ROOT_SHARD=str(case),CODEGARDEN_ROOT_BEGIN="0",CODEGARDEN_ROOT_END=str(len(P)),CODEGARDEN_KNOWN_GOAL_CODES=str(OUT/"known226.txt"))
t=time.monotonic();r=json.loads(subprocess.run([str(ROOT/".build/bundle_neutral_goal"),"16","10","300","1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=420,env=env).stdout);actual=r.pop("candidate_pool");r.pop("neighbors");assert actual==P and r["k"]==10 and r["root_shard"]==case and r["root_shards"]==8
E=[i for i in range(len(P)) if i%8==case];done=r["completed_roots"];assert 0<=done<=len(E)
if done:assert r["last_finished_root"]==E[done-1]
if r["complete"]:assert done==len(E) and not r["found"]
positive=None;follow=[];best=226
if r["found"]:
 C=sorted(set(C)-set(r["removed"])|set(r["added"]));p=out/"candidate.txt";p.write_text(canonical(C));v=verify(p);assert v["cardinality"]>=226 and tuple(C) not in known;positive={"path":p.name,"verification":v};best=len(C);print("VERIFIED_227" if best>=227 else "VERIFIED_NEW226",case,p,flush=True)
 if best==226:
  for k,sec in [(6,10),(8,45),(10,90),(12,150)]:
   e=dict(env,CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0",CODEGARDEN_ROOT_END="65536",CODEGARDEN_KNOWN_GOAL_CODES="")
   z=json.loads(subprocess.run([str(ROOT/".build/bundle_colored"),"16",str(k),str(sec),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=sec+90,env=e).stdout);Q=z.pop("candidate_pool");z.pop("neighbors");z["pool_sha256"]=pool_hash(Q);z["starting_sha256"]=digest_words(C)
   (out/("strict_pool_"+str(k)+".txt")).write_text("\n".join(map(str,Q))+"\n")
   if z["found"]:
    C=sorted(set(C)-set(z["removed"])|set(z["added"]));p=out/("strict_"+str(k)+".txt");p.write_text(canonical(C));v=verify(p);assert v["cardinality"]>=227;z["verification"]=v;z["path"]=p.name;best=len(C);print("VERIFIED_227",case,p,flush=True)
   follow.append(z)
   if best>=227:break
report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"starting_sha256":plan["starting_sha256"],"pool_sha256":pool_hash(P),"ordered_pool_sha256":hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in P)).hexdigest(),"expected_roots":len(E),"new_completed_roots":done,"native":r,"positive":positive,"strict_followups":follow,"best_independently_verified":best,"wall_seconds":time.monotonic()-t,"scope":plan["scope"]}
(out/"report.json").write_text(json.dumps(report,indent=2));print("NEUTRAL10_RESULT",json.dumps({"case":case,"complete":r["complete"],"completed":done,"expected":len(E),"best":best,"positive":positive is not None,"cpu_seconds":r["cpu_seconds"]}),flush=True)
