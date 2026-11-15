"""Independent exhaustive small-instance checks using protected string descendants."""
import importlib.util,itertools,json,pathlib,random,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity
check_integrity()
spec=importlib.util.spec_from_file_location("protected_d2",ROOT/"protected/verify_descendants.py")
vd=importlib.util.module_from_spec(spec);spec.loader.exec_module(vd)
def brute(code,n,k,neutrals=False):
 ds={w:set(vd.descendants(format(w,"0%db"%n))) for w in range(1<<n)};C=set(code);answers=set()
 for size in range(min(k,len(C))+1):
  for removed in itertools.combinations(sorted(C),size):
   fixed=C-set(removed);occupied=set().union(*(ds[w] for w in fixed))
   pool=[w for w in ds if w not in C and not ds[w]&occupied]
   def rec(pos,chosen,used):
    if len(chosen)>size:return True
    if neutrals and len(chosen)==size and chosen:answers.add(tuple(sorted(fixed|set(chosen))))
    for j in range(pos,len(pool)):
     w=pool[j]
     if not ds[w]&used and rec(j+1,chosen+[w],used|ds[w]):return True
    return False
   if rec(0,[],set()):return True,answers
 return False,answers
def main():
 rng=random.Random(99137);rows=[];exe=ROOT/".build/bundle"
 for seed in range(12):
  n=5 if seed<3 else 6;order=list(range(1<<n));rng.shuffle(order);code=[];used=set()
  for w in order:
   d=set(vd.descendants(format(w,"0%db"%n)))
   if not used&d:code.append(w);used|=d
  if seed%3==0 and len(code)>1:code.pop()
  for k in [1,2,3]:
   expected,_=brute(code,n,k)
   args=[str(exe),str(n),str(k),"15","10000000"]
   text="\n".join(format(w,"0%db"%n) for w in code)+"\n"
   r=json.loads(subprocess.run(args+["0"],input=text,capture_output=True,text=True,check=True).stdout)
   assert r["found"]==expected,(code,k,r,expected);assert r["found"] or r["complete"]
   if r["found"]:vd.verify([format(w,"0%db"%n) for w in sorted(set(code)-set(r["removed"])|set(r["added"]))],n)
   else:
    expected,neighbors=brute(code,n,k,True);assert not expected
    q=json.loads(subprocess.run(args+["100000"],input=text,capture_output=True,text=True,check=True).stdout)
    assert q["complete"] and set(map(tuple,q["neighbors"]))==neighbors,(q,neighbors)
    for other in q["neighbors"]:vd.verify([format(w,"0%db"%n) for w in other],n)
   rows.append({"seed":seed,"length":n,"size":len(code),"k":k,"improving":expected,"nodes":r["nodes"]})
 out=ROOT/"artifacts/phase3/bundle_anchor_001";out.mkdir(parents=True,exist_ok=True)
 (out/"test.json").write_text(json.dumps({"cases":rows,"passed":len(rows),"neutral_sets":"Complete sets compared where no augmentation exists; protected string D2 checks"},indent=2))
 print("BUNDLE_TESTS",len(rows),flush=True)
if __name__=="__main__":main()
