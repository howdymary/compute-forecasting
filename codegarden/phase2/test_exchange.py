"""Brute-force independent checks of the compiled exact exchange neighborhood."""
import importlib.util,itertools,json,pathlib,random,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
D=load("exchange_strings",ROOT/"protected/verify_descendants.py")
def main():
 kernel=ROOT/".build/kernel_v2";desc={w:set(D.descendants(format(w,"06b"))) for w in range(64)}
 rng=random.Random(1706);reports=[]
 for case in range(24):
  order=list(range(64));rng.shuffle(order);code=[];used=set()
  for w in order:
   if not desc[w]&used:code.append(w);used|=desc[w]
  if case%3==0 and len(code)>2:code.pop()
  for k in [1,2]:
   expected=False
   for removed in itertools.combinations(code,k):
    fixed=[w for w in code if w not in removed];occupied=set().union(*(desc[w] for w in fixed)) if fixed else set()
    pool=[w for w in range(64) if w not in code and not desc[w]&occupied]
    for added in itertools.combinations(pool,k+1):
     if all(not desc[a]&desc[b] for a,b in itertools.combinations(added,2)):expected=True;break
    if expected:break
   p=subprocess.run([str(kernel),"--augment","6",str(k),"3"],input="\n".join(format(w,"06b") for w in code)+"\n",
    text=True,capture_output=True,check=True)
   r=json.loads(p.stdout);assert r["found"]==expected,(case,k,r,expected)
   assert r["found"] or r["complete"],r
   if r["found"]:
    new=[w for w in code if w not in r["removed"]]+r["added"];D.verify([format(w,"06b") for w in new],6)
   reports.append({"case":case,"k":k,"found":r["found"],"complete":r["complete"],"checks":r["checks"]})
 baseline=(ROOT/"artifacts/best_code.txt").read_text()
 p=subprocess.run([str(kernel),".2","1706","adaptive","", "227","0"],input=baseline,text=True,capture_output=True,check=True)
 native=json.loads(p.stdout);D.verify([format(w,"016b") for w in native["best"]],16)
 out=ROOT/"artifacts/phase2";out.mkdir(parents=True,exist_ok=True)
 (out/"exchange_tests.json").write_text(json.dumps({"bruteforce_cases":48,"all_agree":True,"reports":reports,
   "native_iterations":native["iterations"],"native_incremental_check":True},indent=2))
 print("EXCHANGE_TESTS 48 brute-force comparisons pass")
if __name__=="__main__":main()
