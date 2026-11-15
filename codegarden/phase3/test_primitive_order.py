"""Compare both candidate orders with protected-string strict and primitive-neutral oracles."""
import json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from phase3.test_primitive import brute,vd
import random
rng=random.Random(739911);rows=[]
for case in range(12):
 n=5 if case<4 else 6;order=list(range(1<<n));rng.shuffle(order);C=[];used=set();ds={w:set(vd.descendants(format(w,"0%db"%n))) for w in order}
 for w in order:
  if not used&ds[w]:C.append(w);used|=ds[w]
 if case%3==0 and len(C)>1:C.pop()
 for k in [1,2,3]:
  expected,_=brute(C,n,k);primitive=set()
  if not expected:
   _,neutrals=brute(C,n,k,True)
   for A in neutrals:
    added=sorted(set(A)-set(C));B=[{w for w in C if ds[v]&ds[w]} for v in added];seen={0}
    while True:
     nxt=seen|{j for j in range(len(added)) if any(B[i]&B[j] for i in seen)}
     if nxt==seen:break
     seen=nxt
    if len(seen)==len(added):primitive.add(A)
  for ordering in ["1","2"]:
   r=json.loads(subprocess.run([str(ROOT/".build/bundle"),str(n),str(k),"15","100000000","100000"],input="\n".join(format(w,"0%db"%n) for w in C)+"\n",text=True,capture_output=True,check=True,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER=ordering)).stdout)
   assert r["found"]==expected and (r["found"] or r["complete"])
   if not expected:assert {tuple(v) for v in r["neighbors"]}==primitive,(case,k,ordering,len(primitive),r)
  rows.append({"case":case,"n":n,"k":k,"strict":expected,"primitive_neutral_count":len(primitive) if not expected else None,"both_orders_passed":True})
out=ROOT/"artifacts/phase3/neutral8_order_001";out.mkdir(parents=True,exist_ok=True);(out/"oracle_tests.json").write_text(json.dumps(rows,indent=2));print("PRIMITIVE_ORDER_TESTS",len(rows))
