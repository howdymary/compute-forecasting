"""Publish complete, partial and gated categorical continuation outcomes without rewriting v19."""
import hashlib,json,os,pathlib,statistics
from compute_forecast.probability_v18 import digest,summarize
from compute_forecast.continuation_v21 import selection,expansion_gate
from compute_forecast.quantile_v20 import decompose
from compute_forecast.verify_continuation_v21 import verify
from compute_forecast.train_market_v19 import write
def read(p):return json.loads(pathlib.Path(p).read_bytes())
p=read("configs/ce-continuation-v21.json");parent=read(p["parent"]["report_path"]);pre=pathlib.Path("artifacts/ce-continuation-v21-preflight")
audit=read(pre/"audit.json");ready=read(pre/"readiness.json");models=pathlib.Path("artifacts/ce-continuation-v21-models");out=pathlib.Path("artifacts/ce-continuation-v21-public")
old=next(r for r in parent["runs"] if r["arm"]=="price" and r["seed"]==17)
retained={"development":{"label":"retained_canonical","cells":[r for c in parent["cases"] for cp in c["checkpoints"] if cp["arm"]=="price" and cp["seed"]==17 and cp["update"]==30 for r in cp["rows"]],"summary":old["selected"]["development"]},"retrospective":old["retrospective"]}
baseline=read(pre/"incumbent.json") if (pre/"incumbent.json").exists() else retained
runs=[];incomplete=[]
for arm in ("same","expanded"):
    for seed in (17,29,43):
        d=models/arm/str(seed)
        if (d/"result.json").exists():
            state=read(d/"result.json");assert state["status"]=="completed" and state["selected"]==selection(state["checkpoints"])
            runs.append({"state":state,"development":{str(c["update"]):read(d/("development-"+str(c["update"])+".json")) for c in state["checkpoints"]},"retrospective":read(d/"evaluation-selected.json")})
        elif (d/"progress.json").exists():incomplete.append(read(d/"progress.json"))
seed17=[r["state"] for r in runs if r["state"]["seed"]==17]
gate=expansion_gate(seed17,baseline["development"]["summary"]["primary_pinball"])
ens_pointer=read("results/quantile-training-v20/latest.json");ens_raw=pathlib.Path(ens_pointer["report_path"]).read_bytes();assert hashlib.sha256(ens_raw).hexdigest()==ens_pointer["report_sha256"]
ensembles=json.loads(ens_raw)["ensembles"]
cases=[]
for original in parent["cases"]:
    c={k:v for k,v in original.items() if k not in ("checkpoints","market_state","market_input_identity")}
    c["references"]={"frozen_parent":[r for r in baseline["development"]["cells"] if r["task_id"]==c["task_id"]],**{kind:[r for r in entry["cells"] if r["task_id"]==c["task_id"]] for kind,entry in ensembles["development"].items()}}
    c["checkpoints"]=[{"arm":run["state"]["arm"],"seed":run["state"]["seed"],"update":int(update),"selected":int(update)==run["state"]["selected"]["update"],"rows":[r for r in value["cells"] if r["task_id"]==c["task_id"]]} for run in runs for update,value in run["development"].items()];cases.append(c)
comparisons=[]
for run in runs:
    s=run["state"];comparisons.append({"arm":s["arm"],"seed":s["seed"],"reference":"incumbent","result":decompose(run["retrospective"]["cells"],baseline["retrospective"]["cells"])})
for seed in (17,29,43):
    a=next((r for r in runs if r["state"]["arm"]=="same" and r["state"]["seed"]==seed),None);b=next((r for r in runs if r["state"]["arm"]=="expanded" and r["state"]["seed"]==seed),None)
    if a and b:comparisons.append({"arm":"expanded","seed":seed,"reference":"same","result":decompose(b["retrospective"]["cells"],a["retrospective"]["cells"])})
