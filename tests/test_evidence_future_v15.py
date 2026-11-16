"""Synthetic future-panel contracts; no values are actual market observations."""
import copy
import pytest
from compute_forecast.direct_forecast_v12 import digest
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
    for s in (a,b):
        assert not source_snapshots([s],"2026-11-16T22:00:00Z")[0]
def test_exact_registered_weekly_window_and_finite_limit():
    p=protocol();assert origin_number("2026-12-06",p)==0 and origin_number("2027-02-21",p)==11
    for origin in ("2026-11-29","2026-12-07","2027-02-28"):assert origin_number(origin,p) is None
def test_no_inference_before_readiness_or_without_current_original_vintage():
    r=prepare([snapshot()],[],"2026-11-16T22:00:00Z",protocol())
    assert not r["eligible"] and not r["tasks"] and r["distinct_quote_days"]==1
    assert "current_original_BLS_release_vintage_not_qualified" in r["reasons"]
