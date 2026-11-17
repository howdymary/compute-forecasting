"""Reconstruct public v19 arithmetic from permitted retained outputs."""
import hashlib,json,os,pathlib,statistics
from compute_forecast.probability_v18 import digest,summarize,quantiles
from compute_forecast.direct_forecast_v12 import cell_loss
root=pathlib.Path("artifacts/market-state-v19-public");root.mkdir(parents=True,exist_ok=True)
def read(path):return json.loads(pathlib.Path(path).read_bytes())
p=read("configs/market-state-v19.json");future=read("configs/market-state-v19-prospective.json")
audit=read("inputs/market-state-v19/audit.json");data=read("inputs/market-state-v19/dataset.json");assert audit["dataset_sha256"]==digest(data) and audit["training_ready"]
controls=read("artifacts/market-state-v19-controls/controls.json");assert controls["dataset_sha256"]==digest(data)
base=read("artifacts/market-state-v19-base/base.json");runs=[];cases={}
for t in sorted(data["groups"]["development"],key=lambda x:(x["origin"],x["series_id"])):
    cases[t["task_id"]]={"task_id":t["task_id"],"origin":t["origin"],"metadata":t["metadata"],"history":t["context"],"market_state":t["market_state"],"market_input_identity":t["market_input_identity"],"target_dates":t["target_dates"],"outcomes":t["outcomes"],"checkpoints":[]}
for arm in ("price","market"):
    for seed in (17,29,43):
        directory=pathlib.Path("artifacts/market-state-v19-models")/arm/str(seed);state=read(directory/"result.json");selection=read(directory/"selection.json")
        assert state["status"]=="completed" and state["dataset_sha256"]==digest(data) and state["arm"]==arm and state["seed"]==seed
        assert state["selected"]==selection["selected"]
        assert state["selected"]==min(state["checkpoints"],key=lambda x:(x["development"]["primary_pinball"],x["update"]))
        evaluation=read(directory/"evaluation-selected.json")
        for cp in state["checkpoints"]:
            dev=read(directory/("development-"+str(cp["update"])+".json"))
            assert summarize(dev["cells"])==cp["development"]
            for task_id,c in cases.items():
                rows=[r for r in dev["cells"] if r["task_id"]==task_id];assert len(rows)==3
                c["checkpoints"].append({"arm":arm,"seed":seed,"update":cp["update"],"selected":cp["update"]==state["selected"]["update"],"rows":rows})
        runs.append({"arm":arm,"seed":seed,"source_sha":state["source_sha"],"optimizer_updates":state["optimizer_updates"],"example_presentations":state["example_presentations"],"max_prompt_tokens":state["max_prompt_tokens"],"training_windows":state["training_windows"],"training_horizon_examples":state["training_horizon_examples"],"batch_order_sha256":state["batch_order_sha256"],"elapsed_seconds":state["elapsed_seconds"],"selected":state["selected"],"checkpoints":state["checkpoints"],"retrospective":evaluation,"untuned":base[arm]["retrospective"],"tokenizer":state["tokenizer"],"model":state["model"],"provider_cost_usd":state["provider_cost_usd"]})
for seed in (17,29,43):
    a,b=[next(r for r in runs if r["seed"]==seed and r["arm"]==arm) for arm in ("price","market")]
    assert a["batch_order_sha256"]==b["batch_order_sha256"] and a["optimizer_updates"]==b["optimizer_updates"]
    assert {(r["task_id"],r["horizon_days"]) for r in a["retrospective"]["cells"]}=={(r["task_id"],r["horizon_days"]) for r in b["retrospective"]["cells"]}
comparison=[]
for seed in (17,29,43):
    a,b=[next(r for r in runs if r["seed"]==seed and r["arm"]==arm) for arm in ("price","market")]
    comparison.append({"seed":seed,"price_pinball":a["retrospective"]["summary"]["primary_pinball"],"market_pinball":b["retrospective"]["summary"]["primary_pinball"],"market_minus_price":b["retrospective"]["summary"]["primary_pinball"]-a["retrospective"]["summary"]["primary_pinball"]})
operational=[r for r in runs if r["seed"]==17]
engine=digest({name:hashlib.sha256(pathlib.Path("src/compute_forecast") .joinpath(name).read_bytes()).hexdigest() for name in ("market_future_remote_v19.py","market_future_v19.py","market_analysis_v19.py","market_controls_v19.py","market_state_v19.py","probability_v18.py")})
lock={"future_engine_sha256":engine,"analysis_plan_sha256":hashlib.sha256(pathlib.Path("configs/market-state-v19-analysis.json").read_bytes()).hexdigest(),"base_model":p["model"]["base"],"renderer":p["model"]["renderer"],"tokenizer_sha256":runs[0]["tokenizer"]["backend_sha256"],"log_levels":data["log_levels"],"protocol_sha256":digest(p),"dataset_sha256":digest(data),"records":[{"arm":r["arm"],"seed":17,"selected_update":r["selected"]["update"],"checkpoint_id":r["selected"]["checkpoint_id"]} for r in operational]}
key=read("inputs/market-state-v19/input-key.json")["private_key"]
report={"study_id":"market-state-v19","status":"completed_retrospective_pending_future","protocol":p,"protocol_sha256":digest(p),"audit":audit,"log_levels":data["log_levels"],"runs":runs,"comparison":comparison,"controls":controls,"cases":list(cases.values()),"case_selection":"All development cases in origin/series order, default first; independent of performance","model_lock":lock,"numerical_lock":{"input_key":key,"state_sha256":controls["numerical_state_sha256"]},"future_protocol":future,"prospective_accuracy":"not established","source_attribution":"Pacific Machines (2026), gpu-price-pack v0.1.1-handover, CC BY 4.0 compilation. GPU Price Tracker component, CC BY 4.0. Current continuing quotes: GPU Rental Prices, CC BY 4.0.","limitations":["Reused, dependent historical dates; no prospective accuracy claim","Source-reported historical snapshot timing, not independent publication-vintage evidence","New provider/configuration group medians, different from official targets and future individual contracts","No usable matching-region/node dollar ratios in this training cohort","News, availability, BLS and infrastructure excluded from this comparison"],"workflow_receipt":read("training-workflow-receipt.json"),"new_optimizer_updates":sum(r["optimizer_updates"] for r in runs),"provider_cost_usd":None}
(root/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
lines=["# Market-state v19 findings","","Retrospective direct forecasting comparison; prospective accuracy is not established.","",f"Training: {audit['phases']['training']['windows']} overlapping windows; {report['new_optimizer_updates']} actual optimizer updates across six runs.","","| Seed | Price-only seven-day pinball | Market context | Market minus price |","|---|---:|---:|---:|"]
for c in comparison:lines.append(f"| {c['seed']} | {c['price_pinball']:.9f} | {c['market_pinball']:.9f} | {c['market_minus_price']:+.9f} |")
lines+=["","Lower pinball is better. Seeds share the same market outcomes and are not independent market tests.",f"Retrospective scope: {audit['phases']['retrospective']['windows']} seven-day cases, three reused dependent origins. Twelve training groups; eight eligible evaluation groups.","","Only observed other-provider price changes and collection composition were tested. No evidence of news or availability value follows.","","The separate contract-transfer panel starts no earlier than December 20, 2026, uses 16 weekly origins, and has an April 12, 2027 analysis gate.","","The experiment is running; prospective improvement is not yet established."]
(root/"findings.md").write_text("\n".join(lines)+"\n")
print(json.dumps({"updates":report["new_optimizer_updates"],"comparison":comparison,"model_lock_sha256":digest(lock)}))
