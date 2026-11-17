"""Independent future gate and forecast-encoding contracts, using explicit synthetic quotes."""
import copy,json
from datetime import date,timedelta
from pathlib import Path
import pytest
from compute_forecast.quantile_future_v20 import effective_protocol,validate,score
from compute_forecast.market_future_v19 import prepare
from compute_forecast.probability_v18 import digest,support
from compute_forecast.quantile_v20 import head_quantiles
RAW=json.loads(Path("configs/quantile-training-v20-prospective.json").read_bytes())
P=effective_protocol(RAW,json.loads(Path("configs/market-state-v19-prospective.json").read_bytes()))
def fixture():
    origin="2026-12-20";records=[]
    for i in reversed(range(30)):
        day=(date.fromisoformat(origin)-timedelta(days=i)).isoformat();at=day+"T17:40:00+00:00";rows=[]
        for provider in ("synthetic-a","synthetic-b","synthetic-c","synthetic-d"):
            for family in ("A100","H100"):
                sid=provider+"-"+family;contract={"provider":provider,"family":family,"kind":"synthetic_fixture"}
                meta={"provider":provider,"family":family,"source_id":"synthetic","gpu_model":family+" fixture","pricing_tier":"spot","instrument_class":"synthetic_test_only","region":"synthetic","gpu_count":1,"gpu_memory_gb":80}
                rows.append({"series_id":sid,"date":day,"available_at":at,"value":1.,"contract":contract,"metadata":meta})
        records.append({"status":"captured","eligible_for_origin":True,"observed_day":day,"retrieved_at":at,"observations":rows,"vintage_sha256":digest(rows)})
    prepared=prepare(records,origin,"2026-12-21T00:05:00+00:00",P)
    assert prepared["eligible"]
    lock={"log_levels":[-.1,0.,.1]};rows=[]
    for t in prepared["tasks"]:
        z=support(t["anchor"],lock["log_levels"]);heads=[[0.,1.,0.]]*3;q,raw,cross=head_quantiles(heads,z)
        for h in P["horizons"]:
            for method in P["methods"]:
                row={"method":method,"series_id":t["series_id"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"contract_sha256":digest(t["contract"]),"q10":1.,"q50":1.,"q90":1.,"fallback":False,"support_prices":z}
                if method.startswith("quantile_head"):row.update(head_probabilities=heads,raw_head_means=raw,raw_crossing=cross)
                elif method!="official_drift":row["parent_probability_vectors"]=heads
                rows.append(row)
    value={"study_id":P["study_id"],"protocol_sha256":digest(P),"model_lock_sha256":digest(lock),"origin":origin,"issued_at":"2026-12-21T00:05:00+00:00","information_cutoff":origin+"T23:59:59.999999+00:00","capture_receipts":records,"price_inputs":prepared["tasks"],"input_vintages":prepared["input_vintages"],"cohort":prepared["cohort"],"rows":rows}
    return value,lock
def test_valid_encodings_and_poisoning():
    v,lock=fixture();validate(v,P,lock)
    bad=copy.deepcopy(v);bad["rows"][0]["probabilities"]=[0.,1.,0.]
    with pytest.raises(AssertionError):validate(bad,P,lock)
    bad=copy.deepcopy(v);bad["price_inputs"][0]["context"][-1]["value"]=2.
    with pytest.raises(AssertionError):validate(bad,P,lock)
    bad=copy.deepcopy(v);bad["rows"].pop()
    with pytest.raises(AssertionError):validate(bad,P,lock)
def test_fixed_analysis_and_signed_receipt_before_truth():
    v,lock=fixture()
    class Poison:
        def __iter__(self):raise AssertionError("Truth read before gate")
    result=score(v,Poison(),"2027-04-11T23:59:59+00:00",P,lock)
    assert result["status"]=="pending_fixed_analysis_date" and not result["outcomes_loaded"]
    result=score(v,Poison(),"2027-04-12T00:00:01+00:00",P,lock)
    assert result["status"]=="pending_verified_publication_receipt"
    receipt={"commitment_sha256":digest(v),"created_at":"2026-12-21T01:01:00+00:00"}
    assert score(v,Poison(),"2027-04-12T00:00:01+00:00",P,lock,receipt)["status"]=="ineligible_late_publication"
