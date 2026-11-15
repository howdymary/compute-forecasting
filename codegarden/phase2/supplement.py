"""Preregistered supplemental control: train-selected fixed operator versus frozen proposers.

No new fine-tuning. Provider usage is serialized after the main campaign by the
same Actions concurrency group; its final cumulative reservations are imported.
"""
import base64,datetime as dt,hashlib,json,os,pathlib,subprocess,sys,time,traceback,uuid
from common import *
from providers import Providers,Ledger
from role import recalled
from integrations.tinker_policy import Policy as LegacyPolicy,MODEL,encode_prompt
MAPPING={"random8greedy":1,"random16greedy":0,"structural24greedy":3,"opportunity12exact":4,
 "random24exact":4,"conflict8exact":2,"random40greedy":5,"structural48exact":3,"opportunity6ejection":2}
CONTROL=OUT/"supplement";CONTROL.mkdir(parents=True,exist_ok=True)
def api(path,payload=None,method=None):
 args=["gh","api",path]
 if payload is not None:args+=["--method",method or "POST","--input","-"]
 p=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True)
 return json.loads(p.stdout)
def main_file(path):
 result=api("repos/"+os.environ["GITHUB_REPOSITORY"]+"/contents/"+path+"?ref=codegarden")
 return json.loads(base64.b64decode(result["content"]))
def write(name,value):
 p=CONTROL/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2));return p
class ProposalLedger:
 def __init__(self,ledger):self.ledger=ledger
 def reserve(self,provider,project,amount):
  assert provider=="tinker" and amount==1
  # Legacy policy enforces <=2048 input and <=64 output tokens; verified 4B
  # upper token cost is <.00075 USD. Keep .05 unresolved per call.
  return self.ledger.reserve(provider,project,.05)
 def settle(self,*args):return self.ledger.settle(*args)
