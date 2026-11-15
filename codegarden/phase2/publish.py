"""Publish only phase-two outputs, with a durable lease across checkpoints."""
import json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase2"
def api(path,payload=None,method=None):
 args=["gh","api",path]
 if payload is not None:args+=["--method",method or "POST","--input","-"]
 p=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True)
 return json.loads(p.stdout)
def main():
 repo=os.environ["GITHUB_REPOSITORY"];marker=OUT/".publish-head"
 expected=marker.read_text().strip() if marker.exists() else os.environ["SOURCE_SHA"]
 ref=api("repos/"+repo+"/git/ref/heads/codegarden")
 if ref["object"]["sha"]!=expected:raise RuntimeError("CodeGarden branch moved outside this checkpoint sequence")
 parent=api("repos/"+repo+"/git/commits/"+expected)
 paths=list(OUT.rglob("*.json"))+list(OUT.rglob("*.txt"))
 paths=[p for p in paths if p.name!="environment.txt"]+[ROOT/"budget/shared-allocation.json"]
 entries=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in sorted(set(paths))]
 t=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries})
 c=api("repos/"+repo+"/git/commits",{"parents":[expected],"tree":t["sha"],"message":"Checkpoint bounded CodeGarden phase-two experiments and independent verification"})
 api("repos/"+repo+"/git/refs/heads/codegarden",{"sha":c["sha"],"force":False},"PATCH")
 marker.write_text(c["sha"]);print(json.dumps({"published_head":c["sha"],"phase2_files":len(entries)}))
if __name__=="__main__":main()
