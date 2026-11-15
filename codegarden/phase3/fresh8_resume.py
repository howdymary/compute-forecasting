"""Bounded exact canonical-root suffix shard, with literal input/order guards."""
import hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,pool_hash,digest_words
from supervisor import check_integrity,verify
check_integrity();case=int(sys.argv[1]);parent=case//4;shard=case%4;OUT=ROOT/"artifacts/phase3/fresh8_resume_001";out=OUT/"workers"/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((OUT/"plan.json").read_text());assert hashlib.sha256((ROOT/"phase3/bundle_colored.cpp").read_bytes()).hexdigest()==plan["colored_kernel_sha256"];p=plan["cases"][parent];base=OUT/"sources"/str(parent)
if not p["eligible"] or plan["goal_candidate227"]:
 (out/"report.json").write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"case":case,"parent":parent,"shard":shard,"status":"NO_SEARCH","reason":p["reason"] if not plan["goal_candidate227"] else "goal_candidate_pending_fresh_acceptance"},indent=2));sys.exit(0)
C=[int(w,2) for w in (base/"starting.txt").read_text().split()];assert digest_words(C)==p["starting_sha256"];startv=verify(base/"starting.txt");P=list(map(int,(base/"candidate_pool.txt").read_text().split()));expected=[i for i in range(p["old_completed_prefix"],len(P)) if i%4==shard]
env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="4",CODEGARDEN_ROOT_SHARD=str(shard),CODEGARDEN_ROOT_BEGIN=str(p["old_completed_prefix"]),CODEGARDEN_ROOT_END=str(len(P)),CODEGARDEN_KNOWN_GOAL_CODES=str(base/"known226.txt") if p["goal_filter_enabled"] else "")
begin=time.monotonic();r=json.loads(subprocess.run([str(ROOT/".build/bundle_colored"),"16","8","150","1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=240,env=env).stdout);actual=r.pop("candidate_pool");r.pop("neighbors");assert actual==P
assert r["root_begin"]==p["old_completed_prefix"] and r["root_end"]==len(P) and r["root_shards"]==4 and r["root_shard"]==shard
done=r["completed_roots"];assert 0<=done<=len(expected)
if done:assert r["last_finished_root"]==expected[done-1]
else:assert r["last_finished_root"]==-1
if r["complete"]:assert done==len(expected) and not r["found"]
positive=None
if r["found"]:
 C=sorted(set(C)-set(r["removed"])|set(r["added"]));path=out/"candidate.txt";path.write_text(canonical(C));v=verify(path);assert v["cardinality"]>=226;known={tuple(map(int,line.split()[1:])) for line in (base/"known226.txt").read_text().splitlines()};assert len(C)>=227 or tuple(C) not in known;positive={"path":path.name,"verification":v};print("VERIFIED_227" if len(C)>=227 else "VERIFIED_NEW226",path,flush=True)
report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"parent":parent,"shard":shard,"status":"SEARCHED","starting_sha256":p["starting_sha256"],"starting_verification":startv,"pool_sha256":pool_hash(P),"ordered_pool_sha256":hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in P)).hexdigest(),"old_completed_prefix":p["old_completed_prefix"],"expected_suffix_roots":len(expected),"new_completed_roots":done,"native":r,"positive":positive,"wall_seconds":time.monotonic()-begin,"best_method_independently_verified":len(C),"retained_global_best_verified":max(226,len(C)),"scope":"Only this disjoint modulo4suffix of the source-pinned K8candidate order. Old completed prefix remains separately attributed. Time/node/memory caps are open. Filtered queries only concern enumerated connected goal bundles and saturated pools, not all novel codes. Positive acceptance unchanged; no formal global absence proof."}
(out/"report.json").write_text(json.dumps(report,indent=2));print("FRESH8_RESUME",json.dumps({"case":case,"parent":parent,"shard":shard,"complete":r["complete"],"new_completed":done,"expected":len(expected),"found":r["found"],"best":len(C),"cpu_seconds":r["cpu_seconds"]}),flush=True)
