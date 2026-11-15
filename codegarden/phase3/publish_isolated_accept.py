"""Leased publication of only this CodeGarden batch, with bounded Git tree requests."""
import json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/isolated_acceptance_001"
def api(path,payload=None,method=None):
 args=["gh","api",path]
 if payload is not None:args+=["--method",method or "POST","--input","-"]
 result=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(result.stdout)
repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-isolated-accept-003";head=os.environ["GITHUB_SHA"];assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
parent=api("repos/"+repo+"/git/commits/"+head);base=parent["tree"]["sha"];batch=[];size=0
def flush():
 global base,batch,size
 if batch:base=api("repos/"+repo+"/git/trees",{"base_tree":base,"tree":batch})["sha"];batch=[];size=0
for p in sorted(OUT.rglob("*")):
 if not p.is_file() or p.suffix not in [".json",".txt",".pbtxt",".jsonl"]:continue
 rel=p.relative_to(OUT)
 entry={"path":str(p.relative_to(ROOT.parent)).replace("/isolated_acceptance_001/","/isolated_acceptance_001/"),"mode":"100644","type":"blob","content":p.read_text()};n=len(json.dumps(entry).encode())
 if batch and (len(batch)>=100 or size+n>180000):flush()
 batch.append(entry);size+=n
flush();commit=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":base,"message":"Record fresh verifier-only replay from pinned immutable checker sources; no search proposer runs in acceptance job"})
assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":commit["sha"],"force":False},"PATCH");print("ADAPTIVE_HULL_PUBLISHED",commit["sha"])
