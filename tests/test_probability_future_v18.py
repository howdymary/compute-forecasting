"""Explicit synthetic fixtures for future information and commitment contracts."""
import json,pathlib,math
from datetime import date,timedelta
import pytest
from compute_forecast.probability_future_v18 import prepare,validate,score
from compute_forecast.probability_v18 import digest
from compute_forecast.review_v4 import digest as source_digest
def protocol():return json.loads(pathlib.Path("configs/probability-v18-prospective.json").read_text())
def snapshot(day,value=1.):
    contract={"gpu":"A100 40GB","provider":"synthetic_fixture","region":"synthetic","unit":"USD per GPU-hour"}
    row={"id":"grp-v6-"+source_digest(contract)[:20],"family":"A100","date":day,"value":value,"contract":contract,"unit":"USD per GPU-hour","fetched_at":day+"T17:30:00+00:00"}
    return {"captured_at":day+"T18:00:00+00:00","prices":{"date":day,"license":"CC BY 4.0","rows":[row]},"protected_outcomes_loaded":False,"synthetic":True}
def records():return [snapshot((date(2026,11,17)+timedelta(days=i)).isoformat()) for i in range(20)]
def commitment():
    p=protocol();source=records();state=prepare(source,"2026-12-07T00:10:00+00:00",p);assert state["eligible"]
    task=state["tasks"][0];rows=[]
    for method in p["methods"]:
        for h,target in zip(p["horizons"],task["target_dates"]):
            r={"method":method,"task_id":task["task_id"],"series_id":task["series_id"],"horizon_days":h,"target_date":target,"contract_sha256":digest(task["metadata"]["contract"]),"q10":1.,"q50":1.,"q90":1.,"fallback":False}
            if method in ("untuned","ce_selected","crps_selected"):r.update(probabilities=[0.,1.,0.],support_prices=[.9,1.,1.1],probability_sha256=digest([0.,1.,0.]))
            rows.append(r)
    lock={"synthetic":True,"log_levels":[math.log(.9),0,math.log(1.1)]}
    value={"study_id":p["study_id"],"protocol_sha256":digest(p),"model_lock_sha256":digest(lock),"origin":"2026-12-06","issued_at":"2026-12-07T00:10:00+00:00","information_cutoff":"2026-12-06T23:59:59+00:00","input_vintages":[{"captured_at":s["captured_at"],"snapshot_sha256":digest(s)} for s in source],"target_contracts":{task["series_id"]:task["metadata"]["contract"]},"rows":rows,"status":"issued"}
    return value,p,lock
def test_capture_cutoff_and_origin_gate():
    p=protocol();a=prepare(records(),"2026-12-07T00:10:00+00:00",p)
    b=prepare(records()+[snapshot("2026-12-07",9999.)],"2026-12-07T00:10:00+00:00",p)
    assert a["tasks"]==b["tasks"] and a["eligible"]
    assert not prepare(records(),"2026-12-06T23:00:00+00:00",p)["eligible"]
def test_commitment_maturity_and_missing_truth():
    value,p,lock=commitment();validate(value,p,lock)
    result=score(value,records()+[snapshot("2026-12-07")],"2026-12-07T20:00:00+00:00",p,lock);assert not result["cells"]
    result=score(value,records()+[snapshot("2026-12-07")],"2026-12-08T00:10:00+00:00",p,lock)
    assert not result["cells"] and result["status"]=="pending_fixed_analysis_date"
    result=score(value,records()+[snapshot("2026-12-07")],"2027-02-01T00:10:00+00:00",p,lock)
    assert len(result["cells"])==len(p["methods"]) and result["status"]=="pending"
def test_rejects_late_or_contaminated_commitment():
    value,p,lock=commitment();value["issued_at"]="2026-12-07T02:00:00+00:00"
    with pytest.raises(AssertionError):validate(value,p,lock)
    value,p,lock=commitment();value["rows"][0]["outcome"]=1.
    with pytest.raises(AssertionError):validate(value,p,lock)
def test_rejects_changed_contract():
    value,p,lock=commitment();value["rows"][0]["contract_sha256"]="wrong"
    with pytest.raises(AssertionError):validate(value,p,lock)

def test_rejects_probability_or_horizon_change():
    value,p,lock=commitment();value["rows"][0]["probability_sha256"]="wrong"
    with pytest.raises(AssertionError):validate(value,p,lock)
    value,p,lock=commitment()
    for r in value["rows"]:
        if r["horizon_days"]==7:r["horizon_days"]=2;r["target_date"]="2026-12-08"
    with pytest.raises(AssertionError):validate(value,p,lock)

def test_initialization_fallback_keeps_positive_registered_distribution():
    from compute_forecast.probability_future_v18 import forecast_row
    value,p,lock=commitment();task=prepare(records(),"2026-12-07T00:10:00+00:00",p)["tasks"][0]
    row=forecast_row(task,7,"ce_selected",lock,failure_type="SyntheticInitializationError")
    assert row["probabilities"]==[0.,1.,0.] and row["q10"]==row["q50"]==row["q90"]==task["anchor"]
    assert row["fallback"] and not row["request_attempted"]
    assert row["probability_sha256"]==digest(row["probabilities"])
