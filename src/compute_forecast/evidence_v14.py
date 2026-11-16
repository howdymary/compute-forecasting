"""Point-in-time BLS features and matched direct-forecast prompt contracts."""
import json,math
from datetime import datetime,timezone
from .direct_forecast_v12 import messages as price_messages,conversation as price_conversation,digest
def utc(value):
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None:raise ValueError("Timezone required")
    return dt.astimezone(timezone.utc)
def feature_at(records,origin):
    bound=utc(origin+"T23:59:59+00:00")
    candidates=[r for r in records if utc(r["available_at"])<=bound]
    if not candidates:return None
    latest=max(candidates,key=lambda r:utc(r["available_at"]))
    if latest["status"]!="qualified_pending_spot_check":return None
    if latest["series_id"]!="PCU221122221122":raise ValueError("Wrong economic series")
    vals=latest["values"];assert vals["periods"][-1]==latest["reference_period"]
    y,prior=vals["indices"][-1],vals["indices"][-2]
    if y is None or prior is None or min(y,prior)<=0:raise ValueError("Missing positive monthly pair")
    return {"source_id":latest["series_id"],"source_url":latest["source_url"],"source_content_sha256":latest["content_sha256"],"source_row_sha256":vals["source_row_sha256"],"available_at":latest["available_at"],"first_observed_at":latest["first_observed_at"],"retrieved_at":latest["retrieved_at"],"historical_availability_basis":"Original BLS monthly archived release; current retrieval is not backdated","reference_period":latest["reference_period"],"unit":"Index2003-12=100, not seasonally adjusted","latest_available_index":y,"month_over_month_log_change":math.log(y/prior),"days_since_release":round((bound-utc(latest["available_at"])).total_seconds()/86400,6)}
def messages(task,arm="price_only"):
    if arm not in ("price_only","price_evidence"):raise ValueError("Unregistered arm")
    out=price_messages(task,"price_only");payload=json.loads(out[-1]["content"])
    payload["metadata"]["benchmark_contract"]=task["metadata"].get("benchmark_contract")
    feature=task.get("bls")
    if arm=="price_evidence":
        if feature is None:raise ValueError("Missing qualified evidence")
        if utc(feature["available_at"])>utc(task["origin"]+"T23:59:59+00:00"):raise ValueError("Future economic release")
        payload["supplementary"]={"bls":{k:feature[k] for k in ("source_id","reference_period","unit","latest_available_index","month_over_month_log_change","days_since_release")},"news":None,"infrastructure":None}
    else:payload["supplementary"]={"bls":None,"news":None,"infrastructure":None}
    out[-1]["content"]=json.dumps(payload,sort_keys=True,separators=(",",":"));return out
def conversation(task,arm="price_only"):
    target=price_conversation(task,"price_only")[-1]
    return messages(task,arm)+[target]
def eligibility(groups,records):
    tasks=[t for group in groups.values() for t in group];origins=sorted({t["origin"] for t in tasks})
    observed={o:feature_at(records,o) for o in origins}
    return {"distinct_origins":len(origins),"origins_with_qualified_evidence":sum(v is not None for v in observed.values()),"origin_coverage":sum(v is not None for v in observed.values())/len(origins) if origins else 0,"distinct_releases":len({v["available_at"] for v in observed.values() if v}),"independence_note":"Sliding price windows and repeated monthly features are dependent"}
