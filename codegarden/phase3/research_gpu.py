"""Three separate frozen model contexts use real cross-role memory and Exa before a profiled experiment."""
import datetime as dt,hashlib,json,os,pathlib,subprocess,sys,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"phase2"))
from providers import Providers,http,cli
from phase2.role import recalled
from phase2.model_policy import Policy
from phase3.research3 import read
from supervisor import verify,check_integrity
OUT=ROOT/"artifacts/phase3/research_gpu_001";OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2))
def publish():subprocess.run([sys.executable,"-B",str(ROOT/"phase3/publish_research_gpu.py")],check=True)
def main():
 check_integrity();previous=read("codegarden/artifacts/phase3/long_diversification_001/status.json","codegarden-modal-009")
 assert previous["status"] in ["completed","failed_or_partial"]
 if previous.get("best_verified",0)>=227:
  save("status.json",{"status":"skipped_previous_target_reached","previous":previous,"new_provider_calls":0});publish();return
 history={"source_run":"after-long-"+previous["source_sha"],"conservative_totals":{p:v["reserved"]+v["provider_reported_or_estimated"] for p,v in previous["budget"].items()},"reason":"All historical holds retained, including complete long reservation and its retry-aware concurrency envelope."}
 for name in ["status.json","ledger_progress.json"]:
  try:
   own=read("codegarden/artifacts/phase3/research_gpu_001/"+name,"codegarden-research-gpu-003");data=own.get("budget",own)
   for p,v in data.items():
    if isinstance(v,dict) and "reserved" in v:history["conservative_totals"][p]=max(history["conservative_totals"].get(p,0),v["reserved"]+v["provider_reported_or_estimated"])
  except Exception:pass
 (ROOT/"budget/historical-usage.json").write_text(json.dumps(history,indent=2))
 spec=json.loads((ROOT/"budget/shared-allocation.json").read_text());spec["providers"]["modal"]["codegarden_cap"]=150
 gross=float(json.loads(cli("modal","billing","summary","--json"))["metered_cost"]);floor=248.87-max(0,gross-1.64005948);assert floor>=245,"Full other-project and verification guards unavailable"
 spec["providers"]["past"]["balance_at_snapshot"]=http("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"])["balance"]["left"];(ROOT/"budget/shared-allocation.json").write_text(json.dumps(spec,indent=2))
 events=[];p=None;status={"status":"running","source_sha":os.environ["GITHUB_SHA"],"started_at":dt.datetime.now(dt.timezone.utc).isoformat(),"history":history,"credit_floor":floor}
 def log(kind,value):
  safe=json.loads(json.dumps(value))
  if kind=="exa_search":
   for s in safe.get("sources",[]):s.pop("excerpt",None)
  events.append({"kind":kind,"value":safe});save("provider_trace.json",events)
  if p:save("ledger_progress.json",p.ledger.summary())
 try:
  p=Providers(OUT,log);p.setup_memory();policy=Policy(p.ledger)
  facts={"primary_best_verified":226,"target":227,"closed_root_radius":9,"known226_common_core":216,
   "hard_csp_unknown":128,"tensor_projection":"First CPU archive contained only recoveries of known226; quota206 is an explicitly restricted diversification heuristic, not a validity rule.",
   "experiments":"No new verified227. Exact, tensor and valid-packing methods have distinct resource budgets. Positive-energy227 states are invalid.",
   "training_gate":"No new adaptation dataset with verified primary gains; use frozen proposals, retain previous tied/negative Tinker evaluation."}
  previous_memory=recalled(p.read("analyst","Recall CodeGarden connected_reverse_search_context and its connected neighborhood and primitive bridge findings.","codegarden-43694919468-researcher-connected_reverse_search_context-ec179f25"),"codegarden-43694919468-researcher-connected_reverse_search_context-ec179f25")
  save("analyst_recall.json",previous_memory)
  diagnosis=policy.choose({"role":"analyst","verified_local_artifact_facts":facts,"actual_other_role_memory":previous_memory},["diversity","penalties"])
  assert diagnosis["valid_action"];analyst=p.write("analyst","tensor_plateau_diagnosis",{"facts":facts,"separate_model_context":diagnosis,"actual_other_role_memory":previous_memory},"research-gpu")
  recall1=recalled(p.read("researcher","Recall tensor_plateau_diagnosis, primary_best_verified, hard_csp_unknown and the separate model context diagnosis.",analyst),analyst);save("researcher_recall.json",recall1)
  query_decision=policy.choose({"role":"researcher","actual_analyst_memory":recall1,"budget":"One targeted external-method query and one current-record query"},["overlap","breakout"]);assert query_decision["valid_action"]
  query={"overlap":"maximum independent set diverse solutions incumbent overlap constraints local search","breakout":"maximum independent set dynamic local search weighted penalties breakout GPU"}[query_decision["action"]]
  evidence=[]
  for q in [query,"binary two deletion correcting codes length16 226 227 explicit construction 2026"]:
   r=p.exa(q,"profiled-core-quota-tensor")
   for s in r["sources"]:s.pop("excerpt",None)
   evidence.append(r);save("searches.json",evidence)
  researcher=p.write("researcher","tensor_method_context",{"query_decision":query_decision,"actual_analyst_recall":recall1,"sources":evidence,
   "extracted_method":"Use diversity/overlap restrictions and dynamic penalties as experimental escape mechanisms; retain the full word universe and independent positive verification. Sparse all-word derivatives are an implementation experiment, not a coding theorem."},"research-gpu",[analyst])
  recall2=recalled(p.read("strategist","Recall tensor_method_context, query_decision, source-backed escape methods and core overlap quotas.",researcher),researcher);save("strategist_recall.json",recall2)
  choice=policy.choose({"role":"strategist","actual_researcher_memory":recall2,"facts":facts,"allowed_quotas":{"quota206":"Remove at least10 of216 common-core words in constrained replicas","quota196":"Remove at least20 common-core words"},"budget":"CPU/GPU matched kernel profile first; at most900 GPU search seconds only if measured advantage>=1.5; full conditional reservation0.868USD"},["quota206","quota196"]);assert choice["valid_action"]
  quota=int(choice["action"].removeprefix("quota"));save("strategy_decision.json",choice)
  strategy=p.write("strategist","selected_tensor_experiment",{"decision":choice,"actual_other_role_memory":recall2,"source_program":os.environ["GITHUB_SHA"]},"research-gpu",[researcher]);publish()
  from phase3.gpu_batch import run as gpu_run
  result=gpu_run(p.ledger,OUT,os.environ["GITHUB_SHA"],quota,publish);best=226
  if result.get("host_independent_verification"):best=result["host_independent_verification"]["cardinality"]
  if (OUT/"tensor_result.json").exists() and best<227:
   from phase3.project_tensor3 import project
   projections=project(OUT/"tensor_result.json",OUT/"projections");best=max(best,projections["best_independently_verified"]);publish()
   if best<227:
    from phase3.polish_tensor import run
    best=max(best,run(OUT)["best_verified"]);publish()
  gate="primary_best_verified" in json.dumps(recall1["actual_content"]) and "query_decision" in json.dumps(recall2["actual_content"])
  status.update(status="completed",best_verified=best,source_ids=[analyst,researcher,strategy],memory_content_gate=gate,
   role_execution="Three separately prompted frozen Tinker sampling contexts in one serialized coordinator; not assistant subagents or a parallel swarm",new_training=False,gpu_result=result)
 except Exception as e:status.update(status="failed_or_partial",error=str(e)[:1200]);traceback.print_exc()
 finally:
  status.update(budget=p.ledger.summary() if p else None,finished_at=dt.datetime.now(dt.timezone.utc).isoformat());save("status.json",status);publish();print("RESEARCH_GPU_FINAL",json.dumps(status),flush=True)
if __name__=="__main__":main()
