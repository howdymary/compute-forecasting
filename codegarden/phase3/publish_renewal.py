"""Publish research evidence on its own isolated branch; retain failures too."""
import json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/budget_renewal_002"
def api(path,payload=None,method=None):
 args=["gh","api",path]
 if payload is not None:args+=["--method",method or "POST","--input","-"]
 r=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(r.stdout)
repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-budget-004";head=os.environ.get("SOURCE_SHA",os.environ["GITHUB_SHA"])
assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
parent=api("repos/"+repo+"/git/commits/"+head);paths=list(OUT.glob("*.json"))
paths += [ROOT/"budget/shared-allocation.json",ROOT/"budget/historical-usage.json"]
entries=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in paths if p.exists()]
t=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries})
c=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":t["sha"],"message":"Record refreshed cumulative allocation, Exa record/method research and actual cross-role memory evidence"})
api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":c["sha"],"force":False},"PATCH")
print("RESEARCH_PUBLISHED "+c["sha"])
