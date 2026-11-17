"""Credential-free reconstruction of saved categorical forecasts and matched arithmetic."""
from __future__ import annotations
import argparse,hashlib,json,pathlib,statistics
from compute_forecast.probability_v18 import digest,quantiles,crps,summarize,support
from compute_forecast.direct_forecast_v12 import cell_loss
from compute_forecast.pricing_contract import FORECAST_SHA
from compute_forecast.probability_analysis_v18 import diagnostics,paired
def read(p):return json.loads(p.read_text())
def check(folder):
    root=pathlib.Path(folder);report=read(root/"report.json")
    assert report["study_id"]=="direct-probability-v18" and digest(report["config"])==report["protocol_sha256"]
    assert report["dataset_sha256"]==report["audit"]["dataset_sha256"]
    manifest=root/"manifest.json"
    if manifest.exists():
        for item in read(manifest)["files"]:
            p=(root/item["path"]).resolve();assert p.is_relative_to(root.resolve())
            raw=p.read_bytes();assert len(raw)==item["bytes"] and hashlib.sha256(raw).hexdigest()==item["sha256"]
    case_index={c["task_id"]:c for phase in ("development","retrospective") for c in report["cases"].get(phase,[])}
    for c in case_index.values():assert all(r["date"]<=c["origin"] for r in c["history"])
    def verify_evaluation(ev):
        cells=ev["cells"];keys=[(r["series_id"],r["origin"],r["horizon_days"]) for r in cells];assert len(keys)==len(set(keys))
        for r in cells:
            t=case_index[r["task_id"]];index=(1,3,7).index(r["horizon_days"])
            assert r["series_id"]==t["series_id"] and r["origin"]==t["origin"]
            assert r["target_date"]==t["target_dates"][index] and r["outcome"]==t["outcomes"][index]
            assert r["support_prices"]==support(t["anchor"],report["log_levels"])
            assert len(r["probabilities"])==len(r["support_prices"])==report["config"]["distribution"]["n_levels"]
            assert r["probability_sha256"]==digest(r["probabilities"])
            q=quantiles(r["probabilities"],r["support_prices"]);assert q==[r[k] for k in ("q10","q50","q90")]
            assert 0<q[0]<=q[1]<=q[2] and abs(cell_loss(r["outcome"],q)-r["loss"])<1e-12
            assert abs(crps(r["probabilities"],r["support_prices"],r["outcome"])-r["crps"])<1e-10
        assert summarize(cells)==ev["summary"];return set(keys)
    baseline=None
    if report["base"]:
        for phase in ("development","retrospective"):verify_evaluation(report["base"][phase])
        baseline={(r["series_id"],r["origin"],r["horizon_days"]) for r in report["base"]["retrospective"]["cells"]}
    completed_candidates=[]
    for candidate in report["all_candidates"]:
        folder=root/candidate["artifact_folder"];saved=read(folder/"result.json")
        assert saved["dataset_sha256"]==report["dataset_sha256"] and saved["protocol_sha256"]==report["protocol_sha256"]
        assert saved["model"]==report["config"]["model"]
        assert saved["dataset_equivalent_passes"]==1.0 and saved["example_presentations"]==report["audit"]["phases"]["training"]["horizon_examples"]
        assert saved["optimizer_updates"]==saved["planned_updates"]==94
        assert [c["update"] for c in saved["checkpoints"]]==[0,24,47,94]
        for cp in saved["checkpoints"]:
            ev=read(folder/("development-"+str(cp["update"])+".json"));verify_evaluation(ev);assert ev["summary"]==cp["development"]
        assert min(saved["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))==saved["selected"]
        assert verify_evaluation(read(folder/"evaluation-selected.json"))==baseline
        completed_candidates.append(saved)
    for seed in (17,29,43):
        matched=[r for r in completed_candidates if r["seed"]==seed]
        if matched:
            assert len({r["batch_order_sha256"] for r in matched})==1
            assert len({r["tokenizer"]["backend_sha256"] for r in matched})==1
            assert len({digest(r["packages"]) for r in matched})==1
    if report["status"]=="completed":assert len(completed_candidates)==8
    assert report["optimizer_updates"]==sum(r["optimizer_updates"] for r in completed_candidates)+(report["api_preflight"]["new_optimizer_updates"] if report["api_preflight"] else 0)
    identities=set()
    for run in report["runs"]:
        identity=(run["objective"],run["seed"]);assert identity not in identities;identities.add(identity)
        assert run["protocol_sha256"]==report["protocol_sha256"] and run["dataset_sha256"]==report["dataset_sha256"]
        for cp in run["checkpoints"]:
            ev=run["development_evaluations"][str(cp["update"])];verify_evaluation(ev);assert cp["development"]==ev["summary"]
        assert min(run["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))==run["selected"]
        assert verify_evaluation(run["retrospective_evaluation"])==baseline
        assert run["retrospective_evaluation"]["summary"]==run["retrospective"]
        choice=report["selection"]["choices"][run["objective"]]
        assert choice["selected"]==min(choice["candidates"],key=lambda c:(c["development_pinball"],c["selected_update"],c["learning_rate"]))
        assert run["learning_rate"]==choice["selected"]["learning_rate"]
    if report["status"]=="completed":assert identities=={(a,s) for a in ("ce","crps") for s in (17,29,43)}
    for obj in ("ce","crps"):
        runs=[r for r in report["runs"] if r["objective"]==obj]
        if runs:assert statistics.mean(r["retrospective"]["primary_pinball"] for r in runs)==report["aggregate"][obj]["mean_primary_pinball"]
    for name,ref in report["native_references"].items():
        keys={(r["series_id"],r["origin"],r["horizon_days"]) for r in ref["cells"]};assert keys==baseline
        for r in ref["cells"]:assert abs(cell_loss(r["outcome"],[r[k] for k in ("q10","q50","q90")])-r["loss"])<1e-12
        assert summarize(ref["cells"])==ref["summary"]
    if report.get("diagnostics"):
        d=report["diagnostics"];cases=report["cases"]["retrospective"]
        assert diagnostics(report["base"]["retrospective"]["cells"],cases)==d["untuned"]
        if "primary_untuned" in d:assert diagnostics([r for r in report["base"]["retrospective"]["cells"] if r["horizon_days"]==7],cases)==d["primary_untuned"]
        for run in report["runs"]:
            saved=next(r for r in d["trained"] if r["objective"]==run["objective"] and r["seed"]==run["seed"])
            assert diagnostics(run["retrospective_evaluation"]["cells"],cases)==saved["breakdown"]
            if "primary_breakdown" in saved:assert diagnostics([r for r in run["retrospective_evaluation"]["cells"] if r["horizon_days"]==7],cases)==saved["primary_breakdown"]
            assert paired(run["retrospective_evaluation"]["cells"],report["base"]["retrospective"]["cells"],cases)==saved["versus_untuned"]
            for name,value in report["native_references"].items():
                assert paired(run["retrospective_evaluation"]["cells"],value["cells"],cases)==saved["versus_numerical"][name]
    raw=(root/"report.json").read_text();assert "tinker://" not in raw,"Private checkpoint resource leaked"
    official=pathlib.Path("results/frozen-v1/forecasts.csv");assert hashlib.sha256(official.read_bytes()).hexdigest()==FORECAST_SHA
    assert not report["audit"]["protected_outcomes_loaded"]
    print(json.dumps({"status":"verified","study_id":report["study_id"],"final_runs":len(report["runs"]),"official_export_unchanged":True,"prospective_accuracy":"not established","scope":"Saved probability, score, cohort, selection and public hash reconstruction; full data rebuilding requires authorized pack access"}))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--results");a=p.parse_args()
    if a.results:folder=pathlib.Path(a.results)
    else:
        pointer=read(pathlib.Path("results/probability-v18/latest.json"));target=pathlib.Path(pointer["report_path"])
        assert hashlib.sha256(target.read_bytes()).hexdigest()==pointer["report_sha256"]
        folder=target.parent
    check(folder)
