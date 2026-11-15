"""Checkpoint only this Modal batch, using a durable expected branch head."""
import json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/modal_pair_001"
def api(path,payload=None,method=None):
 args=["gh","api",path]
 if payload is not None:args+=["--method",method or "POST","--input","-"]
 r=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(r.stdout)
repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-modal-003";marker=OUT/".publish-head";head=marker.read_text().strip() if marker.exists() else os.environ["GITHUB_SHA"]
assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
parent=api("repos/"+repo+"/git/commits/"+head);entries=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in OUT.rglob("*") if p.is_file() and p.suffix in [".json",".txt"]]
t=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries});c=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":t["sha"],"message":"Checkpoint bounded multi-family pair repair, exact refinements and independently verified best"})
api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":c["sha"],"force":False},"PATCH");marker.write_text(c["sha"]);print("MODAL_PAIR_PUBLISHED "+c["sha"])
