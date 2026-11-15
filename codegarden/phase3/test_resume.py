"""Complete disjoint root interval coverage checked against protected-string brute force."""
import json,os,pathlib,random,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from phase3.test_connected2 import brute,vd
rng=random.Random(1280001);rows=[]
for case in range(8):
 n=5 if case<4 else 6;order=list(range(1<<n));rng.shuffle(order);C=[];used=set()
 for w in order:
  ds=set(vd.descendants(format(w,"0%db"%n)))
  if not ds&used:C.append(w);used|=ds
 if case%3==0 and len(C)>1:C.pop()
 for k in [1,2,3]:
  expected,_=brute(C,n,k);reports=[];pool=None
  for shard in range(3):
   for begin,end in [(0,(1<<n)//2),((1<<n)//2,1<<n)]:
    r=json.loads(subprocess.run([str(ROOT/".build/bundle"),str(n),str(k),"10","100000000","0"],input="\n".join(format(w,"0%db"%n) for w in C)+"\n",text=True,capture_output=True,check=True,env=dict(os.environ,CODEGARDEN_ROOT_SHARDS="3",CODEGARDEN_ROOT_SHARD=str(shard),CODEGARDEN_ROOT_BEGIN=str(begin),CODEGARDEN_ROOT_END=str(end),CODEGARDEN_BLOCK_ORDER="1")).stdout)
    assert r["root_begin"]==begin and r["root_end"]==end and (r["found"] or r["complete"]);reports.append(r)
    if pool is None:pool=r["candidate_pool"]
    assert pool==r["candidate_pool"]
  assert any(r["found"] for r in reports)==expected
  if not expected:assert sum(r["completed_roots"] for r in reports)==len(pool)
  rows.append({"case":case,"n":n,"k":k,"expected":expected,"disjoint_intervals":6,"passed":True})
out=ROOT/"artifacts/phase3/resume10_001";out.mkdir(parents=True,exist_ok=True);(out/"tests.json").write_text(json.dumps(rows,indent=2));print("RESUME_TESTS",len(rows),flush=True)
