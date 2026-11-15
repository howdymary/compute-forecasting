import pytest
pytest.importorskip("modal")
from datetime import datetime
from compute_forecast.prospective_v2 import calendar_dates
def test_pacific_evening_issuance_uses_future_utc_calendar_targets():
    issued=datetime.fromisoformat("2026-11-14T18:30:00-08:00")
    origin,targets=calendar_dates(issued)
    assert origin.isoformat()=="2026-11-15"
    assert [t.isoformat() for t in targets]==["2026-11-16","2026-11-18","2026-11-22"]
def test_naive_issuance_is_rejected():
    with pytest.raises(ValueError):calendar_dates(datetime(2026,11,15))
