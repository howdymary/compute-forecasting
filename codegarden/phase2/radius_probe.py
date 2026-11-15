"""CPU-only independent brute-force checks and radius-three/four exploration."""
import hashlib,importlib.util,itertools,json,math,os,pathlib,random,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from search import canonical,pool_hash
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
D=module("radius_strings",ROOT/"protected/verify_descendants.py")
def feasible(pool,desc,target):
 if target==0:return True
 if len(pool)<target:return False
 for i,w in enumerate(pool):
  if feasible([v for v in pool[i+1:] if not desc[w]&desc[v]],desc,target-1):return True
 return False
def main():
 binary=ROOT/".build/radius_sweep";out=ROOT/"artifacts/phase2/radius34";out.mkdir(parents=True,exist_ok=True)
 desc={w:set(D.descendants(format(w,"06b"))) for w in range(64)};rng=random.Random(140614);tests=[]
 for case in range(12):
  order=list(range(64));rng.shuffle(order);code=[];occupied=set()
  for w in order:
   if not desc[w]&occupied:code.append(w);occupied|=desc[w]
  for k in range(1,5):
   expected=False
   for rem in itertools.combinations(code,k):
    fixed=[w for w in code if w not in rem];used=set().union(*(desc[w] for w in fixed)) if fixed else set()
    pool=[w for w in range(64) if w not in code and not desc[w]&used]
    if feasible(pool,desc,k+1):expected=True;break
   p=subprocess.run([str(binary),"6",str(k),"10"],input="\n".join(format(w,"06b") for w in code)+"\n",text=True,capture_output=True,check=True)
   r=json.loads(p.stdout);assert r["found"]==expected and (r["found"] or r["complete"]),(case,k,r,expected)
   tests.append({"case":case,"k":k,"found":r["found"],"complete":r["complete"]})
 (out/"tests.json").write_text(json.dumps({"all_agree":True,"cases":48,"tests":tests},indent=2))
 words=(ROOT/"artifacts/best_code.txt").read_text().splitlines();accepted=verify(ROOT/"artifacts/best_code.txt");code=[int(w,2) for w in words];reports=[]
 for k,seconds in [(3,45),(4,150)]:
  p=subprocess.run([str(binary),"16",str(k),str(seconds)],input="\n".join(words)+"\n",text=True,capture_output=True,timeout=seconds+20,check=True)
  r=json.loads(p.stdout);r.update({"source_sha":os.environ["GITHUB_SHA"],"incumbent_witness_sha256":accepted["reports"][0]["witness_sha256"],
   "candidate_universe_sha256":pool_hash(range(65536)),"restriction":"Exactly k removed incumbents and k+1 NEW words outside the original code; all removal sets and compatible words unless timed out",
   "total_removal_sets":math.comb(len(words),k),"starting_words":words,"proof_artifact":None,"budget_seconds":seconds})
  if r["found"]:
   new=[w for w in code if w not in r["removed"]]+r["added"];path=out/("worker_radius"+str(k)+".txt");path.write_text(canonical(new));r["independent_verification"]=verify(path)
  reports.append(r);(out/"sweeps.json").write_text(json.dumps(reports,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in {"starting_words","candidate_pool"}}),flush=True)
 # This job has no provider keys, no provider calls, and only updates its isolated branch.
 repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-radius34";head=os.environ["SOURCE_SHA"]
 def api(path,payload=None,method=None):
  args=["gh","api",path]
  if payload is not None:args+=["--method",method or "POST","--input","-"]
  p=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(p.stdout)
 current=api("repos/"+repo+"/git/ref/heads/"+branch)
 if current["object"]["sha"]!=head:raise RuntimeError("Probe branch lease moved")
 parent=api("repos/"+repo+"/git/commits/"+head)
 entries=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in list(out.glob("*.json"))+list(out.glob("*.txt"))]
 tree=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries})
 commit=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":tree["sha"],"message":"Record exact radius-three/four enumeration and independently checked witness if feasible"})
 api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":commit["sha"],"force":False},"PATCH")
 print("RADIUS_PUBLISHED "+commit["sha"])
if __name__=="__main__":main()
