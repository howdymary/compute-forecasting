"""Publish only CodeGarden closeout artifacts after all workers have finished."""
import json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase2"
def api(path,payload=None,method=None):
 args=["gh","api",path]
 if payload is not None:args+=["--method",method or "POST","--input","-"]
 r=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True)
 return json.loads(r.stdout)
repo=os.environ["GITHUB_REPOSITORY"];head=os.environ["SOURCE_SHA"]
assert api("repos/"+repo+"/git/ref/heads/codegarden")["object"]["sha"]==head
parent=api("repos/"+repo+"/git/commits/"+head)
paths=[p for p in OUT.rglob("*") if p.is_file() and p.suffix in [".json",".txt",".csv",".svg"]]
paths += [ROOT/"artifacts/final_verification.json",ROOT/"budget/phase2-usage-summary.json",ROOT/"budget/historical-usage.json"]
paths += [p for p in (ROOT/"demo").glob("*") if p.is_file() and p.suffix in [".json",".html",".svg"]]
entries=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in sorted(set(paths)) if p.exists()]
tree=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries})
commit=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":tree["sha"],"message":"Publish final CodeGarden phase-two independent checks, resource curves, demo and conservative accounting"})
api("repos/"+repo+"/git/refs/heads/codegarden",{"sha":commit["sha"],"force":False},"PATCH")
print("FINAL_PUBLISHED "+json.dumps({"sha":commit["sha"],"files":len(entries)}))
