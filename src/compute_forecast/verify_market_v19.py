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
if __name__=="__main__":
    import sys
    if len(sys.argv)>1:report=json.loads(pathlib.Path(sys.argv[1]).read_bytes())
    else:
        pointer=json.loads(pathlib.Path("results/market-state-v19/latest.json").read_bytes());raw=pathlib.Path(pointer["report_path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"];report=json.loads(raw)
    print(json.dumps(verify(report)))
