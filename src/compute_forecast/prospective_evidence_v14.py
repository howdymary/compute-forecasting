"""Separate paired-panel gate; reuses the existing locked maturity evaluator."""
from datetime import date,timedelta
from .direct_future_v12 import utc,issuance_status,score
from .direct_forecast_v12 import digest
def validate_commitment(value,protocol,model_lock):
    assert value["study_id"]==protocol["study_id"] and value["protocol_sha256"]==digest(protocol)
    assert value["origin"]>=protocol["first_eligible_origin"]
    assert issuance_status(value["origin"],value["issued_at"],protocol)=="eligible"
    assert value["model_lock_sha256"]==digest(model_lock)
    assert model_lock["operational_seed"]==17
    assert utc(model_lock["locked_at"])<utc(value["issued_at"])
    assert value["input_snapshot_hashes"] and all(v for v in value["input_snapshot_hashes"])
    groups={}
    for row in value["rows"]:
        assert row["target_date"]==(date.fromisoformat(value["origin"])+timedelta(days=row["horizon_days"])).isoformat()
        assert row["horizon_days"] in protocol["horizons"] and row["q10"]>0 and row["q10"]<=row["q50"]<=row["q90"]
        assert row["method"] in ("price_only","price_evidence") or row.get("reference")
        if row["method"] in ("price_only","price_evidence"):
            assert row["checkpoint_sha256"]==model_lock[row["method"]]["checkpoint_sha256"]
            groups.setdefault(row["method"],set()).add((row["series_id"],row["horizon_days"]))
    assert groups.get("price_only") and groups["price_only"]==groups.get("price_evidence"),"Unmatched primary arms"
    return value
def evaluate(value,snapshots,at,protocol,model_lock):
    validate_commitment(value,protocol,model_lock)
    return score(value,snapshots,at,protocol)
