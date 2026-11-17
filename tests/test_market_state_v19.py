import copy,json,pytest
from compute_forecast.market_state_v19 import check_asof,market_features,prompt,normalize_latest
def row(provider="a",region="us-east",value=2.,sid="a"):
    return {"series_id":sid,"date":"2026-10-01","value":value,"metadata":{"source_id":"test","provider":provider,"gpu_model":"A100 40GB","instrument_class":"neocloud_rate_card","pricing_tier":"on_demand","region":region,"gpu_count":1,"gpu_memory_gb":40}}
def task():
    t=row();return {**t,"origin":t["date"],"anchor":t["value"],"context":[{"date":t["date"],"value":t["value"]}],"context_missing_days":41,"market_state":{"log_anchor_to_peer_median":.2},"outcomes":[12345.,12345.,12345.],"arm":"market"}
def test_future_observation_refused():
    r=row();r["date"]="2026-10-02"
    with pytest.raises(ValueError):check_asof([r],"2026-10-01")
def test_late_availability_refused():
    r=row();r["available_at"]="2026-10-02T00:00:00Z"
    with pytest.raises(ValueError):check_asof([r],"2026-10-01")
def test_protected_date_refused():
    r=row();r["date"]="2026-11-10"
    with pytest.raises(ValueError):check_asof([r],"2026-11-17")
def test_unknown_region_is_not_comparable():
    t=task();t["metadata"]["region"]=None
    f=market_features(t,[row("b",None,1.,"b"),row("c",None,3.,"c")],t["origin"])
    assert f["comparable_provider_count"]==0 and f["log_anchor_to_peer_median"] is None
def test_matching_cross_provider_prices():
    t=task();f=market_features(t,[row("b",value=1.,sid="b"),row("c",value=3.,sid="c")],t["origin"])
    assert f["comparable_provider_count"]==2 and f["log_anchor_to_peer_median"]==0 and f["peer_price_rank"]==.5
def test_prompt_outcomes_and_later_catalog_fields_never_leak():
    t=task();t["metadata"]["last_value_to_as_of"]=99999;t["metadata"]["last_date"]="2099-01-01"
    s=prompt(t,7);assert "12345" not in s and "99999" not in s and "2099" not in s
def test_arm_shared_information_identical():
    t=task();b=json.loads(prompt(t,7));t["arm"]="price";a=json.loads(prompt(t,7))
    assert a["history"]==b["history"] and a["shared_history_summary"]==b["shared_history_summary"]
    assert a["market_state"]["values"]["log_anchor_to_peer_median"] is None and b["market_state"]["values"]["log_anchor_to_peer_median"]==.2
def test_nonfinite_feature_refused():
    t=task();t["market_state"]["log_anchor_to_peer_median"]=float("nan")
    with pytest.raises(ValueError):prompt(t,7)
def test_previous_day_capture_retains_its_real_day():
    p={"date":"2026-11-16","generated_at":"2026-11-16T18:00:00Z","offers":[{"provider":"a","gpu":"h100-sxm","kind":"on-demand","vram_gb":80,"usd_hr":2.,"fetched_at":"2026-11-16T17:00:00Z"}]}
    h={"snapshot_date":"2026-11-16","provider_freshness":{"a":{"status":"current"}}}
    v=normalize_latest(p,h,"2026-11-17T07:00:00Z","source","health")
    assert v["rows"][0]["date"]=="2026-11-16" and v["rows"][0]["available_at"].startswith("2026-11-17")
def test_conflicting_current_quote_not_averaged():
    p={"date":"2026-11-16","generated_at":"2026-11-16T18:00:00Z","offers":[{"provider":"a","gpu":"h100-sxm","kind":"on-demand","usd_hr":v,"fetched_at":"2026-11-16T17:00:00Z"} for v in (2.,3.)]}
    h={"snapshot_date":"2026-11-16","provider_freshness":{"a":{"status":"current"}}}
    v=normalize_latest(p,h,"2026-11-16T19:00:00Z","s","h");assert not v["rows"] and v["excluded"][0]["reason"]=="ambiguous_same_contract_prices"
