"""Bounded neutral plateau walks after exact direct augmentation exhaustion."""
import json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from search import canonical
def main():
 out=ROOT/"artifacts/phase2/neutral_walk";out.mkdir(parents=True,exist_ok=True);words=(ROOT/"artifacts/best_code.txt").read_text()
 rows=[]
 for seed in range(818000,818004):
  r=json.loads(subprocess.run([str(ROOT/".build/neutral_kernel"),"30",str(seed)],input=words,text=True,capture_output=True,timeout=50,check=True).stdout)
  path=out/("worker_neutral_"+str(seed)+".txt");path.write_text(canonical(r["best"]));r["independent_verification"]=verify(path)
  r["source_sha"]=os.environ["GITHUB_SHA"];r["witness"]=str(path.relative_to(ROOT.parent));rows.append(r)
  (out/"report.json").write_text(json.dumps({"experiments":rows,"hypothesis":"Neutral moves can invalidate root-specific exhaustion and expose productive adjacent incumbents.",
   "selection":"Outer research assistant, after exact k<=4 root exhaustion; outside the frozen policy comparison.","cost":"Standard public GitHub CPU runner only; no provider calls."},indent=2))
  print("NEUTRAL "+json.dumps({k:v for k,v in r.items() if k not in ["best","independent_verification"]}),flush=True)
  if r["independent_verification"]["cardinality"]>226:break
 repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-radius34";head=os.environ["SOURCE_SHA"]
 def api(path,payload=None,method=None):
  args=["gh","api",path]
  if payload is not None:args+=["--method",method or "POST","--input","-"]
  p=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(p.stdout)
 assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
 parent=api("repos/"+repo+"/git/commits/"+head);entries=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in list(out.glob("*.json"))+list(out.glob("*.txt"))]
 t=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries})
 c=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":t["sha"],"message":"Record neutral plateau walks, state-scoped exhaustion reuse and verified results"})
 api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":c["sha"],"force":False},"PATCH")
if __name__=="__main__":main()
