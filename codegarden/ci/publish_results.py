"""Publish allowlisted CodeGarden outputs; reject a divergent branch head."""
import json,os,pathlib,subprocess,base64
REPO=os.environ["GITHUB_REPOSITORY"];HEAD=os.environ["SOURCE_SHA"]
def api(path,payload=None,method=None):
    args=["gh","api",path]
    if payload is not None:args+=["--method",method or "POST","--input","-"]
    p=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,capture_output=True,text=True,check=True)
    return json.loads(p.stdout)
ref=api("repos/"+REPO+"/git/ref/heads/codegarden")
if ref["object"]["sha"]!=HEAD:raise RuntimeError("CodeGarden branch advanced; refusing to replace it")
parent=api("repos/"+REPO+"/git/commits/"+HEAD);entries=[]
allowed=list(pathlib.Path("codegarden/artifacts/live").glob("*.json"))
allowed+=list(pathlib.Path("codegarden/artifacts/live").glob("*.txt"))
allowed+=list(pathlib.Path("codegarden/artifacts").glob("cp_*.json"))
allowed+=list(pathlib.Path("codegarden/artifacts").glob("cp_*.txt"))
allowed+=list(pathlib.Path("codegarden/artifacts").glob("provider_preflight*.json"))
allowed+=list(pathlib.Path("codegarden/artifacts").glob("final_*.json"))
for path in sorted(set(allowed)):
    entries.append({"path":str(path),"mode":"100644","type":"blob","content":path.read_text()})
if not entries:raise RuntimeError("No allowlisted results")
tree=api("repos/"+REPO+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries})
commit=api("repos/"+REPO+"/git/commits",{"message":"Record CodeGarden sponsor loop and independently verified exact searches","parents":[HEAD],"tree":tree["sha"]})
api("repos/"+REPO+"/git/refs/heads/codegarden",{"sha":commit["sha"],"force":False},"PATCH")
print(json.dumps({"published_commit":commit["sha"],"files":[x["path"] for x in entries]}))
