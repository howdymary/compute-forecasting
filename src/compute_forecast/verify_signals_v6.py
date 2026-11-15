"""Credential-free checks of registered configuration and actual issued pilot."""
import hashlib,json
from pathlib import Path
from .signals_v6 import config,digest,evaluate,readiness,utc
SHA="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
def main():
    root=Path("results/signals-v6/runs/43763941660");index=json.loads((root/"index.json").read_bytes());registration=json.loads((root/"registration.json").read_bytes())
    assert digest(config())==registration["protocol_sha256"]==index["protocol_sha256"]
    assert hashlib.sha256(Path("src/compute_forecast/signals_v6.py").read_bytes()).hexdigest()==registration["engine_sha256"]
    assert hashlib.sha256(Path("results/frozen-v1/forecasts.csv").read_bytes()).hexdigest()==SHA
    snapshots=[json.loads(p.read_bytes()) for p in root.glob("snapshots-*.json")];records=[json.loads(p.read_bytes()) for p in root.glob("commitments-*.json")]
    assert len(snapshots)==1 and len(records)==1
    snapshot=snapshots[0];record=records[0]
    assert len(snapshot["prices"]["cohort"])==len(snapshot["prices"]["rows"])==4
    assert snapshot["prices"]["date"]=="2026-11-15" and snapshot["protected_outcomes_loaded"] is False
    assert set(r["family"] for r in snapshot["prices"]["rows"])=={"A100","H100"}
    assert all(utc(r["fetched_at"]).date().isoformat()==r["date"] for r in snapshot["prices"]["rows"])
    assert len(record["rows"])==48 and record["kind"]=="cold_start_reference_pilot" and record["status"]=="issued_reference_pilot"
    assert record["registration_sha256"]==digest(config()) and digest(snapshot) in record["input_snapshot_hashes"]
    assert utc(record["issued_at"])<utc("2026-11-16T00:00:00Z")
    keys=set()
    for r in record["rows"]:
        key=(r["series_id"],r["horizon_days"],r["forecaster"]);assert key not in keys;keys.add(key)
        assert r["q10"]>0 and r["q10"]<=r["q50"]<=r["q90"]
        assert r["forecaster"] in config()["references"]
    assert len({r["forecaster"] for r in record["rows"]})==4
    score=evaluate(record,snapshots,"2026-11-15T23:00:00Z",digest(record))
    assert score["status"]=="pending" and not score["cells"]
    assert readiness(snapshots)["new_optimizer_updates"]==0
    report={"status":"passed","source_sha":__import__("os").environ.get("GITHUB_SHA"),"protocol_sha256":digest(config()),"engine_sha256":registration["engine_sha256"],"official_csv_sha256":SHA,"actual_quote_contracts":4,"quote_date":"2026-11-15","pilot_forecast_rows":48,"pilot_forecasters":4,"pilot_horizons":[1,3,7],"target_dates":sorted({r["target_date"] for r in record["rows"]}),"primary_signal_forecasts_issued":0,"prospective_improvement_established":False,"registered_weekly_origins":len(config()["origins"]),"hashes":{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob("*.json")},"interpretation":"Actual future pilot commitments verified; primary signal-value test awaits retained history and mature outcomes."}
    out=Path("artifacts/signals-public-v6");out.mkdir(parents=True,exist_ok=True);(out/"verification.json").write_text(json.dumps(report,indent=2)+"\n");print("V6_PUBLIC_VERIFICATION:"+json.dumps(report),flush=True)
if __name__=="__main__":main()
