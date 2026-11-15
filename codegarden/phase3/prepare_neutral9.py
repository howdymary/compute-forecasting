"""Pin a genuinely larger neutral radius after one completed radius8root."""
import hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.core_hulls import symmetries
check_integrity();OUT=ROOT/"artifacts/phase3/neutral9_goal_001";OUT.mkdir(parents=True,exist_ok=True)
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());C=info["codes"][0]
p=OUT/"starting.txt";p.write_text(canonical(C));v=verify(p);assert v["cardinality"]==226
oldpath=ROOT/"artifacts/phase3/neutral8_order_001/0/report.json";old=json.loads(oldpath.read_text())
assert old["native"]["k"]==8 and old["native"]["complete"] and not old["native"]["found"] and not old["novel_verified"]
assert old["starting_verification"]["reports"][0]["witness_sha256"]==digest_words(C)
known=sorted({tuple(K) for B in info["codes"] for K in symmetries(B)})
assert tuple(sorted(C)) in known and all(len(K)==226 for K in known)
kp=OUT/"known226.txt";kp.write_text("".join("226 "+" ".join(map(str,K))+"\n" for K in known))
env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="8",CODEGARDEN_ROOT_SHARD="0",CODEGARDEN_ROOT_BEGIN="0",CODEGARDEN_ROOT_END="0",CODEGARDEN_KNOWN_GOAL_CODES=str(kp))
r=json.loads(subprocess.run([str(ROOT/".build/bundle_neutral_goal"),"16","9","30","1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=90,env=env).stdout)
assert r["complete"] and not r["found"] and r["completed_roots"]==0 and r["neutral_or_improving"]
P=r.pop("candidate_pool");r.pop("neighbors");(OUT/"candidate_pool.txt").write_text("\n".join(map(str,P))+"\n")
plan={"source_sha":os.environ["GITHUB_SHA"],"starting_verification":v,"starting_sha256":digest_words(C),"known_codes":len(known),"known_codes_sha256":hashlib.sha256(kp.read_bytes()).hexdigest(),"pool_size":len(P),"pool_sha256":pool_hash(P),"ordered_pool_sha256":hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in P)).hexdigest(),"native_profile":r,"prior_neutral8_report_sha256":hashlib.sha256(oldpath.read_bytes()).hexdigest(),"prior_neutral8_source_sha":old["source_sha"],"kernel_sha256":hashlib.sha256((ROOT/"phase3/bundle_neutral_goal.cpp").read_bytes()).hexdigest(),"shards":8,"native_cpu_per_shard":300,"hypothesis":"The previous completed radius8neutral root found no outside226basin. Radius9neutral-or-improving proposals may reach a different226code even where strict227augmentations are closed. Known152oriented codes are excluded as exact arrays only, never excluding227supersets.","scope":"Connected outside-blocker bundles plus saturated repair pools, not all disconnected neutral exchanges. Coverage has no formal absence certificate. All valid new226codes retained; primary target remains227."}
(OUT/"plan.json").write_text(json.dumps(plan,indent=2));print("NEUTRAL9_PLAN",json.dumps({k:plan[k] for k in ["starting_sha256","known_codes","pool_size","native_cpu_per_shard","hypothesis"]}),flush=True)
