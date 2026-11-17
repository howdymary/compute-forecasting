"""Locked prospective probability commitments; independent of existing future panels."""
from datetime import date,datetime,timedelta
import math
from .probability_v18 import digest,quantiles
from .direct_future_v12 import utc,issuance_status,tasks_at,score as score_contracts
from .evidence_future_v15 import source_snapshots
def origin_index(origin,p):
    first=date.fromisoformat(p["first_eligible_origin"]);day=date.fromisoformat(origin);delta=(day-first).days
    return delta//7 if delta>=0 and delta%7==0 and day.weekday()==6 and delta//7<p["limits"]["max_weekly_origins"] else None
def prepare(records,at,p):
    snapshots,excluded=source_snapshots(records,at)
    day=utc(at).date();origin=(day-timedelta(days=(day.weekday()+1)%7)).isoformat()
    tasks,failures=tasks_at(snapshots,origin,p)
    for t in tasks:t["metadata"]["benchmark_contract"]=t["metadata"]["contract"]
    reasons=[]
    if origin_index(origin,p) is None:reasons.append("outside_registered_eight_week_window")
    timing=issuance_status(origin,at,p)
    if timing!="eligible":reasons.append(timing)
    if not tasks:reasons.append("no_contract_has_origin_quote_and_twenty_retained_days")
    return {"origin":origin,"eligible":not reasons,"reasons":reasons,"tasks":tasks,"snapshots":snapshots,"failures":failures,"excluded":excluded,"latest_verified_collection_day":max((s["prices"]["date"] for s in snapshots),default=None)}
def validate(value,p,lock):
    assert value["study_id"]==p["study_id"] and value["protocol_sha256"]==digest(p) and value["model_lock_sha256"]==digest(lock)
    assert origin_index(value["origin"],p) is not None
    assert issuance_status(value["origin"],value["issued_at"],p)=="eligible"
    assert value["information_cutoff"]==value["origin"]+"T23:59:59+00:00"
    assert all(utc(s["captured_at"])<=utc(value["information_cutoff"]) for s in value["input_vintages"])
    keys=[(r["method"],r["series_id"],r["horizon_days"]) for r in value["rows"]];assert len(keys)==len(set(keys))
    assert {r["method"] for r in value["rows"]}==set(p["methods"])
    reference={(r["series_id"],r["horizon_days"]) for r in value["rows"] if r["method"]=="untuned"}
    assert 0<len(reference)<=p["limits"]["max_targets"]*3
    for method in p["methods"]:
        assert {(r["series_id"],r["horizon_days"]) for r in value["rows"] if r["method"]==method}==reference
    for row in value["rows"]:
        assert row["contract_sha256"]==digest(value["target_contracts"][row["series_id"]]),"Target contract changed"
        assert "outcome" not in row and "loss" not in row,"Future truth must never enter issuance"
        assert all(math.isfinite(row[k]) for k in ("q10","q50","q90")) and 0<row["q10"]<=row["q50"]<=row["q90"]
        assert row["target_date"]==(date.fromisoformat(value["origin"])+timedelta(days=row["horizon_days"])).isoformat()
        if row["method"] in ("untuned","ce_selected","crps_selected"):assert quantiles(row["probabilities"],row["support_prices"])==[row[k] for k in ("q10","q50","q90")]
    return value
def score(value,records,at,p,lock):
    validate(value,p,lock);snapshots,_=source_snapshots(records,at)
    result=score_contracts(value,snapshots,at,p)
    result["classification"]="Prospective individual-contract transfer; not competition medians"
    return result
