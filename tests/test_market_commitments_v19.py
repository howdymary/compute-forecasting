"""Explicitly synthetic source-contract fixtures, never published market observations."""
from datetime import date,timedelta
from pathlib import Path
from copy import deepcopy
import json
from compute_forecast.market_future_v19 import prepare,validate,snapshots
from compute_forecast.probability_v18 import digest,support,quantiles
P=json.loads(Path("configs/market-state-v19-prospective.json").read_text())
def fixture():
    records=[]
    for i in range(30):
        day=(date(2026,11,21)+timedelta(days=i)).isoformat();at=day+"T17:40:00+00:00";rows=[]
        for provider in ("synthetic-a","synthetic-b","synthetic-c"):
            for family in ("H100","A100"):
                for node in (1,8):
                    contract={"provider":provider,"family":family,"gpu_count":node,"region":"synthetic-region"};sid="synthetic-"+digest(contract)[:20]
                    metadata={"source_id":"synthetic-contract-fixture","provider":provider,"family":family,"gpu_model":family+"-synthetic","instrument_class":"provider_rate_card","pricing_tier":"on_demand","region":"synthetic-region","gpu_count":node,"gpu_memory_gb":80}
                    rows.append({"date":day,"available_at":at,"series_id":sid,"value":1+i*.001,"contract":contract,"metadata":metadata})
        records.append({"status":"captured","eligible_for_origin":True,"observed_day":day,"retrieved_at":at,"vintage_sha256":digest(rows),"observations":rows})
    return records
def commitment():
    records=fixture();x=prepare(records,"2026-12-20","2026-12-21T00:05:00+00:00",P);assert x["eligible"],x["reasons"]
    lock={"log_levels":[(i-9)*.01 for i in range(19)]};rows=[]
    for t in x["tasks"]:
        for h in P["horizons"]:
            for method in P["methods"]:
                rows.append({"method":method,"series_id":t["series_id"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"contract_sha256":digest(t["contract"]),"q10":t["anchor"],"q50":t["anchor"],"q90":t["anchor"]})
    for r in rows:
        if r["method"] in ("price","market","untuned_price","untuned_market"):
            task=next(t for t in x["tasks"] if t["series_id"]==r["series_id"])
            r["support_prices"]=support(task["anchor"],lock["log_levels"]);r["probabilities"]=[float(i==9) for i in range(19)]
    c={"information_cutoff":"2026-12-20T23:59:59.999999+00:00","input_vintages":x["input_vintages"],"study_id":P["study_id"],"protocol_sha256":digest(P),"model_lock_sha256":digest(lock),"origin":"2026-12-20","issued_at":"2026-12-21T00:05:00+00:00","capture_receipts":records,"cohort":x["cohort"],"price_inputs":x["tasks"],"rows":rows}
    return c,lock
def test_complete_matched_synthetic_commitment():
    c,lock=commitment();assert validate(c,P,lock) is c and len(c["rows"])==12*3*10
def test_flag_cannot_override_collection_window():
    records=fixture();records[-1]["retrieved_at"]="2026-12-20T23:00:00+00:00"
    assert "2026-12-20" not in snapshots(records,"2026-12-20T23:59:59+00:00",P)
def test_metadata_revision_is_not_same_contract():
    records=fixture();records[0]["observations"][0]["metadata"]["region"]="changed-region"
    x=prepare(records,"2026-12-20","2026-12-21T00:05:00+00:00",P)
    assert any(r["reason"]=="contract_or_metadata_revision" for r in x["exclusions"])
def test_incomplete_method_cannot_be_hidden():
    import pytest
    c,lock=commitment();c["rows"].pop()
    with pytest.raises(AssertionError):validate(c,P,lock)
def test_future_truth_cannot_enter_commitment():
    import pytest
    c,lock=commitment();c["rows"][0]["outcome"]=1
    with pytest.raises(AssertionError):validate(c,P,lock)

def test_model_inputs_must_reconstruct_from_receipts():
    import pytest
    c,lock=commitment();c["price_inputs"][0]["anchor"]=9999
    with pytest.raises(AssertionError):validate(c,P,lock)
