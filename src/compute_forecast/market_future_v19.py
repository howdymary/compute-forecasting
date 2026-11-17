"""Independent v19 temporal contracts; no network or training."""
from datetime import date,datetime,timedelta,timezone
import math
from .market_state_v19 import utc,check_asof,market_features
from .probability_v18 import digest,quantiles
def weekly_index(origin,p):
    n=(date.fromisoformat(origin)-date.fromisoformat(p["first_eligible_origin"])).days
    return n//7 if n>=0 and n%7==0 and n//7<p["limits"]["max_weekly_origins"] else None
def snapshots(records,at,p):
    available=[]
    for r in records:
        if not r.get("status")=="captured" or not r.get("eligible_for_origin"):continue
        if utc(r["retrieved_at"])>utc(at):continue
        collected=utc(r["retrieved_at"])
        if r["observed_day"]!=collected.date().isoformat():continue
        if not p["capture_window_utc_hours"][0]<=collected.hour<p["capture_window_utc_hours"][1]:continue
        if any(x["date"]!=r["observed_day"] or utc(x["available_at"])>collected for x in r.get("observations",[])):continue
        available.append(r)
    first={}
    for r in sorted(available,key=lambda r:r["retrieved_at"]):
        first.setdefault(r["observed_day"],r)
    return first
def prepare(records,origin,at,p,cohort=None):
    source=snapshots(records,origin+"T23:59:59.999999+00:00",p);allrows={d:r["observations"] for d,r in source.items()}
    tasks=[];exclusions=[];candidates={}
    for r in allrows.get(origin,[]):
        sid=r["series_id"];context=[]
        for day,rows in sorted(allrows.items()):
            if not (date.fromisoformat(origin)-timedelta(days=41)).isoformat()<=day<=origin:continue
            values=[x for x in rows if x["series_id"]==sid]
            if len(values)==1:context.append(values[0])
        if len(context)<p["min_price_days"]:exclusions.append({"series_id":sid,"reason":"insufficient_retained_price_days"});continue
        if any(x["contract"]!=r["contract"] or x["metadata"]!=r["metadata"] for x in context):
            exclusions.append({"series_id":sid,"reason":"contract_or_metadata_revision"});continue
        check_asof(context,origin)
        task={"task_id":sid+"|"+origin,"series_id":sid,"origin":origin,"anchor":r["value"],"metadata":{**r["metadata"],"series_id":sid},"context":[{k:v[k] for k in ("date","value","available_at")} for v in context],"context_missing_days":42-len(context),"target_dates":[(date.fromisoformat(origin)+timedelta(days=h)).isoformat() for h in p["horizons"]],"contract":r["contract"]}
        past={h:allrows.get((date.fromisoformat(origin)-timedelta(days=h)).isoformat(),[]) for h in p["horizons"]}
        task["market_state"]=market_features(task,allrows.get(origin,[]),origin,past_by_horizon=past)
        task["market_input_identity"]=digest({"source_vintages":{d:x["vintage_sha256"] for d,x in source.items() if (date.fromisoformat(origin)-timedelta(days=41)).isoformat()<=d<=origin}})
        if (task["market_state"].get("peer_return_provider_count_7d") or 0)<2:exclusions.append({"series_id":sid,"reason":"insufficient_other_provider_return_context"});continue
        candidates[sid]=task
    if cohort is None:
        buckets={}
        for sid,t in sorted(candidates.items()):buckets.setdefault((t["metadata"]["provider"],t["metadata"]["family"]),[]).append(sid)
        chosen=[]
        while len(chosen)<p["max_contracts"] and any(buckets.values()):
            for key in sorted(buckets):
                if buckets[key] and len(chosen)<p["max_contracts"]:chosen.append(buckets[key].pop(0))
    else:chosen=list(cohort)
    reasons=[]
    if len(chosen)<p["min_contracts"]:reasons.append("insufficient_contracts")
    selected=[candidates[s] for s in chosen if s in candidates]
    if len(selected)!=len(chosen):reasons.append("frozen_cohort_incomplete")
    if len({t["metadata"]["provider"] for t in selected})<p["min_providers"]:reasons.append("insufficient_providers")
    for family in ("A100","H100"):
        if sum(t["metadata"]["family"]==family for t in selected)<p["min_each_gpu_family"]:reasons.append("insufficient_"+family)
    if weekly_index(origin,p) is None:reasons.append("outside_registered_panel")
    deadline=utc(origin+"T23:59:59.999999+00:00")+timedelta(minutes=p["issuance_deadline_minutes_after_origin"])
    if not utc(origin+"T23:59:59.999999+00:00")<utc(at)<=deadline:reasons.append("outside_issuance_window")
    return {"origin":origin,"eligible":not reasons,"reasons":reasons,"tasks":selected,"cohort":chosen,"exclusions":exclusions,"input_vintages":[{"date":d,"retrieved_at":x["retrieved_at"],"vintage_sha256":x["vintage_sha256"]} for d,x in sorted(source.items()) if (date.fromisoformat(origin)-timedelta(days=41)).isoformat()<=d<=origin],"latest_observation":max(source,default=None)}
