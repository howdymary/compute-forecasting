"""Synthetic future-panel contracts; no values are actual market observations."""
import copy
import pytest
from compute_forecast.review_v4 import digest
from compute_forecast.evidence_future_v15 import source_snapshots,origin_number,prepare
def protocol():
    return {"study_id":"synthetic","first_eligible_origin":"2026-12-06","history_calendar_days":42,"min_price_days":20,"horizons":[1,3,7],"issuance_deadline_minutes_after_origin":30,"limits":{"max_weekly_origins":12,"max_targets":4}}
def snapshot(day="2026-11-16",hour="17",quote=None):
    contract={"provider":"synthetic","gpu":"a100-pcie-40"}
    return {"captured_at":day+"T"+hour+":30:00Z","protected_outcomes_loaded":False,"prices":{"date":day,"license":"CC BY 4.0","rows":[{"id":"grp-v6-"+digest(contract)[:20],"date":day,"unit":"USD per GPU-hour","family":"A100","contract":contract,"fetched_at":(quote or day)+"T17:00:00Z","value":2.0}]}}
def test_future_snapshot_accepts_only_source_window_and_same_day_quotes():
    assert len(source_snapshots([snapshot()],"2026-11-16T22:00:00Z")[0])==1
    for bad in (snapshot(hour="20"),snapshot(quote="2026-11-15"),snapshot(day="2026-11-13")):
        assert not source_snapshots([bad],"2026-11-16T22:00:00Z")[0]
def test_future_row_poisoning_is_excluded():
    a=snapshot();a["prices"]["rows"][0]["contract"]["provider"]="changed"
    b=snapshot();b["prices"]["rows"][0]["unit"]="USD per instance-hour"
    c=snapshot();c["prices"]["rows"][0]["value"]=float("inf")
    for s in (a,b,c):
        assert not source_snapshots([s],"2026-11-16T22:00:00Z")[0]
def test_exact_registered_weekly_window_and_finite_limit():
    p=protocol();assert origin_number("2026-12-06",p)==0 and origin_number("2027-02-21",p)==11
    for origin in ("2026-11-29","2026-12-07","2027-02-28"):assert origin_number(origin,p) is None
def test_no_inference_before_readiness_or_without_current_original_vintage():
    r=prepare([snapshot()],[],"2026-11-16T22:00:00Z",protocol())
    assert not r["eligible"] and not r["tasks"] and r["distinct_quote_days"]==1
    assert "current_original_BLS_release_vintage_not_qualified" in r["reasons"]

def ready():
    from datetime import date,timedelta
    from compute_forecast.direct_forecast_v12 import digest as model_digest
    from compute_forecast.evidence_future_v15 import validate,score
    p=protocol();days=[(date(2026,11,17)+timedelta(days=i)).isoformat() for i in range(20)]
    observations=[snapshot(day=d) for d in days]
    for s in observations:s["bls"]={"latest_period":"2026-10"}
    vintage={"status":"qualified_pending_spot_check","series_id":"PCU221122221122","source_url":"https://example.test/synthetic-original.pdf","available_at":"2026-11-13T13:30:00Z","first_observed_at":"2026-11-16T20:00:00Z","retrieved_at":"2026-11-16T20:00:00Z","content_sha256":"synthetic","reference_period":"2026-10","values":{"periods":["2026-06","2026-07","2026-08","2026-09","2026-10"],"indices":[100,101,102,103,104],"source_row_sha256":"synthetic"}}
    result=prepare(observations,[vintage],"2026-12-07T00:05:00Z",p);assert result["eligible"]
    task=result["tasks"][0];lock={"operational_seed":17,"locked_at":"2026-11-20T00:00:00Z","price_only":{"checkpoint_sha256":"synthetic-price"},"price_evidence":{"checkpoint_sha256":"synthetic-bls"}}
    rows=[]
    methods=("price_only","price_evidence","base_price_only","base_price_evidence","last_value","last_value_empirical","drift","seasonal_naive")
    for method in methods:
        for i,h in enumerate(p["horizons"]):
            rows.append({"method":method,"reference":method not in ("price_only","price_evidence"),"checkpoint_sha256":lock.get(method,{}).get("checkpoint_sha256","synthetic-base"),"series_id":task["series_id"],"task_id":task["task_id"],"contract_sha256":model_digest(task["metadata"]["contract"]),"horizon_days":h,"target_date":task["target_dates"][i],"q10":1.8,"q50":2.0,"q90":2.2,"fallback":False})
    commitment={"status":"issued","study_id":p["study_id"],"protocol_sha256":model_digest(p),"origin":"2026-12-06","information_cutoff":"2026-12-06T23:59:59+00:00","issued_at":"2026-12-07T00:05:00Z","model_lock_sha256":model_digest(lock),"input_snapshot_hashes":["synthetic"],"rows":rows}
    return commitment,observations,p,lock
def test_all_eight_arms_match_and_only_matured_observed_truth_is_scored():
    from compute_forecast.evidence_future_v15 import validate,score
    c,observations,p,lock=ready();validate(c,p,lock)
    observations += [snapshot(day=d) for d in ("2026-12-07","2026-12-09","2026-12-13")]
    early=score(c,observations,"2026-12-08T00:01:00Z",p,lock)
    assert early["status"]=="pending" and len(early["cells"])==8
    complete=score(c,observations,"2026-12-14T00:01:00Z",p,lock)
    assert complete["status"]=="completed" and len(complete["cells"])==24
    assert set(complete["by_method"])=={"price_only","price_evidence","base_price_only","base_price_evidence","last_value","last_value_empirical","drift","seasonal_naive"}
def test_duplicate_missing_and_late_commitment_contracts_fail():
    from compute_forecast.evidence_future_v15 import validate
    c,observations,p,lock=ready()
    duplicate=copy.deepcopy(c);duplicate["rows"].append(duplicate["rows"][0])
    missing=copy.deepcopy(c);missing["rows"]=missing["rows"][:-1]
    late=copy.deepcopy(c);late["issued_at"]="2026-12-07T00:31:00Z"
    changed=copy.deepcopy(c);changed["rows"][0]["checkpoint_sha256"]="different"
    for bad in (duplicate,missing,late,changed):
        with pytest.raises(AssertionError):validate(bad,p,lock)
