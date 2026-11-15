"""Serialized recovery of the incomplete memory-only ablation; no search or training."""
import datetime as dt,json,os,pathlib,subprocess,sys,traceback
from common import *
from providers import Providers
from model_policy import Policy
from memory_benchmark import run
DEST=OUT/"supplement/memory_recovery";DEST.mkdir(parents=True,exist_ok=True)
def api(path,payload=None,method=None):
 args=["gh","api",path]
 if payload is not None:args+=["--method",method or "POST","--input","-"]
 r=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(r.stdout)
def main():
 prior=json.loads((OUT/"supplement/status.json").read_text());assert prior["finished_at"]
 (ROOT/"budget/historical-usage.json").write_text(json.dumps({"source_run":"supplement-before-memory-recovery-"+prior["source_sha"],
  "conservative_totals":{p:v["reserved"]+v["provider_reported_or_estimated"] for p,v in prior["budget"].items()},
  "reason":"Carry all cumulative completed and failed supplemental holds before memory-only recovery."}))
 events=[]
 def log(kind,value):events.append({"kind":kind,"value":value});(DEST/"provider_trace.json").write_text(json.dumps(events,indent=2))
 p=Providers(DEST,log);p.setup_memory();status={"source_sha":os.environ["GITHUB_SHA"],"status":"running",
  "reason":"Original comparison completed, then required-source recall failed during separate memory benchmark.",
  "changed_method":"Use original analyst root-result source, not the semantically less relevant dominant-operator source; preserve the initial failure."}
 try:
  source=json.loads((OUT/"roles/analyst_root_output.json").read_text())["source_id"]
  facts=json.loads((OUT/"roles/analyst_root_input.json").read_text())["content"]
  manifest=json.loads((OUT/"frozen_cases.json").read_text())
  result=run(Policy(p.ledger),p,source,facts,manifest)
  status["status"]="completed";status["summary"]=result["summary"]
 except Exception as e:status.update({"status":"failed_or_partial","error":str(e)[:500]});traceback.print_exc()
 finally:
  for name in ["memory_benchmark.json","memory_benchmark_progress.json"]:
   if (OUT/name).exists():(OUT/name).replace(DEST/name)
  status["budget"]=p.ledger.summary();status["finished_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
  (DEST/"status.json").write_text(json.dumps(status,indent=2))
  repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-policy-control";head=os.environ.get("SOURCE_SHA",os.environ["GITHUB_SHA"])
  assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
  parent=api("repos/"+repo+"/git/commits/"+head)
  entries=[{"path":str(file.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":file.read_text()} for file in DEST.rglob("*.json")]
  t=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries})
  c=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":t["sha"],"message":"Preserve failed recall and record serialized memory-only recovery with cumulative reservations"})
  api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":c["sha"],"force":False},"PATCH")
  print("MEMORY_RECOVERY "+json.dumps(status),flush=True)
if __name__=="__main__":main()
