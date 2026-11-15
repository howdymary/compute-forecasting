"""Single final publisher for a free phase-three batch, with source-branch lease."""
import datetime as dt,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
def api(path,payload=None,method=None):
 args=["gh","api",path]
 if payload is not None:args+=["--method",method or "POST","--input","-"]
 r=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(r.stdout)
def main():
 out=ROOT/"artifacts/phase3"/os.environ.get("CODEGARDEN_BATCH","infeasible_probe_001");reports=[]
 for path in sorted(out.glob("probe_*/report.json")):reports.append(json.loads(path.read_text()))
 baseline=out/"preflight/baseline.txt";best=verify(baseline);bestpath=baseline
 for path in out.glob("probe_*/worker_valid_*.txt"):
  checked=verify(path)
  if checked["cardinality"]>best["cardinality"]:best=checked;bestpath=path
 summary={"finished_at":dt.datetime.now(dt.timezone.utc).isoformat(),"source_sha":os.environ["GITHUB_SHA"],"workers_complete":len(reports),
  "best_independently_verified":best,"best_witness_path":str(bestpath.relative_to(ROOT.parent)),
  "modes":{mode:{"cases":sum(r["mode"]==mode for q in reports for r in q["experiments"]),
   "min_pair_energy":min((r["minimum_pair_energy"] for q in reports for r in q["experiments"] if r["mode"]==mode),default=None),
   "iterations":sum(r["iterations"] for q in reports for r in q["experiments"] if r["mode"]==mode),
   "search_cpu_seconds":sum(r["search_cpu_seconds"] for q in reports for r in q["experiments"] if r["mode"]==mode)} for mode in ["tabu","breakout","anneal","hybrid"]},
  "warning":"Positive pair energy describes an invalid target-size state, never a code cardinality. No global record claim without a separate current-source comparison.",
  "provider_cost":0,"provider_calls":0}
 (out/"probe_summary.json").write_text(json.dumps(summary,indent=2))
 repo=os.environ["GITHUB_REPOSITORY"];head=os.environ.get("SOURCE_SHA",os.environ["GITHUB_SHA"])
 assert api("repos/"+repo+"/git/ref/heads/codegarden")["object"]["sha"]==head,"Branch moved; retain uploaded artifacts instead"
 parent=api("repos/"+repo+"/git/commits/"+head)
 entries=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in out.rglob("*") if p.is_file() and p.suffix in [".json",".txt"]]
 if best["cardinality"]>226:entries.append({"path":"codegarden/artifacts/best_code.txt","mode":"100644","type":"blob","content":bestpath.read_text()})
 tree=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries})
 commit=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":tree["sha"],"message":"Record new infeasible-space hypotheses with independently verified acceptance and explicit invalid diagnostics"})
 api("repos/"+repo+"/git/refs/heads/codegarden",{"sha":commit["sha"],"force":False},"PATCH")
 print("PHASE3_PUBLISHED "+json.dumps({"sha":commit["sha"],"best_verified":best["cardinality"],"modes":summary["modes"]}),flush=True)
if __name__=="__main__":main()
