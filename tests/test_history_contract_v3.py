"""Publication boundaries and prospective gates are scientific invariants."""
import copy
from datetime import datetime,timezone
import pytest
from compute_forecast.history_contract_v3 import APPROVED,LICENSE_SHA,digest,validate_history
from compute_forecast.prospective_control_v3 import clock_gate,score_locked
def fixture():
    # Synthetic values belong only to this unit test, never application payloads.
    points=[{"date":"2026-11-04","value":1.0},{"date":"2026-11-06","value":1.5}]
    return {"kind":"independent_historical_context","benchmark_overlay_allowed":False,"benchmark_input_claim":False,"cutoff":"2026-11-06","source":{"license_sha256":LICENSE_SHA,"license":"CC BY 4.0","private_pack_values_published":False},"series":[{"benchmark_series_context":sid,"unit":"USD per GPU-hour","market":"hyperscaler spot advertised offers","benchmark_overlay_allowed":False,"points":copy.deepcopy(points),"points_sha256":digest(points),"observations":2,"missing_calendar_days":1} for sid in APPROVED]}
def test_permitted_context_keeps_gaps():
    h=fixture();assert validate_history(h)["series"][0]["missing_calendar_days"]==1
@pytest.mark.parametrize("mutation",["permission","overlay","future","duplicate","nonfinite","incompatible","filled_gap","hash"])
def test_publication_rejects_unsafe_or_incompatible_history(mutation):
    h=fixture();s=h["series"][0]
    if mutation=="permission":h["source"]["license_sha256"]="unverified"
    if mutation=="overlay":h["benchmark_overlay_allowed"]=True
    if mutation=="future":s["points"][1]["date"]="2026-11-07"
    if mutation=="duplicate":s["points"][1]["date"]=s["points"][0]["date"]
    if mutation=="nonfinite":s["points"][0]["value"]=float("inf")
    if mutation=="incompatible":s["unit"]="USD per instance-hour"
    if mutation=="filled_gap":s["missing_calendar_days"]=0
    if mutation=="hash":s["points"][0]["value"]=2.0
    with pytest.raises(ValueError):validate_history(h)
def test_future_truth_gate_precedes_every_forecast_access():
    class Forbidden(dict):
        def __getitem__(self,k):raise AssertionError("Read protected input before maturity")
    with pytest.raises(ValueError,match="sealed"):score_locked(Forbidden(),Forbidden(),Forbidden(),datetime(2026,11,15,tzinfo=timezone.utc))
def test_maturity_is_utc_and_does_not_imply_available_truth():
    clock_gate(datetime(2026,11,23,tzinfo=timezone.utc))
    with pytest.raises(ValueError):clock_gate(datetime(2026,11,23))
    with pytest.raises(ValueError,match="Committed"):score_locked({}, {}, {},datetime(2026,11,23,tzinfo=timezone.utc))
