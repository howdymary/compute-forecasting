"""Scientific boundary tests for genuinely prospective signal evaluation."""
import copy
from datetime import datetime,timezone
import pytest
from compute_forecast.signals_v6 import *
def snapshot(day="2026-11-15",value=2.):
    row={"provider":"test","gpu":"h100-sxm","vram_gb":80,"usd_hr":value,"kind":"on-demand","source_url":"https://example.org/prices","fetched_at":day+"T08:00:00+00:00","min_gpus":8,"region":"us"}
    raw={"date":day,"generated_at":day+"T09:00:00+00:00","offers":[row]}
    prices=normalize_prices(raw,{"provider_freshness":{"test":{"status":"current"}}},day+"T17:30:00+00:00")
    return {"captured_at":day+"T17:30:00+00:00","prices":prices,"features":{k:None for g in FEATURES.values() for k in g},"events":[],"bls":None,"protocol_sha256":digest(config())}
def pilot(s):
    sid=s["prices"]["rows"][0]["id"]
    r={"series_id":sid,"family":"H100","origin_date":"2026-11-15","target_date":"2026-11-16","horizon_days":1,"forecaster":"last_value","q10":2.,"q50":2.,"q90":2.}
    return issue([s],"2026-11-15","2026-11-15T18:00:00+00:00",[r],pilot=True)
def test_no_backdated_pilot():
    with pytest.raises(ValueError):issue([snapshot()],"2026-11-14","2026-11-15T18:00:00+00:00",[],pilot=True)
def test_timezone_mandatory():
    with pytest.raises(ValueError):utc("2026-11-15T18:00:00")
def test_protected_current_snapshot_refused():
    with pytest.raises(ValueError):snapshot("2026-11-10")
def test_first_vintage_and_future_input():
    first=snapshot();revised=snapshot(value=9);revised["captured_at"]="2026-11-15T19:00:00+00:00"
    assert asof_snapshots([revised,first],"2026-11-15T20:00:00+00:00")[0]["prices"]["rows"][0]["value"]==2
    assert asof_snapshots([revised],"2026-11-15T18:00:00+00:00")==[]
def test_provider_freshness_excludes_carried_quotes():
    p={"date":"2026-11-15","generated_at":"2026-11-15T09:00:00Z","offers":[{"provider":"bad","gpu":"h100-sxm","kind":"on-demand","usd_hr":2,"fetched_at":"2026-11-14T08:00:00Z"}]}
    assert not normalize_prices(p,{"provider_freshness":{"bad":{"status":"stale"}}},"2026-11-15T18:00:00Z")["rows"]
def test_reference_quantile_order():
    s=snapshot();r=pilot(s)["rows"][0];r["q10"]=3
    with pytest.raises(ValueError):issue([s],"2026-11-15","2026-11-15T18:00:00Z",[r],pilot=True)
def test_duplicate_reference_rejected():
    s=snapshot();r=pilot(s)["rows"][0]
    with pytest.raises(ValueError):issue([s],"2026-11-15","2026-11-15T18:00:00Z",[r,r],pilot=True)
def test_immutable_forecast(tmp_path):
    retain(tmp_path,"commitments",{"x":1},"origin")
    with pytest.raises(ValueError):retain(tmp_path,"commitments",{"x":2},"origin")
def test_unmatured_outcome_never_scored():
    s=snapshot();r=pilot(s);truth=snapshot("2026-11-16",4)
    result=evaluate(r,[truth],"2026-11-16T23:59:00Z",digest(r))
    assert result["status"]=="pending" and not result["cells"]
def test_compatible_matured_outcome():
    s=snapshot();r=pilot(s);truth=snapshot("2026-11-16",4)
    result=evaluate(r,[truth],"2026-11-17T00:00:01Z",digest(r))
    assert result["status"]=="completed" and result["cells"][0]["pinball"]==1
    assert result["classification"]=="cold_start_reference_pilot"
def test_changed_commitment_refused():
    s=snapshot();r=pilot(s);h=digest(r);r["rows"][0]["q50"]=3
    with pytest.raises(ValueError):evaluate(r,[],"2026-11-18T00:00:00Z",h)
def test_incompatible_truth_protocol():
    r=pilot(snapshot());s=snapshot("2026-11-16");s["protocol_sha256"]="wrong"
    with pytest.raises(ValueError):evaluate(r,[s],"2026-11-17T00:00:00Z")
def test_future_evidence_excluded():
    event={"id":"a","first_observed_at":"2026-11-16T00:00:00Z","published_at":"2026-11-14T00:00:00Z","publication_verified":True,"kind":"price_announcement"}
    assert feature_vector([event],None,"2026-11-15T18:00:00Z")["gpu_price_announcement_count_7d"]==0
def test_unverified_publication_excluded():
    event={"id":"a","first_observed_at":"2026-11-15T00:00:00Z","published_at":"2026-11-14T00:00:00Z","publication_verified":False,"kind":"price_announcement"}
    assert feature_vector([event],None,"2026-11-15T18:00:00Z")["gpu_price_announcement_count_7d"]==0
def test_bls_current_revision_not_backdated():
    b={"first_observed_at":"2026-11-16T00:00:00Z","period_first_observed_at":"2026-11-16T00:00:00Z","observations":[{"value":198}]}
    assert feature_vector([],b,"2026-11-15T18:00:00Z")["electricity_ppi_index"] is None
def test_cold_start_has_no_signal_claim():
    r=readiness([snapshot()])
    assert r["status"]=="gated" and r["new_optimizer_updates"]==0 and r["retained_price_days"]==1
def test_no_relative_skill_for_zero_loss():
    cells=[{"series_id":"x","target_date":"2027-01-01","horizon_days":7,"forecaster":f,"cohort":"primary","pinball":0.,"covered":True,"width":0.} for f in ("signals_111","signals_000")]
    assert paired(cells,"signals_111","signals_000")["skill"] is None
def test_sparse_learners_are_not_fabricated():
    pytest.importorskip("sklearn")
    qs,error=predict_arm([snapshot()],"unknown","2026-11-15T18:00:00Z",7,"111")
    assert qs is None and error["reason"]=="insufficient_retained_price_days"

def test_final_analysis_gate_and_empty_outcomes():
    from compute_forecast.signals_analysis_v6 import summarize
    r=summarize([],[],"2026-11-15T22:00:00Z")
    assert not r["final_gate_open"] and not r["prospective_improvement_established"]
    assert not any(g["improvement_established"] for g in r["group_effects"].values())
def test_block_interval_requires_origins():
    from compute_forecast.signals_analysis_v6 import block_interval
    assert block_interval([-.1]*15)["interval"] is None
def test_holm_retains_registered_three_test_family():
    from compute_forecast.signals_analysis_v6 import holm
    p=holm({"news":.01,"infrastructure":None,"bls":None})
    assert p["news"]==.03 and p["bls"] is None
