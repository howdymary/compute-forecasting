"""Execution contracts for the registered paired future panel; no historical retuning."""
from __future__ import annotations
import hashlib,json,math
from datetime import datetime,date,timedelta,timezone
from .direct_forecast_v12 import digest
from .direct_future_v12 import utc,tasks_at,issuance_status
from .evidence_v14 import feature_at
from .prospective_evidence_v14 import validate_commitment,evaluate
def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str,separators=(",",":"),allow_nan=True).encode()).hexdigest()
def source_snapshots(records,at):
    accepted=[];excluded=[]
    for s in sorted(records,key=lambda s:s.get("captured_at","")):
        try:
            stamp=utc(s["captured_at"]);day=s["prices"]["date"]
            assert stamp<=utc(at) and stamp.date().isoformat()==day
            assert datetime.fromisoformat(day).date()>date(2026,11,13)
            assert 17<=stamp.hour<19
            assert s["prices"]["license"]=="CC BY 4.0"
            assert not s.get("protected_outcomes_loaded")
            rows=[]
            for row in s["prices"]["rows"]:
                assert row["date"]==day and row["unit"]=="USD per GPU-hour"
                assert row["id"]=="grp-v6-"+digest(row["contract"])[:20]
                assert row["family"] in ("A100","H100")
                assert utc(row["fetched_at"]).date().isoformat()==day
                assert utc(row["fetched_at"])<=stamp
                assert math.isfinite(row["value"]) and row["value"]>0
                rows.append(row)
            assert rows
            accepted.append({"eligible":True,"captured_at":s["captured_at"],"source_snapshot_sha256":digest(s),"prices":s["prices"],"bls":s.get("bls")})
        except (AssertionError,KeyError,ValueError,TypeError):
            excluded.append({"captured_at":s.get("captured_at"),"source_snapshot_sha256":fingerprint(s),"reason":"incompatible_capture_window_identity_unit_or_freshness"})
    return accepted,excluded
def origin_number(origin,p):
    first=date.fromisoformat(p["first_eligible_origin"]);day=date.fromisoformat(origin)
    if day.weekday()!=6 or day<first or (day-first).days%7:return None
    index=(day-first).days//7
    return index if index<p["limits"]["max_weekly_origins"] else None
def prepare(records,bls_records,at,p):
    snapshots,excluded=source_snapshots(records,at)
    latest=max((s["prices"]["date"] for s in snapshots),default=None)
    day=utc(at).date();origin=(day-timedelta(days=(day.weekday()+1)%7)).isoformat()
    tasks,failures=tasks_at(snapshots,origin,p)
    feature=feature_at(bls_records,origin)
    latest_origin=max((s for s in snapshots if s["prices"]["date"]<=origin),key=lambda s:s["captured_at"],default=None)
    current_period=((latest_origin or {}).get("bls") or {}).get("latest_period")
    evidence_ready=bool(feature and utc(feature["first_observed_at"])<=utc(origin+"T23:59:59+00:00") and feature["reference_period"]==current_period)
    reasons=[]
    number=origin_number(origin,p)
    if number is None:reasons.append("outside_registered_twelve_week_window")
    timing=issuance_status(origin,at,p)
    if timing!="eligible":reasons.append(timing)
    if not tasks:reasons.append("no_contract_has_required_origin_and_twenty_retained_days")
    if not evidence_ready:reasons.append("current_original_BLS_release_vintage_not_qualified")
    for t in tasks:
        t["bls"]=feature;t["metadata"]["benchmark_contract"]=t["metadata"]["contract"]
    return {"study_id":p["study_id"],"checked_at":at,"origin":origin,"origin_number":number,"eligible":not reasons,"reasons":reasons,"latest_verified_quote_date":latest,"retained_snapshot_count":len(snapshots),"distinct_quote_days":len({s["prices"]["date"] for s in snapshots}),"excluded_snapshots":excluded,"tasks":tasks,"failures":failures,"snapshots":snapshots,"current_api_BLS_period":current_period,"qualified_original_BLS_period":feature["reference_period"] if feature else None,"first_eligible_origin":p["first_eligible_origin"]}
def validate(value,p,lock):
    validate_commitment(value,p,lock)
    assert origin_number(value["origin"],p) is not None
    keys=[(r["method"],r["series_id"],r["horizon_days"]) for r in value["rows"]]
    assert len(keys)==len(set(keys)),"Duplicate method/target/horizon"
    primary={(r["series_id"],r["horizon_days"]) for r in value["rows"] if r["method"]=="price_only"}
    assert {r["method"] for r in value["rows"]}=={"price_only","price_evidence","base_price_only","base_price_evidence","last_value","last_value_empirical","drift","seasonal_naive"}
    assert value["information_cutoff"]==value["origin"]+"T23:59:59+00:00"
    for name in ("price_only","price_evidence","base_price_only","base_price_evidence","last_value","last_value_empirical","drift","seasonal_naive"):
        rows=[r for r in value["rows"] if r["method"]==name]
        assert {(r["series_id"],r["horizon_days"]) for r in rows}==primary,"Unmatched arm or reference cells"
        for row in rows:
            assert all(math.isfinite(row[k]) for k in ("q10","q50","q90"))
            assert row["contract_sha256"] and row["task_id"]
    assert len({sid for sid,h in primary})<=p["limits"]["max_targets"]
    return value
def score(value,snapshots,at,p,lock):
    validate(value,p,lock);accepted,_=source_snapshots(snapshots,at)
    return evaluate(value,accepted,at,p,lock)
