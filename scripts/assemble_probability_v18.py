"""Publish only retained actual probability runs; preserve failed candidates and matched scopes."""
from __future__ import annotations
import collections,hashlib,json,os,pathlib,shutil,statistics,subprocess
from datetime import datetime,timezone
from compute_forecast.probability_v18 import digest,quantiles,crps,summarize
from compute_forecast.direct_forecast_v12 import cell_loss
from compute_forecast.probability_analysis_v18 import diagnostics,paired
def read(p):return json.loads(pathlib.Path(p).read_text())
def mean(x):return statistics.mean(x) if x else None
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False)+"\n")
def key(r):return (r["series_id"],r["origin"],r["horizon_days"])
def comparison(candidate,reference):
    a={key(r):r for r in candidate};b={key(r):r for r in reference};assert a.keys()==b.keys(),"Matched comparison cohort mismatch"
    rows=[]
    for k,r in a.items():
        assert abs(r["outcome"]-b[k]["outcome"])<1e-10
        rows.append({**{n:r[n] for n in ("series_id","origin","horizon_days")},"difference":r["loss"]-b[k]["loss"]})
    primary=[r for r in rows if r["horizon_days"]==7]
    return {"n":len(primary),"difference":mean([r["difference"] for r in primary]),"by_origin":{o:mean([r["difference"] for r in primary if r["origin"]==o]) for o in sorted({r["origin"] for r in primary})},"by_series":{s:mean([r["difference"] for r in primary if r["series_id"]==s]) for s in sorted({r["series_id"] for r in primary})},"horizons":{str(h):{"n":sum(r["horizon_days"]==h for r in rows),"difference":mean([r["difference"] for r in rows if r["horizon_days"]==h])} for h in (1,3,7)}}
