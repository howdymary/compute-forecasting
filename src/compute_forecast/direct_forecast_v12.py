"""Pure contracts for a direct return-distribution forecaster."""
from __future__ import annotations
import hashlib,json,math,statistics
from datetime import date,timedelta
KEYS=("r1","r3","r7")
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False,separators=(",",":")).encode()).hexdigest()
def messages(task,arm="price_only"):
    if arm not in ("price_only","price_evidence"):raise ValueError("Unknown input arm")
    if arm=="price_evidence" and not task.get("evidence"):raise ValueError("No eligible evidence")
    origin=task["origin"]
    if any(r["date"]>origin for r in task["context"]):raise ValueError("Future observation")
    anchor=task["anchor"]
    context=[{"date":r["date"],"log_price_relative_to_origin":round(math.log(r["value"]/anchor),8)} for r in task["context"]]
    meta={k:task["metadata"].get(k) for k in ("series_id","source_id","gpu_model","instrument_class","pricing_tier","statistic")}
    payload={"origin":origin,"metadata":meta,"unit":"USD per GPU-hour","anchor_price":anchor,"history":context,"missing_calendar_days":task["context_missing_days"],"horizons_days":[1,3,7]}
    if arm=="price_evidence":
        if any(e["available_at"]>origin+"T23:59:59+00:00" for e in task["evidence"]):raise ValueError("Future evidence")
        payload["evidence"]=task["evidence"]
    return [{"role":"system","content":"Forecast this exact advertised GPU rental-price series. Return only a JSON object with numeric r1, r3, r7: log(future price / anchor_price) at 1, 3, 7 calendar days. Draw one plausible future outcome vector, not three quantiles. Use only the supplied history and evidence. Missing dates are missing observations. Do not use tools or provide explanations."},{"role":"user","content":json.dumps(payload,sort_keys=True,separators=(",",":"))}]
def conversation(task,arm="price_only"):
    if task["target_dates"]!=[(date.fromisoformat(task["origin"])+timedelta(days=h)).isoformat() for h in (1,3,7)]:raise ValueError("Target day mismatch")
    if any(y<=0 or not math.isfinite(y) for y in task["outcomes"]):raise ValueError("Invalid outcome")
    target=dict(zip(KEYS,[round(math.log(y/task["anchor"]),8) for y in task["outcomes"]]))
    return messages(task,arm)+[{"role":"assistant","content":json.dumps(target,separators=(",",":"),allow_nan=False)}]
def parse(text,lower=-20,upper=20):
    obj=json.loads(text)
    if not isinstance(obj,dict) or set(obj)!=set(KEYS):raise ValueError("Exact numeric schema required")
    values=[]
    for k in KEYS:
        v=obj[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lower<=v<=upper:raise ValueError("Invalid log return")
        values.append(float(v))
    return values
def quantile(values,q):
    ordered=sorted(values);pos=(len(ordered)-1)*q;i=int(pos);j=min(i+1,len(ordered)-1)
    return ordered[i]+(ordered[j]-ordered[i])*(pos-i)
def price_quantiles(vectors,anchor):
    if not vectors:raise ValueError("No sampled vectors")
    return [[quantile([anchor*math.exp(v[i]) for v in vectors],q) for q in (.1,.5,.9)] for i in range(3)]
def cell_loss(y,qs):
    if len(qs)!=3 or not 0<qs[0]<=qs[1]<=qs[2] or not all(math.isfinite(x) for x in qs):raise ValueError("Invalid quantiles")
    return sum(max(q*(y-v),(q-1)*(y-v)) for q,v in zip((.1,.5,.9),qs))/3
def summarize(cells):
    if not cells:return {"n_cells":0,"pinball":None,"primary_pinball":None,"coverage":None,"width":None}
    primary=[r for r in cells if r["horizon_days"]==7]
    origins=sorted({r["origin"] for r in cells})
    return {"n_cells":len(cells),"n_tasks":len({r["task_id"] for r in cells}),"n_series":len({r["series_id"] for r in cells}),"n_origins":len(origins),"origins":origins,"pinball":statistics.mean(r["loss"] for r in cells),"primary_pinball":statistics.mean(r["loss"] for r in primary) if primary else None,"coverage":statistics.mean(r["q10"]<=r["outcome"]<=r["q90"] for r in cells),"width":statistics.mean(r["q90"]-r["q10"] for r in cells),"fallback_cells":sum(r.get("fallback",False) for r in cells),"by_horizon":{str(h):{"n_cells":len(v),"pinball":statistics.mean(r["loss"] for r in v),"coverage":statistics.mean(r["q10"]<=r["outcome"]<=r["q90"] for r in v),"width":statistics.mean(r["q90"]-r["q10"] for r in v)} for h in (1,3,7) if (v:=[r for r in cells if r["horizon_days"]==h])}}
def matched(candidate,reference):
    key=lambda r:(r["series_id"],r["origin"],r["horizon_days"])
    a={key(r):r for r in candidate};b={key(r):r for r in reference}
    if len(a)!=len(candidate) or len(b)!=len(reference) or set(a)!=set(b):raise ValueError("Cohort mismatch")
    deltas=[{"series_id":k[0],"origin":k[1],"horizon_days":k[2],"difference":a[k]["loss"]-b[k]["loss"]} for k in sorted(a)]
    ref=statistics.mean(r["loss"] for r in reference)
    return {"n_cells":len(deltas),"mean_difference":statistics.mean(r["difference"] for r in deltas),"skill":1-statistics.mean(r["loss"] for r in candidate)/ref if ref>0 else None,"by_origin":{o:statistics.mean(r["difference"] for r in deltas if r["origin"]==o) for o in sorted({r["origin"] for r in deltas})},"cells":deltas,"uncertainty_note":"Origin-level differences; dependent origins and correlated series do not establish population significance"}
