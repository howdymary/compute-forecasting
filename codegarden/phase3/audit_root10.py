"""Standalone completion coverage audit, not an independent formal absence proof."""
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity
check_integrity();N=61427;pool="091054e7eb0c2642a937e2d7a4d05a9a90ff9c55070a72ee88964829b80e8044";incumbent="417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa"
coverage=[0]*N;old=[];resumed=[];receipts=[];cpu=0
for i in range(8):
 p=ROOT/"artifacts/phase3/sharded10_001/workers"/(str(i)+".json");r=json.loads(p.read_text());m=r["metadata"];n=r["native"]
 assert m["source_sha"]=="b0039e3dcc3e8884cb667ca3e914c19a2d709d80" and m["starting_sha256"]==incumbent
 assert n["candidate_count"]==N and n["candidate_pool_sha256"]==pool and n["root_shard"]==i and n["root_shards"]==8 and n["k"]==10 and not n["found"]
 assert not n["complete"] and n["budget_limited"] and not n["memory_limited"]
 roots=list(range(i,n["active_root"],8));assert len(roots)==n["completed_roots"] and roots[-1]==n["last_finished_root"]
 for j in roots:coverage[j]+=1
 old.append({"shard":i,"active_root":n["active_root"],"completed_roots":len(roots),"cpu_seconds":n["cpu_seconds"]});cpu+=n["cpu_seconds"];receipts.append({"path":str(p.relative_to(ROOT)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
for i in range(32):
 p=ROOT/"artifacts/phase3/resume10_001"/str(i)/"report.json";r=json.loads(p.read_text());n=r["native"];begin=old[i%8]["active_root"]
 assert r["source_sha"]=="06000bb4fd75dda6cbdd442e10adf062093d501f" and r["candidate_pool_sha256"]==pool and r["root_begin"]==begin
 assert n["candidate_count"]==N and n["k"]==10 and n["complete"] and not n["found"] and not n["memory_limited"] and not n["budget_limited"]
 assert n["root_shard"]==i and n["root_shards"]==32 and n["root_begin"]==begin
 assert r["starting_verification"]["accepted"] and r["starting_verification"]["reports"][0]["witness_sha256"]==incumbent
 roots=[j for j in range(begin,N) if j%32==i];assert len(roots)==n["completed_roots"] and roots[-1]==n["last_finished_root"]
 for j in roots:coverage[j]+=1
 resumed.append({"shard":i,"begin":begin,"completed_roots":len(roots),"cpu_seconds":n["cpu_seconds"]});cpu+=n["cpu_seconds"];receipts.append({"path":str(p.relative_to(ROOT)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
assert all(x==1 for x in coverage)
out=ROOT/"artifacts/phase3/audits_001";out.mkdir(parents=True,exist_ok=True)
report={"incumbent_sha256":incumbent,"candidate_pool_sha256":pool,"candidate_count":N,"radius":10,"old_root_prefixes":old,"resumed_suffixes":resumed,"all_roots_covered_exactly_once":True,"all_native_cpu_seconds":cpu,"source_receipts":receipts,"scope":"Coverage audit only. Native completed connected-bundle enumeration under pinned safe reductions found no strict exchange removing at most10 root words. This script does not independently re-enumerate or provide a formal absence certificate. No global optimality conclusion."}
(out/"root10_coverage.json").write_text(json.dumps(report,indent=2));print("ROOT10_COVERAGE",N,"roots exactly once",cpu,flush=True)
