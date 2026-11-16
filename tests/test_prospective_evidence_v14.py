"""Synthetic commitment gates; no fixture prices represent real market observations."""
import pytest
from compute_forecast.prospective_evidence_v14 import validate_commitment
from compute_forecast.direct_forecast_v12 import digest
def fixture():
    p={"study_id":"synthetic-v14-panel","first_eligible_origin":"2026-12-06","issuance_deadline_minutes_after_origin":30,"horizons":[1,3,7]}
    lock={"operational_seed":17,"locked_at":"2026-12-01T00:00:00Z","price_only":{"checkpoint_sha256":"synthetic-p"},"price_evidence":{"checkpoint_sha256":"synthetic-e"}}
    rows=[{"method":m,"series_id":"synthetic-a100","horizon_days":1,"target_date":"2026-12-07","q10":1,"q50":2,"q90":3,"checkpoint_sha256":lock[m]["checkpoint_sha256"]} for m in ("price_only","price_evidence")]
    c={"study_id":p["study_id"],"protocol_sha256":digest(p),"origin":"2026-12-06","issued_at":"2026-12-07T00:10:00Z","model_lock_sha256":digest(lock),"input_snapshot_hashes":["synthetic"],"rows":rows}
    return p,lock,c
def test_paired_commitment_requires_advance_lock_and_matched_cells():
    p,lock,c=fixture();assert validate_commitment(c,p,lock)==c
    c["rows"].pop()
    with pytest.raises(AssertionError,match="Unmatched"):validate_commitment(c,p,lock)
def test_late_issuance_is_rejected():
    p,lock,c=fixture();c["issued_at"]="2026-12-07T00:31:00Z"
    with pytest.raises(AssertionError):validate_commitment(c,p,lock)
