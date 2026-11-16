"""Synthetic contract tests; none of these numbers are historical GPU observations."""
import copy,json
import pytest
from compute_forecast.evidence_v14 import feature_at,messages,conversation
def release():
    return {"status":"qualified_pending_spot_check","series_id":"PCU221122221122","source_url":"https://example.test/archive.pdf","available_at":"2026-07-15T12:30:00Z","first_observed_at":"2026-11-16T21:00:00Z","retrieved_at":"2026-11-16T21:00:00Z","content_sha256":"synthetic","reference_period":"2026-06","values":{"periods":["2026-02","2026-03","2026-04","2026-05","2026-06"],"indices":[100,101,102,103,104],"source_row_sha256":"synthetic"}}
def task():
    return {"origin":"2026-07-14","anchor":2.0,"metadata":{"series_id":"synthetic-a100","gpu_model":"A10040GB","instrument_class":"synthetic","benchmark_contract":"synthetic"},"context":[{"date":"2026-07-14","value":2.0}],"context_missing_days":41,"outcomes":[2.0,2.1,1.9],"target_dates":["2026-07-15","2026-07-17","2026-07-21"],"bls":None}
def test_original_release_cannot_arrive_before_publication():
    r=release();assert feature_at([r],"2026-07-14") is None
    f=feature_at([r],"2026-07-15");assert f["reference_period"]=="2026-06" and f["first_observed_at"].startswith("2026-11-16")
def test_latest_failed_release_does_not_silently_carry_an_older_vintage():
    a=release();b={**a,"available_at":"2026-08-13T12:30:00Z","status":"unavailable"}
    assert feature_at([a,b],"2026-08-14") is None
def test_evidence_poisoning_and_label_leakage():
    t=task();t["bls"]=feature_at([release()],"2026-07-15")
    with pytest.raises(ValueError,match="Future economic"):messages(t,"price_evidence")
    t["context"].append({"date":"2026-07-15","value":999})
    with pytest.raises(ValueError,match="Future observation"):messages(t,"price_only")
def test_arms_share_actual_labels_but_not_economic_inputs():
    t=task();r=release();r["available_at"]="2026-07-10T12:30:00Z";t["bls"]=feature_at([r],t["origin"])
    a=conversation(t,"price_only");b=conversation(t,"price_evidence")
    assert a[-1]==b[-1] and a[0]==b[0]
    x,y=json.loads(a[1]["content"]),json.loads(b[1]["content"])
    assert x["history"]==y["history"] and x["supplementary"]["bls"] is None and y["supplementary"]["bls"]
    assert "outcomes" not in a[1]["content"] and "outcomes" not in b[1]["content"]
