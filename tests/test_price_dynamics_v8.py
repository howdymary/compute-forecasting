"""Scientific contracts use explicitly synthetic prices, never historical fixtures."""
from datetime import datetime,timezone,timedelta,date
import pytest
from compute_forecast.price_dynamics_v8 import *
def prices(n=100):
    return {(date(2026,1,1)+timedelta(days=i)).isoformat():2+(.01*i) for i in range(n)}
def test_future_data_poisoning():
    v=prices()
    with pytest.raises(ValueError):history(v,"2026-02-01")
    with pytest.raises(ValueError):replay({"2026-02-02":{"a":2}},"2026-02-01",1,[1,2,3])
def test_pool_does_not_mix_instruments():
    v=prices();at=max(v);meta={"series_id":"s","source_id":"a","instrument_class":"spot","pricing_tier":"spot","family":"A100","unit":"USD per GPU-hour"}
    foreign={"meta":{**meta,"series_id":"x","instrument_class":"list"},"values":{d:p*100 for d,p in v.items()}}
    q,a=pooled(v,meta,{"x":foreign},at,7,[1,2,3])
    assert a["donor_series"]==0 and q==sorted(q)
def test_pool_level_scaling_and_boundary():
    v=prices();at=max(v);meta={"series_id":"s","source_id":"a","instrument_class":"spot","pricing_tier":"spot","family":"A100","unit":"USD per GPU-hour"}
    q,_=pooled(v,meta,{},at,7,[1,2,3])
    q2,_=pooled({d:x*10 for d,x in v.items()},meta,{},at,7,[10,20,30])
    assert q2==pytest.approx([10*x for x in q])
def test_calibration_maturity_and_horizon():
    rows=[{"origin":"2026-01-01","target":"2026-02-02","horizon":7,"truth":2,"quantiles":[1,2,3]}]
    with pytest.raises(ValueError):calibrate([1,2,3],rows,"2026-02-01",7)
    q,d=calibrate([1,2,3],[],"2026-02-01",7)
    assert q==[1,2,3] and d["fallback"]
def test_calibration_actual_forecast_errors():
    rows=[{"origin":"2026-01-01","target":"2026-01-08","horizon":7,"truth":10,"quantiles":[8,9,11]} for _ in range(24)]
    q,d=calibrate([8,9,11],rows,"2026-02-01",7)
    assert q==[10,10,10] and d["n"]==24
    assert calibrate([8,9,11],rows,"2026-02-01",3)[1]["n"]==0
def test_no_unattested_exit():
    days={"2026-01-01":{"a":1,"b":3},"2026-01-02":{"a":1}}
    q,d=replay(days,"2026-01-02",1,[1,1,1],minimum=1)
    assert d["rejected_membership_uncertain"]==1 and d["fallback"]
def test_deterministic_observed_repricing():
    days={f"2026-01-{i:02}":{"a":1+i/100,"b":3+i/100} for i in range(1,20)}
    a=replay(days,"2026-01-19",1,[1,2,3]);b=replay(days,"2026-01-19",1,[1,2,3])
    assert a==b and a[1]["scenarios"]==18 and not a[1]["fallback"]
def test_empty_and_invalid():
    with pytest.raises(ValueError):ordered([3,2,1])
    with pytest.raises(ValueError):ordered([0,1,2])
    assert replay({},"2026-01-01",7,[1,2,3])[1]["fallback"]
def test_matched_and_zero_baseline():
    cells=[{"method":m,"series_id":"s","origin":"2026-01-01","horizon":7,"loss":l} for m,l in (("A",0),("C",1))]
    assert paired(cells,"C","A",draws=10)["skill"] is None
    with pytest.raises(ValueError):paired(cells[:1],"C","A",draws=10)
def test_issuance_before_resolution():
    c={"cutoff":"2026-11-22T23:59:59+00:00","issued_at":"2026-11-23T00:10:00+00:00","deadline":"2026-11-23T00:30:00+00:00","snapshot_sha256":"x","configuration_sha256":"y","forecasts":[{"resolution_at":"2026-11-24T00:00:00+00:00","quantiles":[1,2,3]}]}
    assert validate_commitment(c,"2026-11-23T00:20:00+00:00")
    c["forecasts"][0]["resolution_at"]="2026-11-22T00:00:00+00:00"
    with pytest.raises(ValueError):validate_commitment(c,"2026-11-23T00:20:00+00:00")
def test_news_cap_is_not_frequency():
    from compute_forecast.news_measurement_v8 import measurement
    v=measurement([{"url":"https://example.com/a"}]*6,{"query":"q","numResults":6},"2026-11-16")
    assert v["cap_reached"] and v["deduplicated_events"]==1 and "not no market" in v["zero_means"]

def test_notebook_renderer_integration():
    from compute_forecast.explore_ui import HTML
    assert HTML.count("function dynamicsPage()")==1
    assert HTML.count('<script>')==1 and HTML.count('</script>')==1
    assert "dynamics:dynamicsPage" in HTML
