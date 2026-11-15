"""Publish allowlisted research artifacts through Git data; never overwrite another head."""
import json,os,pathlib,subprocess
REPO=os.environ["GITHUB_REPOSITORY"];HEAD=os.environ["SOURCE_SHA"]
def api(path,payload=None):
    args=["gh","api",path]
    if payload is not None:args+=["--method","POST","--input","-"]
    p=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,capture_output=True,text=True,check=True)
    return json.loads(p.stdout)
ref=api("repos/"+REPO+"/git/ref/heads/codegarden")
if ref["object"]["sha"]!=HEAD:raise RuntimeError("CodeGarden branch advanced; refusing to replace it. Results remain in job logs.")
parent=api("repos/"+REPO+"/git/commits/"+HEAD)
entries=[]
for path in sorted(pathlib.Path("codegarden/artifacts").glob("remote_run.*")):
    entries.append({"path":str(path),"mode":"100644","type":"blob","content":path.read_text()})
path=pathlib.Path("codegarden/artifacts/provider_preflight_v2.json")
if path.exists():entries.append({"path":str(path),"mode":"100644","type":"blob","content":path.read_text()})
tree=api("repos/"+REPO+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries})
commit=api("repos/"+REPO+"/git/commits",{"message":"Record verified CodeGarden CPU batch","parents":[HEAD],"tree":tree["sha"]})
subprocess.run(["gh","api","repos/"+REPO+"/git/refs/heads/codegarden","--method","PATCH","--input","-"],
 input=json.dumps({"sha":commit["sha"],"force":False}),text=True,capture_output=True,check=True)
print(json.dumps({"published_commit":commit["sha"],"files":[x["path"] for x in entries]}))
