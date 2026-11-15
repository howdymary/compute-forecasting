"""Publish a CPU-only independent audit to its isolated scratch branch."""
import json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
def api(path,payload=None,method=None):
 args=["gh","api",path]
 if payload is not None:args+=["--method",method or "POST","--input","-"]
 r=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True)
 return json.loads(r.stdout)
repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-radius34";head=os.environ["SOURCE_SHA"]
assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
parent=api("repos/"+repo+"/git/commits/"+head)
p=ROOT/"artifacts/phase2/conflict_repairs/independent_audit.json"
t=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()}]})
c=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":t["sha"],"message":"Independently reconstruct all 512 full candidate pools and verify their repair bounds"})
api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":c["sha"],"force":False},"PATCH")
print("AUDIT_PUBLISHED "+c["sha"])
