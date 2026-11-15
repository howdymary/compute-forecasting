"""Partition checks against protected-string brute force."""
import json,os,pathlib,random,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from phase3.test_connected2 import brute,vd
rng=random.Random(823171);rows=[]
for case in range(12):
 n=5 if case<4 else 6;order=list(range(1<<n));rng.shuffle(order);C=[];used=set()
 for w in order:
  ds=set(vd.descendants(format(w,"0%db"%n)))
  if not ds&used:C.append(w);used|=ds
 if case%3==0 and len(C)>1:C.pop()
 for k in [1,2,3]:
  expected,_=brute(C,n,k);reports=[]
  for shard in range(3):
   r=json.loads(subprocess.run([str(ROOT/".build/bundle"),str(n),str(k),"15","100000000","0"],input="\n".join(format(w,"0%db"%n) for w in C)+"\n",text=True,capture_output=True,check=True,env=dict(os.environ,CODEGARDEN_ROOT_SHARDS="3",CODEGARDEN_ROOT_SHARD=str(shard),CODEGARDEN_BLOCK_ORDER="1")).stdout)
   assert r["root_shard"]==shard and r["root_shards"]==3 and (r["found"] or r["complete"])
   reports.append(r)
  assert any(r["found"] for r in reports)==expected
  assert all(r["candidate_pool"]==reports[0]["candidate_pool"] for r in reports)
  if not expected:assert sum(r["completed_roots"] for r in reports)==len(reports[0]["candidate_pool"])
  rows.append({"case":case,"n":n,"k":k,"expected":expected,"shards":3,"passed":True})
out=ROOT/"artifacts/phase3/sharded9_001";out.mkdir(parents=True,exist_ok=True);(out/"partition_tests.json").write_text(json.dumps(rows,indent=2));print("SHARD_TESTS",len(rows))
