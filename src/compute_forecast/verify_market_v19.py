"""Credential-free reconstruction of public v19 forecasts and comparisons."""
import hashlib,json,pathlib,statistics
from compute_forecast.probability_v18 import digest,quantiles,summarize
from compute_forecast.direct_forecast_v12 import cell_loss
def verify(report):
    assert report["study_id"]=="market-state-v19" and not report["protocol"]["preservation"]["protected_outcomes_loaded"]
    assert report["protocol_sha256"]==digest(report["protocol"])
    keys=None
    for run in report["runs"]:
        rows=run["retrospective"]["cells"];current={(r["task_id"],r["horizon_days"]) for r in rows}
        assert len(current)==len(rows)
        if keys is None:keys=current
        assert current==keys
        for group in (rows,run["untuned"]["cells"]):
            for r in group:
                q=[r[k] for k in ("q10","q50","q90")]
                assert q==quantiles(r["probabilities"],r["support_prices"])
                assert abs(cell_loss(r["outcome"],q)-r["loss"])<1e-12
        assert summarize(rows)==run["retrospective"]["summary"]
        assert run["selected"]==min(run["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))
    for c in report["comparison"]:
        a,b=[next(r for r in report["runs"] if r["seed"]==c["seed"] and r["arm"]==arm) for arm in ("price","market")]
        assert abs(c["market_minus_price"]-(b["retrospective"]["summary"]["primary_pinball"]-a["retrospective"]["summary"]["primary_pinball"]))<1e-12
        assert a["batch_order_sha256"]==b["batch_order_sha256"]
        assert abs(sum(r["weighted_contribution"] for r in c["by_origin"])-c["market_minus_price"])<1e-12
    for case in report["cases"]:
        for cp in case["checkpoints"]:
            for r in cp["rows"]:
                assert r["origin"]==case["origin"] and r["task_id"]==case["task_id"]
                assert [r[k] for k in ("q10","q50","q90")]==quantiles(r["probabilities"],r["support_prices"])
                assert abs(cell_loss(r["outcome"],[r[k] for k in ("q10","q50","q90")])-r["loss"])<1e-12
    assert report["new_optimizer_updates"]==sum(r["optimizer_updates"] for r in report["runs"])
    for phase,methods in report["controls"]["results"].items():
        for method,value in methods.items():
            assert summarize(value["cells"])==value["summary"]
            if phase=="retrospective":assert {(r["task_id"],r["horizon_days"]) for r in value["cells"]}==keys
            for r in value["cells"]:assert abs(cell_loss(r["outcome"],[r[k] for k in ("q10","q50","q90")])-r["loss"])<1e-12
    official=pathlib.Path("results/frozen-v1/forecasts.csv")
    assert hashlib.sha256(official.read_bytes()).hexdigest()=="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
    return {"status":"passed","runs":len(report["runs"]),"matched_cells":len(keys),"optimizer_updates":report["new_optimizer_updates"],"prospective_accuracy":"not established"}
def verify_progress(report):
    assert report["study_id"]=="market-state-v19-progress" and report["status"]=="training_in_progress"
    assert report["protocol_sha256"]==digest(report["protocol"]) and not report["protocol"]["preservation"]["protected_outcomes_loaded"]
    assert len(report["runs"])==6 and report["new_optimizer_updates"]==sum(r["optimizer_updates"] for r in report["runs"])
    assert report["completed_runs"]==sum(r["status"]=="completed" for r in report["runs"])
    for run in report["runs"]:
        if run["status"]=="queued":assert run["optimizer_updates"]==0 and len(run["checkpoints"])==1 and run["selected"] is None
        for cp in run["checkpoints"]:
            rows=[r for case in report["cases"] for c in case["checkpoints"] if c["arm"]==run["arm"] and c["seed"]==run["seed"] and c["update"]==cp["update"] for r in c["rows"]]
            assert summarize(rows)==cp["development"]
            for r in rows:
                assert quantiles(r["probabilities"],r["support_prices"])==[r[k] for k in ("q10","q50","q90")]
                assert abs(cell_loss(r["outcome"],[r[k] for k in ("q10","q50","q90")])-r["loss"])<1e-12
    return {"status":"passed_progress_contracts","completed_runs":report["completed_runs"],"durable_optimizer_updates":report["new_optimizer_updates"],"scope":"Actual retained development checkpoints; final comparisons still pending"}

if __name__=="__main__":
    import sys
    if len(sys.argv)>1:report=json.loads(pathlib.Path(sys.argv[1]).read_bytes())
    else:
        pointer_file=pathlib.Path("results/market-state-v19/latest.json")
        if not pointer_file.exists():pointer_file=pathlib.Path("results/market-state-v19/progress/latest.json")
        pointer=json.loads(pointer_file.read_bytes());raw=pathlib.Path(pointer["report_path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"];report=json.loads(raw)
    print(json.dumps(verify_progress(report) if report["study_id"]=="market-state-v19-progress" else verify(report)))
