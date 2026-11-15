"""Continue an explicit unfinished shard without replaying its completed root prefix."""
import hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import check_integrity,verify
check_integrity();case=int(sys.argv[1]);OUT=ROOT/"artifacts/phase3/suffix_retry_001";out=OUT/"workers"/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((OUT/"plan.json").read_text());q=plan["tasks"][case];p=plan["families"][q["family"]];base=OUT/"sources"/str(case)
C=[int(w,2) for w in (base/"starting.txt").read_text().split()];assert digest_words(C)==p["starting_sha256"];P=list(map(int,(base/"candidate_pool.txt").read_text().split()));E=[i for i in p["previous_uncovered_roots"] if i%p["shards"]==q["shard"]];assert E==list(range(q["root_begin"],len(P),p["shards"])) and len(E)==q["expected_remaining_roots"]
env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS=str(p["shards"]),CODEGARDEN_ROOT_SHARD=str(q["shard"]),CODEGARDEN_ROOT_BEGIN=str(q["root_begin"]),CODEGARDEN_ROOT_END=str(len(P)),CODEGARDEN_KNOWN_GOAL_CODES=str(base/"known226.txt"))
exe="bundle_neutral_goal" if p["kind"]=="neutral" else "bundle_colored";t=time.monotonic();r=json.loads(subprocess.run([str(ROOT/".build"/exe),"16",str(p["rank"]),"300","1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=420,env=env).stdout);actual=r.pop("candidate_pool");r.pop("neighbors");assert actual==P and r["k"]==p["rank"] and r["root_begin"]==q["root_begin"] and r["root_shards"]==p["shards"] and r["root_shard"]==q["shard"]
done=r["completed_roots"];assert 0<=done<=len(E)
if done:assert r["last_finished_root"]==E[done-1]
if r["complete"]:assert done==len(E) and not r["found"]
positive=None;follow=[];best=len(C)
if r["found"]:
 C=sorted(set(C)-set(r["removed"])|set(r["added"]));path=out/"candidate.txt";path.write_text(canonical(C));v=verify(path);assert v["cardinality"]>=226;known={tuple(map(int,l.split()[1:])) for l in (base/"known226.txt").read_text().splitlines()};assert tuple(C) not in known;best=len(C);positive={"path":path.name,"verification":v};print("VERIFIED_227" if best>=227 else "VERIFIED_NEW226",case,path,flush=True)
 if best==226:
  for k,sec in [(6,10),(8,45),(10,90),(12,150)]:
   e=dict(env,CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0",CODEGARDEN_ROOT_BEGIN="0",CODEGARDEN_ROOT_END="65536",CODEGARDEN_KNOWN_GOAL_CODES="")
   z=json.loads(subprocess.run([str(ROOT/".build/bundle_colored"),"16",str(k),str(sec),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=sec+90,env=e).stdout);Q=z.pop("candidate_pool");z.pop("neighbors");z["pool_sha256"]=pool_hash(Q);z["starting_sha256"]=digest_words(C);(out/("strict_pool_"+str(k)+".txt")).write_text("\n".join(map(str,Q))+"\n")
   if z["found"]:
    C=sorted(set(C)-set(z["removed"])|set(z["added"]));path=out/("strict_"+str(k)+".txt");path.write_text(canonical(C));z["verification"]=verify(path);assert z["verification"]["cardinality"]>=227;z["path"]=path.name;best=len(C);print("VERIFIED_227",case,path,flush=True)
   follow.append(z)
   if best>=227:break
report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"family":q["family"],"shard":q["shard"],"starting_sha256":p["starting_sha256"],"pool_sha256":pool_hash(P),"ordered_pool_sha256":hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in P)).hexdigest(),"root_begin":q["root_begin"],"expected_remaining_roots":len(E),"new_completed_roots":done,"native":r,"positive":positive,"strict_followups":follow,"best_method_independently_verified":best,"retained_global_best_verified":max(226,best),"wall_seconds":time.monotonic()-t,"scope":plan["scope"]}
(out/"report.json").write_text(json.dumps(report,indent=2));print("SUFFIX_RETRY_RESULT",json.dumps({"case":case,"family":p["name"],"shard":q["shard"],"complete":r["complete"],"completed":done,"expected":len(E),"positive":positive is not None,"best":best}),flush=True)
