"""All values here are synthetic contract fixtures, never market observations."""
import asyncio,copy,json
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import pytest
from compute_forecast.review_v4 import digest
from compute_forecast.interval_v4 import empirical_interval
from compute_forecast.vintage_v4 import TARGET,LICENSE_SHA,validate_snapshot,retain,select_snapshot
from compute_forecast.prospective_panel_v4 import protocol,origin_gate,score_locked,reference
def snapshot(points=None):
    return {"schema_version":4,"retrieved_at":"2000-02-01T00:00:00+00:00","cutoff":"2000-01-31","target_definition":TARGET,"source":{"license_sha256":LICENSE_SHA},"series":[{"id":"hubbard-independent-a100-40","points":points or [{"date":"2000-01-01","value":1.}],"auxiliary":{}}],"source_objects":[]}
def test_snapshot_permission_missingness_and_protected_dates():
    v=snapshot();assert validate_snapshot(v) is v
    bad=copy.deepcopy(v);bad["source"]["license_sha256"]="wrong"
    with pytest.raises(ValueError):validate_snapshot(bad)
    bad=copy.deepcopy(v);bad["series"][0]["points"]*=2
    with pytest.raises(ValueError):validate_snapshot(bad)
    bad=copy.deepcopy(v);bad["cutoff"]="2026-11-10";bad["series"][0]["points"]=[{"date":"2026-11-10","value":1.}]
    with pytest.raises(ValueError,match="protected"):validate_snapshot(bad)
def test_append_only_vintage_retains_revisions(tmp_path):
    a=snapshot();first=retain(tmp_path,a);b=copy.deepcopy(a);b["retrieved_at"]="2000-02-02T00:00:00+00:00";b["series"][0]["points"][0]["value"]=1.1
    second=retain(tmp_path,b)
    assert first["snapshot_id"]!=second["snapshot_id"]
    assert second["revisions"][0]["previous"]==1.
    assert len([p for p in tmp_path.glob("*.json") if not p.name.endswith(".receipt.json")])==2
def test_snapshot_selection_respects_capture_time(tmp_path):
    retain(tmp_path,snapshot())
    assert select_snapshot(tmp_path,"2000-01-15") is None
    assert select_snapshot(tmp_path,"2000-02-02")["value"]["cutoff"]=="2000-01-31"
def test_weighted_interval_uses_matured_labels_and_refuses_later_inputs():
    at=date(2000,6,1);v={at-timedelta(days=i):2.+i*.001 for i in range(180)}
    result=empirical_interval(v,at,7)
    assert result["status"]=="completed" and result["last_label_date"]<=at.isoformat()
    assert result["quantiles"]==sorted(result["quantiles"]) and not result["coverage_guarantee"]
    v[at+timedelta(days=1)]=2.
    with pytest.raises(ValueError):empirical_interval(v,at,7)
def test_interval_insufficient_residuals_are_pending():
    at=date(2000,1,10);v={at-timedelta(days=i):1. for i in range(9)}
    assert empirical_interval(v,at,7)["quantiles"] is None
def test_origin_cannot_be_backdated_or_issued_early():
    p=protocol()
    with pytest.raises(ValueError):origin_gate(p["origins"][0],datetime(2026,11,15,tzinfo=timezone.utc),p)
    with pytest.raises(ValueError):origin_gate(p["origins"][0],datetime(2026,11,24,tzinfo=timezone.utc),p)
    origin_gate(p["origins"][0],datetime(2026,11,23,1,tzinfo=timezone.utc),p)
    assert p["validation_lags_days"]==[8,15]
def commitment():
    row={"series_id":"hubbard-independent-a100-40","origin":"2026-11-23","target_date":"2026-11-24","horizon_days":1,"q10":.9,"q50":1.,"q90":1.1}
    return {"origin":"2026-11-23","registration_sha256":digest(protocol()),"target_definition_sha256":digest(TARGET),"rows":[{**row,"forecaster":"direct_last_value"},{**row,"forecaster":"test"}],"failures":[]}
def test_locked_scoring_clock_and_changed_hash():
    r=commitment();sha=digest(r)
    with pytest.raises(ValueError,match="matured"):score_locked(r,sha,None,datetime(2026,11,24,tzinfo=timezone.utc))
    r["rows"][0]["q50"]=1.01
    with pytest.raises(ValueError,match="changed"):score_locked(r,sha,None,datetime(2026,12,1,tzinfo=timezone.utc))
def test_scoring_missing_outcomes_pending_and_duplicate_rejected():
    r=commitment();truth=snapshot([{"date":"2026-11-24","value":1.}]);truth["cutoff"]="2026-11-24";truth["retrieved_at"]="2026-11-25T00:00:00+00:00"
    now=datetime(2026,12,1,tzinfo=timezone.utc)
    result=score_locked(r,digest(r),truth,now);assert result["scores"]["test"]["n_cells"]==1
    truth["series"][0]["points"]=[]
    assert score_locked(r,digest(r),truth,now)["status"]=="pending_missing_outcomes"
    r["rows"].append(r["rows"][0])
    with pytest.raises(ValueError,match="Duplicate"):score_locked(r,digest(r),truth,now)
def test_learning_gate_creates_no_model_client(tmp_path):
    from compute_forecast.campaign_v2 import REGISTRY
    from compute_forecast.learning_v4 import train
    ids=[c["id"] for c in REGISTRY]
    def task(identifier,origin,phase):
        return {"task_id":identifier,"origin":origin,"phase":phase,"reward_label_end":origin,"observation":{},"scale":1.,"validation":{c:{"loss":0.,"last_label_date":origin,"n_cells":1} for c in ids},"future_evaluator_only":{c:{"loss":0.,"cells":1} for c in ids}}
    tasks=[task("training","2000-01-01","training"),task("development","2000-02-01","development")]
    r=asyncio.run(train(tasks,tmp_path/"private",tmp_path/"public"))
    assert r["actual_optimizer_updates"]==0 and r["model_clients_created"]==0
def test_packet_format_has_fixed_character_budget():
    from compute_forecast.feedback_v4 import padded
    assert len(padded("synthetic"))==len(padded("x"*5000))==900