def main():
 import modal,tinker
 main_status=main_file("codegarden/artifacts/phase2/campaign_status.json")
 if not main_status.get("finished_at"):raise RuntimeError("Main campaign has not finished; no shared provider spending allowed")
 history={"source_run":"main-phase2-"+main_status["source_sha"],"conservative_totals":
  {p:d["reserved"]+d["provider_reported_or_estimated"] for p,d in main_status["budget"].items()},
  "reason":"Carry every cumulative main-campaign hold and charge into serialized supplemental evaluation."}
 (ROOT/"budget/historical-usage.json").write_text(json.dumps(history))
 ledger=Ledger(CONTROL);events=[]
 def log(kind,value):events.append({"kind":kind,"value":value,"time":time.time()});write("provider_trace.json",events)
 p=Providers(CONTROL,log);p.setup_memory()
 status={"status":"running","source_sha":os.environ["GITHUB_SHA"],"main_finished_at":main_status["finished_at"],
  "new_training":False,"checkpoint_origin":"phase-one trained sampler; new phase-two training gate rejected conditional learning"}
 active=[]
 try:
  manifest=json.loads((OUT/"frozen_cases.json").read_text());training=json.loads((OUT/"training_cases.json").read_text())
  # Exclude the close 225-word lineage from fixed-baseline selection. Threshold
  # and exclusion were preregistered before this study's held-out measurements.
  usable=[e for e in training["examples"] if "225" not in e["family"]]
  totals=[sum(e["scores"][a]["size"] for e in usable) for a in range(6)]
  selected=max(range(6),key=lambda a:(totals[a],-a));assert selected==4
  facts={"selected_fixed_operator":ACTIONS[selected],"training_scores_by_operator":dict(zip(ACTIONS,totals)),
   "selection_cases":len(usable),"excluded_related_lineage":"arena_225_lobster-boy",
   "training_gate":training["gate"],"interpretation":"One fixed operator is supported; do not fabricate a state-dependent fine-tuning target.",
   "root_exchanges":[{k:r[k] for k in ["k","status","complete","incumbent_sha256","candidate_universe_sha256","restrictions"]} for r in json.loads((OUT/"root_sweeps.json").read_text())],
   "global_cp":{"status":"UNKNOWN","target":227,"meaning":"No impossibility conclusion"}}
  source=p.write("analyst","dominant_operator_finding",facts,"phase2-supplement")
  actual=recalled(p.read("strategist","Recall the analyst's dominant fixed-operator finding and the failed conditional-learning gate.",source),source)
  # All model conditions share the legacy prompt/action space and the same
  # explicitly declared mapping into the new compiled operators.
  expected=json.loads((ROOT/"artifacts/live/training.json").read_text())["checkpoint_sha256"]
  service=tinker.ServiceClient(display_name="CodeGarden supplemental checkpoint lookup")
  rest=service.create_rest_client();path=None
  for offset in [0,100]:
   runs=rest.list_training_runs(limit=100,offset=offset).result().training_runs
   for run in runs:
    cp=run.last_sampler_checkpoint
    if cp and hashlib.sha256(cp.tinker_path.encode()).hexdigest()==expected:path=cp.tinker_path;break
   if path or len(runs)<100:break
  if not path:raise RuntimeError("The pinned historical sampler is unavailable; do not replace it with a different checkpoint")
  proxy=ProposalLedger(ledger);base=LegacyPolicy(proxy);trained=LegacyPolicy(proxy,path)
  compact={"actual_memory_source":actual["source_id"],"recalled_content_sha256":actual["content_sha256"],
    "actual_recalled_content":actual["actual_content"]}
  if len(json.dumps(compact))>4000:raise ValueError("Recall too long for comparable legacy context")
  conditions=["strong_fixed","untrained_no_external","untrained_with_memory","historical_trained_with_memory"]
  held=[c for c in manifest["cases"] if c["split"]=="heldout"];assert len(held)==8
  protocol={"conditions":conditions,"cases":[{"id":c["case_id"],"starting_sha256":c["starting_sha256"]} for c in held],
   "cpu_seconds_per_case":20,"seed_rule":"case.seed*10","fixed_operator_selected_on_24_training_cases":ACTIONS[selected],
   "excluded_close_lineage_jaccard":.714828897338403,"same_model_prompts_and_action_mapping":MAPPING,
   "new_training":False,"historical_checkpoint_sha256":expected,"monetary_caps_per_condition":{"modal_usd":2,"tinker_usd":2},
   "order":"Rotate condition submission order by case index; paired seed and starting code",
   "limitation":"A single experiment-level operator selection, not a test of within-episode neighborhood switching"}
  write("protocol.json",protocol)
  ledger.reserve("modal","codegarden",1)
  image=modal.Image.debian_slim(python_version="3.11").apt_install("g++")
  for rel in ["kernel.cpp","phase2/kernel_v2.cpp"]:image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel,copy=True)
  image=image.run_commands("g++ -O3 -std=c++17 /opt/codegarden/phase2/kernel_v2.cpp -o /opt/codegarden/kernel_v2")
  for rel in ["protected/verify_descendants.py","protected/verify_lcs.py"]:image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
  app=modal.App("codegarden-phase2-supplement",tags={"project":"codegarden","campaign":"phase2-control"})
  volume=modal.Volume.from_name("codegarden-phase2-control-checkpoints",create_if_missing=True)
  @app.function(serialized=True,image=image,cpu=1,memory=768,timeout=90,max_containers=4,volumes={"/codegarden/results":volume})
  def worker(words,seed,arm,tag):
   import importlib.util
   path=pathlib.Path("/codegarden/results")/uuid.uuid4().hex;path.mkdir()
   meta={"seed":seed,"arm":arm,"tag":tag,"cpu_seconds_cap":20,"starting_words":words}
   (path/"metadata.json").write_text(json.dumps(meta));volume.commit()
   started=time.perf_counter()
   process=subprocess.run(["/opt/codegarden/kernel_v2","20",str(seed),"fixed",str(path/"checkpoint.txt"),"227",str(arm)],
    input="\n".join(words)+"\n",text=True,capture_output=True,timeout=65,check=True)
   r=json.loads(process.stdout);final=[format(w,"016b") for w in r["best"]]
   def module(name,rel):
    spec=importlib.util.spec_from_file_location(name,"/opt/codegarden/"+rel);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
   D=module("control_desc","protected/verify_descendants.py");L=module("control_lcs","protected/verify_lcs.py")
   r["verification"]={"descendant":D.verify(final),"lcs":L.verify(final)};assert all(v["valid"] for v in r["verification"].values())
   r["words"]=final;r["runtime_seconds"]=time.perf_counter()-started;r["durable_path"]=str(path)
   (path/"result.json").write_text(json.dumps(r));(path/"witness.txt").write_text("\n".join(sorted(final))+"\n");volume.commit()
   for key in ["archive","current","current_words"]:r.pop(key,None)
   return r
  rows=[]
  with app.run():
   ledger.reserve("modal","codegarden",32*20*.002);jobs=[]
   for i,case in enumerate(held):
    order=conditions[i%4:]+conditions[:i%4]
    for condition in order:
     s=state(case["starting_words"],case["state"]["recent_verified_results"],case["state"]["stagnation_cpu_seconds"],20)
     s["incumbent_sha256"]=case["starting_sha256"];s["compiled_backend_mapping"]=MAPPING
     if condition in ["untrained_with_memory","historical_trained_with_memory"]:s["actual_recalled_finding"]=compact
     decision=None;arm=selected;t=time.perf_counter()
     if condition!="strong_fixed":
      model=trained if condition=="historical_trained_with_memory" else base
      decision=model.choose(s);decision["prompt_tokens"]=len(encode_prompt(model.tokenizer,s));arm=MAPPING[decision["action"]] if decision["valid_action"] else selected
     overhead=time.perf_counter()-t
     write("contexts/"+case["case_id"]+"_"+condition+".json",{"state":s,"decision":decision})
     call=worker.spawn(case["starting_words"],case["seed"]*10,arm,case["case_id"]+"-"+condition);active.append(call);jobs.append((case,condition,arm,decision,overhead,call))
   for case,condition,arm,decision,overhead,call in jobs:
    r=call.get(timeout=400);verification=check_words(r["words"],"supplement/worker_"+case["case_id"]+"_"+condition+".txt")
    row={"case_id":case["case_id"],"condition":condition,"starting_size":len(case["starting_words"]),"starting_sha256":case["starting_sha256"],
     "seed":case["seed"]*10,"arm":arm,"decision":decision,"controller_seconds":overhead,"result":r,"host_verification":verification}
    rows.append(row);write("progress.json",{"rows":rows})
  summary={c:{"cases":sum(r["condition"]==c for r in rows),"sum_best_sizes":sum(r["host_verification"]["cardinality"] for r in rows if r["condition"]==c),
   "search_cpu_seconds":sum(r["result"]["cpu_seconds"] for r in rows if r["condition"]==c),
   "controller_seconds":sum(r["controller_seconds"] for r in rows if r["condition"]==c),
   "valid_model_choices":sum(bool(r["decision"] and r["decision"]["valid_action"]) for r in rows if r["condition"]==c)} for c in conditions}
  write("evaluation.json",{"protocol":protocol,"rows":rows,"summary":summary})
  if before_cutoff():
   from model_policy import Policy
   from memory_benchmark import run
   memory=run(Policy(ledger),p,source,facts,manifest)
   for name in ["memory_benchmark.json","memory_benchmark_progress.json"]:
    (OUT/name).replace(CONTROL/name)
  status.update({"status":"completed","summary":summary,"historical_checkpoint_sha256":expected})
 except Exception as e:
  status.update({"status":"failed_or_partial","error_type":type(e).__name__,"error":str(e)[:700]});traceback.print_exc()
 finally:
  if status.get("status")!="completed":
   for call in active:
    try:call.cancel()
    except Exception:pass
  status["budget"]=ledger.summary();status["finished_at"]=dt.datetime.now(dt.timezone.utc).isoformat();write("status.json",status)
  repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-policy-control";head=os.environ["SOURCE_SHA"]
  assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
  parent=api("repos/"+repo+"/git/commits/"+head)
  entries=[{"path":str(file.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":file.read_text()} for file in list(CONTROL.rglob("*.json"))+list(CONTROL.rglob("*.txt"))]
  tree=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries});commit=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":tree["sha"],"message":"Record serialized supplemental controls using imported shared reservations and pinned historical checkpoint"})
  api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":commit["sha"],"force":False},"PATCH")
  print("SUPPLEMENT_FINAL "+json.dumps(status),flush=True)
if __name__=="__main__":main()
