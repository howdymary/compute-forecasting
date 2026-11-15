"""Continue actual Exa/past/Tinker evidence into a bounded profiled experiment.
Do not wait for optional memory ingestion before doing the mathematical experiment.
"""
import datetime as dt,hashlib,json,os,pathlib,subprocess,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"phase2"))
from providers import Providers,http,cli
from phase2.role import recalled
from phase2.model_policy import Policy
from phase3.research3 import read
from supervisor import check_integrity
OUT=ROOT/"artifacts/phase3/research_gpu_003";OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2))
def publish():subprocess.run([sys.executable,"-B",str(ROOT/"phase3/publish_research_gpu3.py")],check=True)
def main():
 check_integrity();up=read("codegarden/artifacts/phase3/research_gpu_002/status.json","codegarden-research-gpu-004");assert up["status"]=="failed_or_partial" and up["error"]=="Memory ingestion not ready"
 assert up["budget"]["modal"]["reserved"]==148.98,"No duplicated rights to a possibly already reserved Modal experiment"
 history={"source_run":"resume-memory-ingestion-"+up["source_sha"],"conservative_totals":{k:v["reserved"]+v["provider_reported_or_estimated"] for k,v in up["budget"].items()},"reason":"Preserve all failed/partial reservations and estimated memory ingestion credits. No prior Modal GPU reservation was made."}
 for name in ["status.json","ledger_progress.json"]:
  try:
   own=read("codegarden/artifacts/phase3/research_gpu_003/"+name,"codegarden-research-gpu-005");data=own.get("budget",own)
   for k,v in data.items():
    if isinstance(v,dict) and "reserved" in v:history["conservative_totals"][k]=max(history["conservative_totals"].get(k,0),v["reserved"]+v["provider_reported_or_estimated"])
  except Exception:pass
 (ROOT/"budget/historical-usage.json").write_text(json.dumps(history,indent=2));spec=json.loads((ROOT/"budget/shared-allocation.json").read_text());gross=float(json.loads(cli("modal","billing","summary","--json"))["metered_cost"]);floor=248.87-max(0,gross-1.64005948);assert floor>=245
 spec["providers"]["modal"]["codegarden_cap"]=150;spec["providers"]["past"]["balance_at_snapshot"]=http("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"])["balance"]["left"];(ROOT/"budget/shared-allocation.json").write_text(json.dumps(spec,indent=2))
 trace=[];p=None;status={"status":"running","source_sha":os.environ["GITHUB_SHA"],"started_at":dt.datetime.now(dt.timezone.utc).isoformat(),"history":history,"credit_floor":floor,"upstream_pending_ingestion":True}
 def log(kind,value):
  trace.append({"kind":kind,"value":value});save("provider_trace.json",trace)
  if p:save("ledger_progress.json",p.ledger.summary())
 try:
  p=Providers(OUT,log);p.setup_memory();evidence=read("codegarden/artifacts/phase3/research_gpu_002/searches.json","codegarden-research-gpu-004");save("upstream_exa_sources.json",evidence)
  attempts=[];memory=None
  preferred="codegarden-43707956052-researcher-tensor_method_context_v2-"
  for attempt in range(4):
   token=p.ledger.reserve("past","codegarden",1);result=http("https://api.past.dev/api/v1/recall",os.environ["PAST_API_KEY"],{"identity":p.actors["strategist"],"query":"Recall CodeGarden tensor_method_context_v2 source_review query_decision maximum independent set overlap constraints dynamic penalties and core quotas. Include source-backed phase3_deeper_method_research if the new ingestion is still pending.","maxTokens":4000});p.ledger.settle(token,1)
   ids=sorted({s["sourceId"] for r in result.get("results",[]) for s in r.get("sources",[])});attempts.append({"attempt":attempt,"actual_source_ids":ids,"actual_result":result});save("memory_attempts.json",attempts)
   sid=next((s for s in ids if s.startswith(preferred)),None)
   if sid is None:sid=next((s for s in ids if s.startswith("codegarden-") and "-researcher-" in s),None)
   if sid:
    memory=recalled(result,sid);save("strategist_recall.json",memory);log("memory_read",{"role":"strategist","returned_source_id":sid,"preferred_ingestion_returned":sid.startswith(preferred),"used_in_next_decision":True});break
   time.sleep(5)
  if memory is None:raise ValueError("No actual other-role researcher memory returned")
  policy=Policy(p.ledger);choice=policy.choose({"role":"strategist","actual_researcher_memory":memory,"actual_upstream_exa_sources":evidence,"primary_best_verified":226,"target":227,"closed_root_radius":9,"known226_common_core":216,"negative_evidence":"Fixed/adaptive penalties, event capture and32 larger-exchange trials found no new226. Pairwise portfolio unions are being exhausted.","allowed_quotas":{"quota206":"Constrained replicas retain at most206 shared-core words","quota196":"Constrained replicas retain at most196 shared-core words"},"budget":"Matched CPU/GPU profile; at most900 GPU search seconds if speedup>=1.5; reserve entire0.868USD conditional maximum"},["quota206","quota196"]);assert choice["valid_action"];save("strategy_decision.json",choice);save("ledger_progress.json",p.ledger.summary());publish()
  from phase3.gpu_batch2 import run
  gpu=run(p.ledger,OUT,os.environ["GITHUB_SHA"],int(choice["action"].removeprefix("quota")),publish);best=226
  if gpu.get("host_independent_verification"):best=gpu["host_independent_verification"]["cardinality"]
  if (OUT/"tensor_result.json").exists() and best<227:
   from phase3.project_tensor3 import project
   projections=project(OUT/"tensor_result.json",OUT/"projections");best=max(best,projections["best_independently_verified"]);publish()
   if best<227:
    from phase3.polish_tensor import run as polish
    best=max(best,polish(OUT)["best_verified"]);publish()
  status.update(status="completed",best_verified=best,gpu_result=gpu,new_training=False,actual_memory_source=memory["source_id"],memory_scope="Upstream researcher already read actual analyst findings and ran two real Exa queries. This strategist retrieved actual researcher memory; preferred-new versus older-returned source is recorded explicitly. No new claim of successful ingestion if not returned.")
 except Exception as e:status.update(status="failed_or_partial",error=str(e)[:1200]);traceback.print_exc()
 finally:
  status.update(budget=p.ledger.summary() if p else None,finished_at=dt.datetime.now(dt.timezone.utc).isoformat());save("status.json",status);publish();print("RESEARCH_GPU_CONTINUATION",json.dumps(status),flush=True)
if __name__=="__main__":main()