def validate(commitment,p,lock):
    assert commitment["study_id"]==p["study_id"] and commitment["protocol_sha256"]==digest(p) and commitment["model_lock_sha256"]==digest(lock)
    origin=commitment["origin"];assert weekly_index(origin,p) is not None
    assert prepare(commitment["capture_receipts"],origin,commitment["issued_at"],p,commitment["cohort"])["eligible"]
    tasks={t["series_id"]:t for t in commitment["price_inputs"]}
    expected={(sid,h) for sid in commitment["cohort"] for h in p["horizons"]};seen=set()
    for row in commitment["rows"]:
        key=(row["method"],row["series_id"],row["horizon_days"]);assert key not in seen;seen.add(key)
        assert "outcome" not in row and "loss" not in row
        assert row["method"] in p["methods"] and 0<row["q10"]<=row["q50"]<=row["q90"]
        assert all(math.isfinite(row[k]) for k in ("q10","q50","q90"))
        assert row["target_date"]==(date.fromisoformat(origin)+timedelta(days=row["horizon_days"])).isoformat()
        assert row["contract_sha256"]==digest(tasks[row["series_id"]]["contract"])
        if row.get("probabilities") is not None:
            assert quantiles(row["probabilities"],row["support_prices"])==[row[k] for k in ("q10","q50","q90")]
    for method in p["methods"]:assert {(r["series_id"],r["horizon_days"]) for r in commitment["rows"] if r["method"]==method}==expected
    return commitment
def score(commitment,records,at,p,lock,publication_receipt=None):
    validate(commitment,p,lock)
    if utc(at)<utc(p["final_analysis_not_before"]):return {"status":"pending_fixed_analysis_date","not_before":p["final_analysis_not_before"],"outcomes_loaded":False,"cells":[]}
    if not publication_receipt or publication_receipt.get("commitment_sha256")!=digest(commitment):return {"status":"pending_verified_publication_receipt","cells":[],"outcomes_loaded":False}
    deadline=utc(commitment["origin"]+"T23:59:59.999999+00:00")+timedelta(minutes=p["issuance_deadline_minutes_after_origin"])
    if utc(publication_receipt["created_at"])>deadline:return {"status":"ineligible_late_publication","cells":[],"outcomes_loaded":False}
    from .direct_forecast_v12 import cell_loss
    truth=snapshots(records,at,p);cells=[];missing=[]
    for r in commitment["rows"]:
        if utc(at)<=utc(r["target_date"]+"T23:59:59+00:00"):missing.append(r);continue
        hits=[x for x in truth.get(r["target_date"],{}).get("observations",[]) if x["series_id"]==r["series_id"] and digest(x["contract"])==r["contract_sha256"]]
        if len(hits)!=1:missing.append({"method":r["method"],"series_id":r["series_id"],"target_date":r["target_date"]});continue
        y=hits[0]["value"];cells.append({**r,"origin":commitment["origin"],"outcome":y,"loss":cell_loss(y,[r[k] for k in ("q10","q50","q90")]),"truth_vintage_sha256":truth[r["target_date"]]["vintage_sha256"]})
    return {"status":"resolved" if not missing else "partially_pending","cells":cells,"missing":missing,"outcomes_loaded":True}
