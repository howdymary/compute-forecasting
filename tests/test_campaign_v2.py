"""Causal and numerical contracts for the separately registered v2 study."""
from datetime import date,timedelta
import math
import pytest
pytest.importorskip("modal")
pytest.importorskip("numpy")
from compute_forecast.campaign_v2 import REGISTRY,protocol,validate_origin,audit_values,calibrated

def test_registered_labels_do_not_cross_training_boundary_or_opened_final():
    p=protocol()
    assert all(date.fromisoformat(o)+timedelta(days=7)<=date.fromisoformat(p["train_last_label"]) for o in p["training_origins"])
    for origin in p["training_origins"]+p["development_origins"]+p["evaluation_origins"]:validate_origin(origin)
    for origin in ("2026-10-25","2026-11-06","2026-11-07"):
        with pytest.raises(ValueError):validate_origin(origin)

def test_observation_recency_does_not_claim_quote_verification():
    a=audit_values({date(2026,7,1):1.0,date(2026,7,3):1.0},"2026-07-04")
    assert a["observations"]==2 and a["missing_calendar_days"]==2 and a["price_changes"]==0
    assert a["days_since_last_observation"]==1 and a["verified_quote_age_days"] is None

def test_future_values_cannot_change_past_ar_forecast():
    at=date(2026,7,24);v={at-timedelta(days=k):2+math.sin(k*.3)*.1 for k in range(100)}
    c={"family":"ar","days":56,"alpha":100}
    before,reason=calibrated(v,at,7,c)
    altered={**v,at+timedelta(days=1):1e6,at+timedelta(days=7):1e-6}
    after,why=calibrated(altered,at,7,c)
    assert reason is None and why is None and before==after
    assert 0<before[0]<=before[1]<=before[2]

def test_embedded_remote_protocol_matches_committed_configuration():
    import json
    from pathlib import Path
    assert protocol()==json.loads(Path("configs/campaign-v2.json").read_text())