def main():
    root=pathlib.Path("inputs/probability-v18-collected");out=pathlib.Path("artifacts/probability-v18-public");out.mkdir(parents=True,exist_ok=True)
    p=read("configs/direct-probability-v18.json");audit=read("results/probability-v18/audits/44006306188/audit.json")
    datasets=list(root.rglob("dataset.json"));data=read(datasets[0]) if datasets else None
    if data:assert digest(data)==audit["dataset_sha256"] and data["protocol_sha256"]==digest(p)
    selections=list(root.rglob("learning-rates.json"));selection=read(selections[0]) if selections else None
    bases=list(root.rglob("base.json"));base=read(bases[0]) if bases else None
    api_checks=list(root.rglob("api-preflight.json"));api_check=read(api_checks[0]) if api_checks else None
    candidates=[];final=[];failures=[]
    for path in sorted(root.rglob("result.json")):
        value=read(path)
        if value.get("study_id")!=p["study_id"]:continue
        assert value["dataset_sha256"]==audit["dataset_sha256"] and value["protocol_sha256"]==digest(p)
        folder=value["objective"]+"/seed-"+str(value["seed"])+"/lr-"+format(value["learning_rate"],".0e")
        public=out/"models"/folder;public.mkdir(parents=True,exist_ok=True)
        for f in path.parent.glob("*.json"):shutil.copyfile(f,public/f.name)
        selected=min(value["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))
        assert selected==value["selected"],"Checkpoint selection changed"
        evaluations={str(c["update"]):read(path.parent/("development-"+str(c["update"])+".json")) for c in value["checkpoints"]}
        evaluation=read(path.parent/"evaluation-selected.json")
        for ev in [*evaluations.values(),evaluation]:
            for r in ev["cells"]:
                assert 0<r["q10"]<=r["q50"]<=r["q90"]
                assert quantiles(r["probabilities"],r["support_prices"])==[r[k] for k in ("q10","q50","q90")]
                assert abs(cell_loss(r["outcome"],[r[k] for k in ("q10","q50","q90")])-r["loss"])<1e-12
                assert abs(crps(r["probabilities"],r["support_prices"],r["outcome"])-r["crps"])<1e-10
            assert ev["summary"]==summarize(ev["cells"])
        record={**value,"artifact_folder":"models/"+folder,"development_evaluations":evaluations,"retrospective_evaluation":evaluation}
        candidates.append(record)
        if selection and value["learning_rate"]==selection["choices"][value["objective"]]["selected"]["learning_rate"]:final.append(record)
    for f in root.rglob("progress.json"):
        value=read(f)
        if value.get("study_id")==p["study_id"] and not (f.parent/"result.json").exists():failures.append({k:value.get(k) for k in ("objective","seed","learning_rate","status","optimizer_updates","source_sha")})
    final.sort(key=lambda r:(r["objective"],r["seed"]))
    assert len({(r["objective"],r["seed"]) for r in final})==len(final),"Duplicate final run"
    references={}
    if data:
        lookup={(r["method"],r["series_id"],r["origin"],r["horizon_days"]):r for r in data["references"]}
        for method in p["evaluation"]["references"]:
            cells=[]
            for t in data["groups"]["retrospective"]:
                for h,y in zip(p["data"]["horizons"],t["outcomes"]):
                    r=lookup[(method,t["series_id"],t["origin"],h)];q=[r[k] for k in ("q10","q50","q90")]
                    cells.append({"task_id":t["task_id"],"series_id":t["series_id"],"origin":t["origin"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"outcome":y,"q10":q[0],"q50":q[1],"q90":q[2],"loss":cell_loss(y,q),"crps":None,"fallback":r["fallback"],"method":method})
            references[method]={"summary":summarize(cells),"cells":cells}
    comparisons=[];aggregate={}
    if base:
        for run in final:
            comparisons.append({"objective":run["objective"],"seed":run["seed"],"versus_base":comparison(run["retrospective_evaluation"]["cells"],base["retrospective"]["cells"])})
        for name in ("ce","crps"):
            runs=[r for r in final if r["objective"]==name]
            if runs:
                aggregate[name]={"seeds":len(runs),"mean_primary_pinball":mean([r["retrospective"]["primary_pinball"] for r in runs]),"seed_primary_losses":[{"seed":r["seed"],"pinball":r["retrospective"]["primary_pinball"],"selected_update":r["selected"]["update"]} for r in runs],"mean_coverage":mean([r["retrospective"]["by_horizon"]["7"]["coverage"] for r in runs]),"mean_width":mean([r["retrospective"]["by_horizon"]["7"]["width"] for r in runs]),"mean_crps":mean([r["retrospective"]["by_horizon"]["7"]["crps"] for r in runs]),"mean_median_mae":mean([r["retrospective"]["by_horizon"]["7"]["median_mae"] for r in runs])}
        aggregate["base"]={"mean_primary_pinball":base["retrospective"]["summary"]["primary_pinball"],"summary":base["retrospective"]["summary"]}
    paired=[]
    for seed in p["model"]["seeds"]:
        a=next((r for r in final if r["objective"]=="crps" and r["seed"]==seed),None);b=next((r for r in final if r["objective"]=="ce" and r["seed"]==seed),None)
        if a and b:paired.append({"seed":seed,**comparison(a["retrospective_evaluation"]["cells"],b["retrospective_evaluation"]["cells"])})
    original_subset=[]
    original_pointer=read("results/evidence-v14/latest.json");original=read(original_pointer["report_path"])
    for run in final:
        prior=next((r for r in original["runs"] if r["arm"]=="price_only" and r["seed"]==run["seed"]),None)
        if not prior:continue
        old=read(pathlib.Path(original_pointer["report_path"]).parent/"price_only"/("seed-"+str(run["seed"]))/"evaluation-base.json")["cells"]
        new={key(r):r for r in run["retrospective_evaluation"]["cells"]};matched=[r for r in old if key(r) in new]
        if matched:original_subset.append({"objective":run["objective"],"seed":run["seed"],"scope":"Only exact retained v14 JSON-base matches; not the full v18 cohort; provider base revision unrecorded","original_summary":summarize(matched),"candidate_summary":summarize([new[key(r)] for r in matched]),"comparison":comparison([new[key(r)] for r in matched],matched)})
    issued=0
    status="completed" if len(final)==6 else "partial" if candidates else "pending_or_gated"
    report={"study_id":p["study_id"],"schema_version":18,"status":status,"created_at":datetime.now(timezone.utc).isoformat(),"classification":p["classification"],"config":p,"protocol_sha256":digest(p),"dataset_sha256":audit["dataset_sha256"],"audit":audit,"preflight_path":"results/probability-v18/audits/44006306188/preflight.json","api_preflight":api_check,"selection":selection,"runs":final,"all_candidates":[{k:r.get(k) for k in ("objective","seed","learning_rate","selected","optimizer_updates","artifact_folder","status")} for r in candidates],"incomplete_runs":failures,"expected_final_runs":6,"aggregate":aggregate,"comparisons_to_base":comparisons,"crps_minus_ce":paired,"native_references":references,"original_json_subset":original_subset,"chronos":{"status":"unavailable","reason":"No new comparator executed; no verified pinned forecast artifact matched to the new full cohort"},"base":base,"cases":{phase:[{"task_id":t["task_id"],"series_id":t["series_id"],"metadata":t["metadata"],"origin":t["origin"],"anchor":t["anchor"],"history":t["context"],"target_dates":t["target_dates"],"outcomes":t["outcomes"]} for t in data["groups"][phase]] for phase in ("development","retrospective")} if data else {},"log_levels":audit["log_levels"],"optimizer_updates":sum(r["optimizer_updates"] for r in candidates)+(api_check["new_optimizer_updates"] if api_check else 0),"provider_cost_usd":None,"usage_scope":"Completed retained candidate runs plus the separate API mechanism check; active runs may have additional unpublished updates","prospective":{"status":"registered_pending_issuance","forecasts_issued":issued,"accuracy":"not established","protocol":"configs/probability-v18-prospective.json","aggregate_source":"Continuing exact collector medians not verified; individual contracts are a separate transfer cohort"},"limits":["Twenty-five seven-day cases from eleven series and three dependent historical dates; no population-significance claim","All opened historical outcomes remain retrospective","19-point support introduces discretization; actual outcomes are never clipped","Base weight revision is unavailable; tokenizer content hash is retained","BLS and news are excluded from this price-only study","Unknown costs remain unknown"],"preservation":p["preservation"],"source_attribution":audit["source_attribution"]}
    if data and base:
        cohort=report["cases"]["retrospective"]
        detail={"untuned":diagnostics(base["retrospective"]["cells"],cohort),"numerical_references":{name:diagnostics(value["cells"],cohort) for name,value in references.items()},"trained":[],"conditional_uncertainty":"Three dependent reused market origins. Seed ranges and leave-one-origin sensitivity are descriptive; no population confidence interval is estimated."}
        for run in final:
            candidate=run["retrospective_evaluation"]["cells"]
            detail["trained"].append({"objective":run["objective"],"seed":run["seed"],"breakdown":diagnostics(candidate,cohort),"versus_untuned":paired(candidate,base["retrospective"]["cells"],cohort),"versus_numerical":{name:paired(candidate,value["cells"],cohort) for name,value in references.items()}})
        report["diagnostics"]=detail
        report["chronos"]={"status":"unavailable_on_registered_cohort","existing_artifact":"results/explorer-v3/chronos-control.json","existing_origins":["2026-08-29","2026-09-05","2026-09-12"],"reason":"The retained Chronos retrospective origins have zero overlap with the registered October25/28/30 cohort. Existing November commitments remain unscored and are not repurposed."}
        report["resource_accounting"]={"completed_candidate_runs":len(candidates),"completed_optimizer_updates":sum(r["optimizer_updates"] for r in candidates),"mechanism_preflight_updates":api_check["new_optimizer_updates"] if api_check else 0,"example_presentations":sum(r["example_presentations"] for r in candidates),"elapsed_candidate_seconds_sum":sum(r["elapsed_seconds"] for r in candidates),"provider_cost_usd":None,"note":"Summed candidate elapsed time is not campaign wall time or a billing receipt; active unsaved updates are excluded."}
    if base and aggregate:
        reference=base["retrospective"]["summary"]["primary_pinball"]
        report["retrospective_training_gain"]={obj:{"mean_difference":aggregate[obj]["mean_primary_pinball"]-reference,"improving_seeds":sum(r["retrospective"]["primary_pinball"]<reference and r["selected"]["update"]>0 for r in final if r["objective"]==obj),"scope":"Descriptive historical matched comparison only"} for obj in ("ce","crps") if obj in aggregate}
    if len(final)==6 and base:
        starting=base["retrospective"]["summary"]["by_horizon"]["7"]
        best_native=min(value["summary"]["primary_pinball"] for value in references.values())
        report["primary_interpretation"]={"scope":"Retrospective seven-day quantile loss on 25 matched cases, 11 series, three dependent dates; three seeds per objective","models":{obj:{"difference_vs_untuned":aggregate[obj]["mean_primary_pinball"]-starting["pinball"],"difference_vs_best_official_reference":aggregate[obj]["mean_primary_pinball"]-best_native,"median_mae_difference_vs_untuned":aggregate[obj]["mean_median_mae"]-starting["median_mae"],"wins_vs_untuned_seeds":report["retrospective_training_gain"][obj]["improving_seeds"]} for obj in ("ce","crps")},"limitations":"Probabilistic score improvement does not establish improved median predictions, every-case improvement, an objective's universal superiority, or prospective accuracy. Original JSON forecasts use a separate six-case seven-day subset; Chronos has no matched origin."}
    write(out/"report.json",report);write(out/"config.json",p);write(out/"audit.json",audit)
    lines=["# Direct probability forecasting v18","",""+status+". CE and CRPS use the same registered output levels and matched chronological data.","","Retrospective seven-day results; three dependent dates. Prospective improvement is not established.","","| Method | Seven-day pinball | Median MAE | CRPS | Coverage | Width |","|---|---:|---:|---:|---:|---:|"]
    if base:lines.append(f'| Untuned probability model | {base["retrospective"]["summary"]["primary_pinball"]:.10f} | {base["retrospective"]["summary"]["by_horizon"]["7"]["median_mae"]:.6f} | {base["retrospective"]["summary"]["by_horizon"]["7"]["crps"]:.6f} | {base["retrospective"]["summary"]["by_horizon"]["7"]["coverage"]:.2%} | {base["retrospective"]["summary"]["by_horizon"]["7"]["width"]:.6f} |')
    for obj in ("ce","crps"):
        if obj in aggregate:
            a=aggregate[obj];lines.append(f'| {obj.upper()} trained, {a["seeds"]} seeds | {a["mean_primary_pinball"]:.10f} | {a["mean_median_mae"]:.6f} | {a["mean_crps"]:.6f} | {a["mean_coverage"]:.2%} | {a["mean_width"]:.6f} |')
    for method,value in references.items():
        a=value["summary"];lines.append(f'| Native {method} | {a["primary_pinball"]:.10f} | {a["by_horizon"]["7"]["median_mae"]:.6f} | not retained | {a["by_horizon"]["7"]["coverage"]:.2%} | {a["by_horizon"]["7"]["width"]:.6f} |')
    if report.get("primary_interpretation"):
        lines.extend(["","## Interpretation","","All comparisons below are descriptive, retrospective and conditional on this registered cohort."])
        for obj,value in report["primary_interpretation"]["models"].items():
            lines.append(f'{obj.upper()}: trained-minus-untuned seven-day pinball {value["difference_vs_untuned"]:+.10f}; difference from the best official reference {value["difference_vs_best_official_reference"]:+.10f}; median-MAE difference {value["median_mae_difference_vs_untuned"]:+.6f}. {value["wins_vs_untuned_seeds"]}/3 seeds improved over the common untuned model.')
        lines.extend(["",report["primary_interpretation"]["limitations"]])
    lines.extend(["",f'Actual optimizer updates including API preflight: {report["optimizer_updates"]}. Complete final runs: {len(final)}/6.',"","All candidate runs, original selections, failures and probability vectors are retained in the versioned results folder. Learning rates and checkpoints are selected on development fields only. The original v14 JSON comparison uses a separate exact-match subset.","","Provider charges are unavailable. This is a direct price-distribution model, separate from the earlier experiment selector."])
    (out/"findings.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({"study_id":p["study_id"],"status":status,"final_runs":len(final),"optimizer_updates":report["optimizer_updates"],"aggregate":aggregate}),flush=True)
if __name__=="__main__":main()
