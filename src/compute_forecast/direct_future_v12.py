"""Locked, source-specific prospective contracts; fixtures are explicitly synthetic."""
from __future__ import annotations
import math
from datetime import datetime,date,timedelta,timezone
from .direct_forecast_v12 import digest,cell_loss,summarize
def utc(value):
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None:raise ValueError("Timezone required")
    return dt.astimezone(timezone.utc)
def cutoff(origin):return utc(origin+"T23:59:59+00:00")
def asof(snapshots,at):
    bound=utc(at);first={}
    for snapshot in sorted(snapshots,key=lambda s:s["captured_at"]):
        if not snapshot.get("eligible") or utc(snapshot["captured_at"])>bound:continue
        day=snapshot["prices"]["date"];first.setdefault(day,snapshot)
    return [first[d] for d in sorted(first)]
def tasks_at(snapshots,origin,p):
    retained=asof(snapshots,origin+"T23:59:59+00:00");start=(date.fromisoformat(origin)-timedelta(days=p["history_calendar_days"]-1)).isoformat()
    values={};metadata={}
    for s in retained:
        if s["prices"]["date"]<start:continue
        for r in s["prices"]["rows"]:
            sid=r["id"];values.setdefault(sid,{})[r["date"]]=r["value"];metadata[sid]=r
    tasks=[];failures=[]
    for sid,history in sorted(values.items()):
        if origin not in history or len(history)<p["min_price_days"]:
            failures.append({"series_id":sid,"reason":"missing_origin_quote" if origin not in history else "insufficient_retained_days","observed":len(history),"required":p["min_price_days"]});continue
        r=metadata[sid];contract=r["contract"]
        task={"task_id":digest([p["study_id"],sid,origin])[:24],"series_id":sid,"origin":origin,"anchor":history[origin],"metadata":{"series_id":sid,"source_id":"gpurentalprices_current_contract","gpu_model":contract.get("gpu"),"instrument_class":"individual_provider_contract","pricing_tier":"on_demand","statistic":"first_verified_snapshot_in_registered_UTC_window","contract":contract},"context":[{"date":d,"value":v} for d,v in sorted(history.items())],"context_missing_days":p["history_calendar_days"]-len(history),"evidence":[],"target_dates":[(date.fromisoformat(origin)+timedelta(days=h)).isoformat() for h in p["horizons"]]}
        tasks.append(task)
    return tasks,failures
def issuance_status(origin,issued_at,p):
    at=utc(issued_at);origin_end=cutoff(origin)
    if date.fromisoformat(origin).weekday()!=6:return "unregistered_origin"
    if at<origin_end:return "before_origin_cutoff"
    if at>origin_end+timedelta(minutes=p["issuance_deadline_minutes_after_origin"]):return "missed_issuance_deadline"
    return "eligible"
def score(commitment,snapshots,at,p):
    if commitment.get("status")!="issued":return {"status":"not_issued","cells":[],"summary":None}
    issued=utc(commitment["issued_at"]);bound=utc(at);truth={}
    for s in asof(snapshots,at):
        for r in s["prices"]["rows"]:truth[(r["id"],r["date"])]=(r,s)
    cells=[];pending=[]
    for row in commitment["rows"]:
        key=(row["series_id"],row["target_date"])
        observed=truth.get(key)
        target_day_end=cutoff(row["target_date"])
        if bound<=target_day_end or observed is None:
            pending.append({"series_id":row["series_id"],"target_date":row["target_date"],"horizon_days":row["horizon_days"],"reason":"outcome_not_mature_or_missing"});continue
        r,s=observed
        if utc(s["captured_at"])<=issued:raise ValueError("Outcome existed before issuance")
        if row["contract_sha256"]!=digest(r["contract"]):raise ValueError("Incompatible outcome contract")
        qs=[row[k] for k in ("q10","q50","q90")];y=r["value"]
        cells.append({**row,"outcome":y,"loss":cell_loss(y,qs),"truth_snapshot_sha256":digest(s),"origin":commitment["origin"],"task_id":row["task_id"]})
    groups={}
    for method in sorted({r["method"] for r in cells}):groups[method]=summarize([r for r in cells if r["method"]==method])
    return {"status":"completed" if not pending else "pending","scored_at":at,"cells":cells,"by_method":groups,"pending":pending,"compatible_observed_truth_only":True}
