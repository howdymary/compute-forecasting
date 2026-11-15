"""Publish only this free follow-up from its isolated branch."""
import json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/budget_inspect_002"
def api(path,payload=None,method=None):
 args=["gh","api",path]
 if payload is not None:args+=["--method",method or "POST","--input","-"]
 r=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(r.stdout)
repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-budget-inspect-004";head=os.environ["GITHUB_SHA"]
assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
parent=api("repos/"+repo+"/git/commits/"+head);entries=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in OUT.rglob("*") if p.is_file() and p.suffix in [".json",".txt"]]
t=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries});c=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":t["sha"],"message":"Record tested blocker-union augmentations and bounded neutral components"})
api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":c["sha"],"force":False},"PATCH");print("BUNDLE_PUBLISHED "+c["sha"])
