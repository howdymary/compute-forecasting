"""Allowlisted public release built from actual, successful remote run artifacts."""
from __future__ import annotations
import argparse,hashlib,json,math,os
from datetime import datetime,timezone
from pathlib import Path
PACK_SHA="f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c"

def read_one(root,name):
    found=list(Path(root).rglob(name))
    if len(found)!=1:raise ValueError(f"Expected one {name}, found {len(found)}")
    return json.loads(found[0].read_text())

def pick(value,keys):return {k:value[k] for k in keys if k in value}

def public_trace(report):
    return {"policy":report["policy"],"traces":[{**pick(row,("origin","selected_config_id","revealed_configs","validation_loss","future_pinball","future_cells","trials")),"decisions":[pick(d,("step","selected_family_id","selected_config_id","family_selection_mode","parameter_selection_mode","runtime_seconds","revealed_validation_result")) for d in row.get("decisions",[])]} for row in report["traces"]]}

def build(root,sha):
    root=Path(root);policy=read_one(root/"policy","search-report.json")
    final=read_one(root/"final","final-report.json");freeze=read_one(root/"final","freeze-used.json")
    grid=read_one(root/"grid","representation-grid.json");memory=read_one(root/"memory","research-loop.json")
    export=read_one(root/"submission","export-report.json")
    baseline=read_one(root/"baseline","development-baseline-selection.json")
    if policy["code_sha"]!=freeze["policy_training_source_sha"] or policy["actual_training_updates"]!=50 or policy["epochs"]!=5:raise ValueError("Wrong trained study")
    if final["dataset_sha256"]!=PACK_SHA or not final["final_period_opened"] or final["training_updates"]!=0 or final["selected_checkpoint"]!=freeze["policy_checkpoint"]:raise ValueError("Wrong frozen final")
    if grid["final_period_opened"] or len(grid["origins"])!=26:raise ValueError("Wrong development grid")
    if memory["status"]!="completed" or memory["scope"]!="current_research" or not memory["actual_cross_agent_use"] or memory["historical_benchmark_input"]:raise ValueError("Unverified memory loop")
    events=[];authors={e["source_id"]:e["role"] for e in memory["events"] if e["event"]=="write"}
    for e in memory["events"]:
        item=pick(e,("event","role","source_id","required_source_id","returned_source_ids","used_memory_source_ids","selected_action","created_at","content_sha256"))
        if e["event"]=="read" and e["required_source_id"] not in e["returned_source_ids"]:raise ValueError("Unverified recall")
        if e["event"]=="write":
            record=e["record"];item.update(kind=record["kind"],parents=record["parent_record_ids"])
            content=record["content"]
            numerical=content.get("numerical_result",content)
            item["summary"]=pick(content,("hypothesis","objection_id","criticism","selected_action","used_criticism_source_id"))
            if numerical.get("tool")=="completed_forecast_experiment":
                item["experiment"]=pick(numerical,("config_id","execution_mode","cache_hit","new_numerical_execution","forecast_origin","last_label_date","source_run_id","source_code_sha","official_cell_file_sha256","result","metrics","exact_metrics"))
        events.append(item)
    if len(memory["writers"])<2 or len(memory["readers"])<2 or not any(any(authors.get(s)!=e["role"] for s in e.get("used_memory_source_ids",[]) if s in authors) for e in events):raise ValueError("No cross-agent use")
    frames=[]
    for r in grid["origins"]:
        if r.get("dataset_sha256")!=PACK_SHA or r.get("final_period_opened"):raise ValueError("Wrong grid vintage")
        frames.append({**pick(r,("origin","status","run_id","runtime_seconds","label_end")),"series":[pick(s,("series_id","gpu_model","pricing_tier","statistic")) for s in r.get("primary_catalog",[])],"methods":[{"config_id":m["config_id"],"pinball":m["exact_metrics"]["pinball"],"n_cells":m["exact_metrics"]["n_cells"],"skill_pooled":m["exact_metrics"].get("skill_pooled"),"by_horizon":{str(h):pick(v,("pinball","n_cells","skill_pooled")) for h,v in m.get("by_horizon",{}).items() if str(h) in ("1","3","7")}} for m in r.get("results",[])]})
    sources=[pick(s,("title","url","published_at","retrieved_at","historical_eligibility")) for s in memory["exa_evidence"]["sources"]]
    policy_public=pick(policy,("model","lora_rank","learning_rate","epochs","training_examples","training_datums","training_datums_seen","completed_model_decisions","forced_single_option_actions","training_temporal_origins","development_temporal_origins","actual_training_updates","trial_budget_per_task","common_initial_trials","teacher","selected_checkpoint_on_development","fixed_forecaster_references","comparisons","created_at","code_sha","training_cost_status","limitations"))
    final_public=pick(final,("final_origins","temporal_origins","trial_budget_per_task","selected_checkpoint_label","policy_model","frozen_at","comparisons","forecaster_references","paired_block_bootstrap","completed_model_decisions","forced_single_option_actions","training_updates","created_at","code_sha","limitations","cost_status"))
    result={"schema_version":1,"created_at":datetime.now(timezone.utc).isoformat(),"code_sha":sha,"dataset_sha256":PACK_SHA,"development":policy_public,"final":final_public,"representation":{"frames":sorted(frames,key=lambda f:f["origin"]),"attempted_origins":len(frames),"eligible_origins":sum(f["status"]=="completed" for f in frames),"code_sha":grid["code_sha"]},"traces":{"starting":public_trace(read_one(root/"final","starting_policy-final.json")),"trained":public_trace(read_one(root/"final","frozen_trained_policy-final.json"))},"memory":{"run_id":memory["run_id"],"writers":memory["writers"],"readers":memory["readers"],"actual_cross_agent_use":True,"events":events,"sources":sources,"exa_cost_dollars":memory["exa_evidence"].get("cost_dollars"),"historical_benchmark_input":False,"memory_performance_gain_claimed":False},"official_baseline":pick(baseline,("selected_method","methods","development_origins","last_development_label","code_sha")),"submission":pick(export,("run_id","origin_date","origin_cutoff_utc","dataset_sha256","method","n_headline_series","forecast_rows","horizons_days","quantiles","columns","forecast_csv_sha256","future_competition_truth_loaded","official_future_score","validation","runtime_seconds","cost_status","created_at","code_sha","vintage_note","source_attribution")),"freeze":pick(freeze,("frozen_at","protocol_version","policy_checkpoint_label","policy_training_run_id","official_method","official_selection_run_id","final_origins","numerical_code_sha256")),"links":{"training":"https://github.com/howdymary/compute-forecasting/actions/runs/43648086958","grid":"https://github.com/howdymary/compute-forecasting/actions/runs/43644639332","memory":"https://github.com/howdymary/compute-forecasting/actions/runs/43649141181","final":"https://github.com/howdymary/compute-forecasting/actions/runs/43653016797","repository":"https://github.com/howdymary/compute-forecasting/tree/compute-observatory"}}
    # Export reports contain derived forecasts and provenance only; no raw tables.
    validate(result);return result

def validate(value):
    if set(value)!={"schema_version","created_at","code_sha","dataset_sha256","development","final","representation","traces","memory","official_baseline","submission","freeze","links"}:raise ValueError("Unexpected public release fields")
    if value["dataset_sha256"]!=PACK_SHA or len(value["code_sha"])!=40:raise ValueError("Invalid source identity")
    encoded=json.dumps(value,allow_nan=False)
    if len(encoded)>500000:raise ValueError("Oversized public release")
    for forbidden in ("api_key","token_secret","Authorization","sampler_path","state_path","tinker://","rental_observations"):
        if forbidden in encoded:raise ValueError("Private field in public release")
    return value

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--inputs",default="inputs");p.add_argument("--output",default="artifacts/release.json");a=p.parse_args()
    result=build(a.inputs,os.environ["GITHUB_SHA"]);out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
