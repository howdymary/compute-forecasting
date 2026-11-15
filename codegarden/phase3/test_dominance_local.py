"""Independent brute-force strict feasibility comparison with proven outside dominance."""
import json,os,pathlib,random,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from phase3.test_connected2 import brute,vd
def main():
 rows=[];rng=random.Random(771128);exe=ROOT/".build/bundle"
 for case in range(12):
  n=5 if case<3 else 6;ds={w:set(vd.descendants(format(w,"0%db"%n))) for w in range(1<<n)};retained=[];removed=[]
  for w in sorted(ds,key=lambda x:(len(ds[x]),x)):
   u=next((u for u in retained if ds[u]<=ds[w]),None)
   if u is None:retained.append(w)
   else:removed.append(w);assert ds[u]<=ds[w]
  mask=ROOT/".build"/("small_dom_"+str(n)+".txt");mask.write_text("\n".join(map(str,removed))+"\n")
  order=list(ds);rng.shuffle(order);C=[];used=set()
  for w in order:
   if not ds[w]&used:C.append(w);used|=ds[w]
  if case%3==0 and len(C)>1:C.pop()
  for k in [1,2,3]:
   expected,_=brute(C,n,k);inputs="\n".join(format(w,"0%db"%n) for w in C)+"\n";got=[]
   for filter_path in ["",str(mask)]:
    r=json.loads(subprocess.run([str(exe),str(n),str(k),"15","100000000","0"],input=inputs,text=True,capture_output=True,check=True,env=dict(os.environ,CODEGARDEN_DOMINANCE_FILTER=filter_path,CODEGARDEN_BLOCK_ORDER="1")).stdout)
    assert r["found"]==expected and (r["found"] or r["complete"]),(case,k,r)
    if r["found"]:vd.verify([format(w,"0%db"%n) for w in sorted(set(C)-set(r["removed"])|set(r["added"]))],n)
    got.append(r["found"])
   rows.append({"case":case,"n":n,"k":k,"incumbent":C,"excluded_outside_words":len(removed),"expected_strict_improvement":expected,"both_match":got[0]==got[1]})
 out=ROOT/"artifacts/phase3/dominance_native_002";out.mkdir(parents=True,exist_ok=True);(out/"test_local_filter.json").write_text(json.dumps({"cases":rows,"passed":len(rows),"oracle":"Exhaustive removal subsets and protected string descendant sets"},indent=2));print("DOMINANCE_LOCAL_TESTS",len(rows),flush=True)
if __name__=="__main__":main()