expected=set(ready["arms"]);pilot_done={r["state"]["arm"] for r in runs if r["state"]["seed"]==17}==expected
operational=[{"arm":"incumbent","update":0,"checkpoint_id":p["parent"]["checkpoint_id"],"development_loss":baseline["development"]["summary"]["primary_pinball"]}]+[{"arm":r["state"]["arm"],"update":r["state"]["selected"]["update"],"checkpoint_id":r["state"]["selected"]["checkpoint_id"],"development_loss":r["state"]["selected"]["development"]["primary_pinball"]} for r in runs if r["state"]["seed"]==17]
primary=min(operational,key=lambda v:(v["development_loss"],{"incumbent":0,"same":1,"expanded":2}[v["arm"]]))
model_lock={"base_model":p["model"]["base"],"renderer":p["model"]["renderer"],"tokenizer_sha256":p["parent"]["tokenizer_sha256"],"log_levels":parent["log_levels"],"records":operational,"primary_arm":primary["arm"],"dataset_sha256":audit["dataset_sha256"],"protocol_sha256":digest(p),"identity_kind":"Hashes of immutable private checkpoint identities; not weight-byte checksums"} if pilot_done and ready["training_ready"] else None
status="completed_pilot" if pilot_done else "gated" if not ready["training_ready"] else "incomplete"
r={"study_id":p["study_id"],"status":status,"protocol":p,"protocol_sha256":digest(p),"parent_report_sha256":p["parent"]["report_sha256"],"log_levels":parent["log_levels"],"audit":audit,"readiness":ready,"baseline":baseline,"baseline_source":"Verified fresh restore" if (pre/"incumbent.json").exists() else "Retained canonical; restoration not verified","runs":runs,"incomplete_runs":incomplete,"expansion_gate":gate,"expansion_status":read("artifacts/ce-continuation-v21-expansion/gate.json") if pathlib.Path("artifacts/ce-continuation-v21-expansion/gate.json").exists() else {"status":"pending_registered_gate"},"ensembles":ensembles,"parent_development_pinball":baseline["development"]["summary"]["primary_pinball"],"parent_retrospective":baseline["retrospective"]["summary"],"comparisons":comparisons,"cases":cases,"controls":parent["controls"],"model_lock":model_lock,"future_protocol":read(p["future_protocol"]),"new_optimizer_updates":sum(v["state"]["optimizer_updates"] for v in runs),"uncompleted_confirmed_updates":sum(v.get("optimizer_updates",0) for v in incomplete),"prospective_accuracy":"not established","provider_cost_usd":None,"source_sha":os.environ.get("PUBLICATION_SOURCE_SHA",os.environ["GITHUB_SHA"]),"workflow_trigger_sha":os.environ["GITHUB_SHA"],"source_attribution":audit["source_attribution"],"limitations":p["limitations"]}
check=verify(r);write(out/"report.json",r);write(out/"verification.json",check)
lines=["# Categorical continuation v21 findings","","Post-event historical development and exploratory evaluation. Prospective improvement is not yet established.","","A is the frozen operational v19 price-only checkpoint30. B and C share that same initial weights and Adam state, unchanged19-level categorical output and CE objective, lower learning rate and additional update budget. B uses the original corpus; C uses the expanded corpus.","","| Corpus | Windows | Horizon examples | Groups | Providers | Origins | Changed7d windows |","|---|---:|---:|---:|---:|---:|---:|"]
for arm,v in audit["counts"].items():lines.append("| "+arm+" | "+str(v["windows"])+" | "+str(v["horizon_examples"])+" | "+str(v["groups"])+" | "+str(v["providers"])+" | "+str(len(v["origins"]))+" | "+str(v["changed_7d"])+" |")
lines+=["","Expanded-data readiness: "+str(audit["expanded_ready"])+". Reasons: "+json.dumps(audit["expanded_gate_reasons"])+". Actual selected training sources: "+json.dumps(audit["counts"]["expanded"]["sources"])+".","","| Arm | Ordering seed | Additional updates | Selected additional update | Dev7d loss | Exploratory7d loss | Coverage | Mean width |","|---|---:|---:|---:|---:|---:|---:|---:|"]
base=baseline["retrospective"]["summary"];lines.append("| incumbent | 17 parent | 0 | 0 | "+str(baseline["development"]["summary"]["primary_pinball"])+" | "+str(base["primary_pinball"])+" | "+str(base["by_horizon"]["7"]["coverage"])+" | "+str(base["by_horizon"]["7"]["width"])+" |")
for run in runs:
    s=run["state"];v=run["retrospective"]["summary"]["by_horizon"]["7"];lines.append("| "+s["arm"]+" | "+str(s["seed"])+" | "+str(s["optimizer_updates"])+" | "+str(s["selected"]["update"])+" | "+str(s["selected"]["development"]["primary_pinball"])+" | "+str(v["pinball"])+" | "+str(v["coverage"])+" | "+str(v["width"])+" |")
lines+=["","Development expansion gate: "+json.dumps(gate)+". This is an engineering screen, not statistical evidence.","","Only saved development checkpoints select candidates. Exploratory results cover24 seven-day cases on three reused, dependent dates. Seeds share market outcomes. A continuation gain does not isolate learning rate; an expanded-data gain does not isolate sample count from changed corpus composition.","","All original training tasks and evaluation cases are preserved. New examples are not independent market experiments; overlap, repeated flat contexts and source variation remain explicit in audit.json.","","The operational future candidate is chosen using development scores, with ties retaining the incumbent. Existing panels and gates remain unchanged. Full future probability vectors require compatible fresh source observations and verified pre-resolution publication.","","Public arithmetic: python -m compute_forecast.verify_continuation_v21. See docs/ce-continuation-v21.md."]
(out/"findings.md").write_text("\n".join(lines)+"\n");print(json.dumps(check))
