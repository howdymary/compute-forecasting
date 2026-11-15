"""Retry only exact unfinished modulo suffixes of two immutable coverage families."""
import hashlib,json,os,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import check_integrity,verify
check_integrity();OUT=ROOT/"artifacts/phase3/suffix_retry_001";OUT.mkdir(parents=True,exist_ok=True);families=[];tasks=[]
for name,prefix,rank,shards,kind,expected_source,parent in [
 ("neutral10","neutral10_goal_001",10,8,"neutral","d0afc0069930e375de6ee5eada861cc4f7388a53",None),
 ("fresh9_parent6","fresh9_tail_001",9,4,"strict","613c86f234a070b0a7b13331675c0b9b42fc3a66",6)]:
 base=ROOT/"artifacts/phase3"/prefix;raw=(base/"coverage.json").read_bytes();allold=json.loads(raw);assert allold["source_sha"]==expected_source and allold["exchange_rank"]==rank
 old=allold if parent is None else allold["parents"][parent];assert not old.get("positives",old.get("positive_verifications",[])) and not old["duplicate_completed_roots"]
 family=len(families);(OUT/("previous_"+str(family)+".json")).write_bytes(raw)
 src=base if parent is None else base/"sources"/str(parent);C=[int(w,2) for w in (src/"starting.txt").read_text().split()];v=verify(src/"starting.txt");P=list(map(int,(src/"candidate_pool.txt").read_text().split()));assert v["cardinality"]==len(C) and len(P)==old["pool_size"] and digest_words(C)==old.get("starting_sha256",old.get("source_incumbent_sha256"))
 ordered=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in P)).hexdigest()
 if parent is None:assert ordered==old["ordered_pool_sha256"]
 families.append({"family":family,"name":name,"rank":rank,"shards":shards,"kind":kind,"source_sha":expected_source,"source_prefix":prefix,"source_parent":parent,"starting_sha256":digest_words(C),"starting_verification":v,"pool_size":len(P),"pool_sha256":pool_hash(P),"ordered_pool_sha256":ordered,"previous_coverage_sha256":hashlib.sha256(raw).hexdigest(),"previous_completed":old["total_unique_completed_roots"],"previous_uncovered_roots":old["uncovered_roots"],"goal_filter_enabled":True})
 for shard in range(shards):
  U=sorted(i for i in old["uncovered_roots"] if i%shards==shard)
  if not U:continue
  assert U==list(range(U[0],len(P),shards))
  case=len(tasks);dest=OUT/"sources"/str(case);dest.mkdir(parents=True,exist_ok=True)
  for filename in ["starting.txt","candidate_pool.txt","known226.txt"]:(dest/filename).write_bytes((src/filename).read_bytes())
  tasks.append({"case":case,"family":family,"shard":shard,"root_begin":U[0],"expected_remaining_roots":len(U),"native_cpu_limit_seconds":300})
plan={"source_sha":os.environ["GITHUB_SHA"],"families":families,"tasks":tasks,"input_authority_commit":"635d085cc08145c55fad58821678e86d02c3fe93","scope":"Only unfinished modulo suffixes, exact prior pools/orders/seed and goal formulation. Preserve all old completed roots. Interrupted roots are open. Connected/saturated goal scope retained; no global or formal absence proof."}
assert len(tasks)==10
(OUT/"plan.json").write_text(json.dumps(plan,indent=2));print("SUFFIX_RETRY_PLAN",json.dumps(tasks),flush=True)
