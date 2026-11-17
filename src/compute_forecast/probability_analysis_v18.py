"""Descriptive diagnostics from retained forecasts, without new selection or inference."""
from __future__ import annotations
import collections,math,statistics
def pinball(y,q,tau):
    error=y-q
    return max(tau*error,(tau-1)*error)
def mean(x):return statistics.mean(x) if x else None
def diagnostics(cells,cases):
    tasks={c["task_id"]:c for c in cases};groups=collections.defaultdict(list)
    for r in cells:
        t=tasks[r["task_id"]];m=t["metadata"];changed=abs(r["outcome"]-t["anchor"])>1e-12
        values={"horizon":str(r["horizon_days"]),"source":m["source_id"],"series":r["series_id"],"origin":r["origin"],"gpu_family":m["gpu_model"].split()[0],"instrument":m["instrument_class"],"price_changed":"changed" if changed else "unchanged"}
        groups[("all","all")].append(r)
        for axis,value in values.items():groups[(axis,value)].append(r)
    out={}
    for (axis,value),rows in sorted(groups.items()):
        n=len(rows);quantile_losses={name:mean([pinball(r["outcome"],r[name],tau) for r in rows]) for name,tau in (("q10",.1),("q50",.5),("q90",.9))}
        total=mean([r["loss"] for r in rows])
        assert abs(mean(list(quantile_losses.values()))-total)<1e-12
        out.setdefault(axis,{})[value]={"n":n,"origins":len({r["origin"] for r in rows}),"pinball":total,"quantile_pinball":quantile_losses,"median_mae":mean([abs(r["outcome"]-r["q50"]) for r in rows]),"coverage":mean([int(r["q10"]<=r["outcome"]<=r["q90"]) for r in rows]),"interval_width":mean([r["q90"]-r["q10"] for r in rows]),"crps":mean([r["crps"] for r in rows if r.get("crps") is not None]),"failures":sum(bool(r.get("fallback")) for r in rows),"out_of_support":sum(not(r["support_prices"][0]<=r["outcome"]<=r["support_prices"][-1]) for r in rows if r.get("support_prices"))}
    return out
def paired(candidate,reference,cases):
    a={(r["series_id"],r["origin"],r["horizon_days"]):r for r in candidate if r["horizon_days"]==7}
    b={(r["series_id"],r["origin"],r["horizon_days"]):r for r in reference if r["horizon_days"]==7}
    assert a.keys()==b.keys() and a
    meta={r["task_id"]:r["metadata"] for r in cases};values=[];overall=mean([r["loss"]-b[k]["loss"] for k,r in a.items()])
    for axis in ("source","series","origin","gpu_family","instrument"):
        groups=collections.defaultdict(list)
        for key,r in a.items():
            m=meta[r["task_id"]];label={"source":m["source_id"],"series":r["series_id"],"origin":r["origin"],"gpu_family":m["gpu_model"].split()[0],"instrument":m["instrument_class"]}[axis]
            groups[label].append(r["loss"]-b[key]["loss"])
        rows=[{"group":name,"n":len(v),"mean_difference":mean(v),"weighted_contribution":len(v)/len(a)*mean(v)} for name,v in sorted(groups.items())]
        assert abs(sum(r["weighted_contribution"] for r in rows)-overall)<1e-12
        values.append({"axis":axis,"groups":rows})
    origins=sorted({r["origin"] for r in a.values()})
    leave_one=[]
    for omitted in origins:
        ds=[r["loss"]-b[k]["loss"] for k,r in a.items() if r["origin"]!=omitted]
        leave_one.append({"omitted_origin":omitted,"n":len(ds),"difference":mean(ds)})
    base=mean([r["loss"] for r in b.values()])
    return {"n":len(a),"difference":overall,"skill_vs_reference":1-mean([r["loss"] for r in a.values()])/base if base else None,"contributions":values,"leave_one_origin_out":leave_one,"uncertainty_note":"Descriptive sensitivity only: three reused, dependent dates; seed and cell replication do not increase independent temporal sample size"}
