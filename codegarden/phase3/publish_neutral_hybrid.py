"""Leased publication of only this CodeGarden batch, with bounded Git tree requests."""
import base64,json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/neutral_hybrid_001"
def api(path,payload=None,method=None):
 args=["gh","api",path]
 if payload is not None:args+=["--method",method or "POST","--input","-"]
 result=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(result.stdout)
repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-neutral-hybrid-001";head=os.environ["GITHUB_SHA"];assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
parent=api("repos/"+repo+"/git/commits/"+head);base=parent["tree"]["sha"];batch=[];size=0
def flush():
 global base,batch,size
 if batch:base=api("repos/"+repo+"/git/trees",{"base_tree":base,"tree":batch})["sha"];batch=[];size=0
for p in sorted(OUT.rglob("*")):
 if not p.is_file():continue
 path=str(p.relative_to(ROOT.parent))
 if p.suffix==".gz":
  blob=api("repos/"+repo+"/git/blobs",{"content":base64.b64encode(p.read_bytes()).decode(),"encoding":"base64"});entry={"path":path,"mode":"100644","type":"blob","sha":blob["sha"]};n=len(json.dumps(entry).encode())
 elif p.suffix in [".json",".txt",".pbtxt",".jsonl"]:
  if p.suffix==".jsonl" and p.with_name(p.name+".gz").exists():continue
  entry={"path":path,"mode":"100644","type":"blob","content":p.read_text()};n=len(json.dumps(entry).encode())
 else:continue
 if batch and (len(batch)>=100 or size+n>180000):flush()
 batch.append(entry);size+=n
flush();commit=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":base,"message":"Record optional pivot repairs with full raw-member eligibility checks and independent positive verification"})
assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":commit["sha"],"force":False},"PATCH");print("ADAPTIVE_HULL_PUBLISHED",commit["sha"])
