"""Causal and missing-calendar invariants, executed on the hosted study runner."""
from datetime import date, timedelta
import math
import pytest
pytest.importorskip("modal")
np = pytest.importorskip("numpy")
from compute_forecast.representation_study import features_at, forecast_series

def fixture_values():
    start=date(2026,1,20)
    return {start+timedelta(days=i): 2.0+i*.002+.01*math.sin(i/3) for i in range(180)}

def test_future_prices_cannot_change_a_historical_forecast():
    origin=date(2026,5,9)
    observed=fixture_values()
    prefix={d:v for d,v in observed.items() if d<=origin}
    contaminated={**prefix,**{d:1e7*(i+1) for i,d in enumerate(observed) if d>origin}}
    config={"space":"log","aux":"target_only","days":56,"alpha":1}
    expected,reason=forecast_series(prefix,origin,7,config,{})
    actual,other=forecast_series(contaminated,origin,7,config,{})
    assert expected is not None and reason is None and other is None
    assert actual == pytest.approx(expected,rel=1e-12)

def test_lags_use_calendar_days_and_do_not_bridge_missing_dates():
    day=date(2026,7,8)
    values={day:4.0,day-timedelta(days=2):2.0,day-timedelta(days=3):1.0}
    vector=features_at(values,day,"level")
    assert math.isnan(vector[1])
    assert vector[2]==3.0
    assert vector[-1]==pytest.approx(1/7)

def test_every_prequential_fit_only_uses_matured_labels(monkeypatch):
    import compute_forecast.representation_study as study
    start=date(2026,1,20); origin=date(2026,5,9); horizon=7
    values={start+timedelta(days=i): float(100+i) for i in range(180)}
    calls=[]
    def checked(x,y,query,alpha):
        assert max(row[0] for row in x) <= query[0]-horizon
        assert set(y)=={float(horizon)}
        calls.append(query[0])
        return float(horizon)
    monkeypatch.setattr(study,"ridge_prediction",checked)
    result,reason=study.forecast_series(values,origin,horizon,{"space":"level","aux":"target_only","days":28,"alpha":1},{})
    assert reason is None and result is not None
    assert len(calls)>5 and min(calls)<max(calls)
    assert all(q>0 for q in result) and result==sorted(result)

def test_unsupported_auxiliary_data_is_an_explicit_fallback():
    result,reason=forecast_series(fixture_values(),date(2026,5,9),3,{"space":"log","aux":"fixed_basket","days":28,"alpha":100},{})
    assert result is None and reason=="unsupported_auxiliary_contract"
