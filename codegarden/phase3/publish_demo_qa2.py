"""Publish only this QA evidence, including real browser screenshots."""
import base64,json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/demo_qa_004"
def api(path,payload=None,method=None):
 args=["gh","api",path]
 if payload is not None:args+=["--method",method or "POST","--input","-"]
 r=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(r.stdout)
OUT.mkdir(parents=True,exist_ok=True)
if not (OUT/"report.json").exists():(OUT/"setup_failure.json").write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"browser_checks_completed":False,"success_claim":False,"reason":"Browser QA did not finish; inspect this run logs. No mathematical result inferred."},indent=2))
repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-demo-qa-004";head=os.environ["GITHUB_SHA"];assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head;parent=api("repos/"+repo+"/git/commits/"+head);entries=[]
for p in sorted(OUT.rglob("*")):
 if not p.is_file() or p.suffix not in [".json",".txt",".png"]:continue
 entry={"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob"}
 if p.suffix==".png":entry["sha"]=api("repos/"+repo+"/git/blobs",{"content":base64.b64encode(p.read_bytes()).decode(),"encoding":"base64"})["sha"]
 else:entry["content"]=p.read_text()
 entries.append(entry)
tree=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries});commit=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":tree["sha"],"message":"Verify recorded demo in real desktop/mobile browser, decode ten examples and independently check downloaded witness"})
api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":commit["sha"],"force":False},"PATCH");print("DEMO_QA_PUBLISHED",commit["sha"])
