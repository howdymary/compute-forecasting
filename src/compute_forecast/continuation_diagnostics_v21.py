"""Read-only diagnostics on retained categorical forecasts; never produces new forecasts."""
import math,statistics
from .probability_v18 import bin_index
def mean(values):return statistics.mean(values) if values else None
def vector_metrics(p,reference,levels,z,y):
    if len(p)!=len(reference) or len(p)!=len(levels) or len(z)!=len(p):raise ValueError("Support mismatch")
    for v in (p,reference):
        if any(not math.isfinite(x) or x<0 for x in v) or abs(sum(v)-1)>1e-5:raise ValueError("Invalid mass")
    zero=levels.index(0);target=bin_index(z,y);mass=p[target]
    singular=any(a>0 and b==0 for a,b in zip(reference,p))
    kl=None if singular else sum(a*math.log(a/b) for a,b in zip(reference,p) if a>0)
    return {"entropy_nats":-sum(a*math.log(a) for a in p if a>0),"unchanged_probability":p[zero],"nearest_level_nll":-math.log(mass) if mass>0 else None,"zero_target_mass":mass==0,"forward_kl_from_incumbent":kl,"singular_forward_kl":singular,"total_variation_from_incumbent":sum(abs(a-b) for a,b in zip(p,reference))/2,"out_of_support":y<z[0] or y>z[-1]}
def evaluate(candidate,reference,levels,horizon=7):
    key=lambda r:(r["task_id"],r["horizon_days"])
    a={key(r):r for r in candidate if r["horizon_days"]==horizon};b={key(r):r for r in reference if r["horizon_days"]==horizon}
    if a.keys()!=b.keys():raise ValueError("Unmatched diagnostic cohort")
    values=[]
    for k,r in sorted(a.items()):
        ref=b[k]
        if any(r[x]!=ref[x] for x in ("anchor","outcome","target_date","support_prices")):raise ValueError("Truth or support mismatch")
        value=vector_metrics(r["probabilities"],ref["probabilities"],levels,r["support_prices"],r["outcome"])
        values.append({"task_id":r["task_id"],"origin":r["origin"],"series_id":r["series_id"],"changed_price":r["changed_price"],**value})
    def summary(rows):
        return {"n":len(rows),"entropy_nats":mean([r["entropy_nats"] for r in rows]),"unchanged_probability":mean([r["unchanged_probability"] for r in rows]),"finite_nearest_level_nll":mean([r["nearest_level_nll"] for r in rows if r["nearest_level_nll"] is not None]),"zero_target_mass":sum(r["zero_target_mass"] for r in rows),"finite_forward_kl_from_incumbent":mean([r["forward_kl_from_incumbent"] for r in rows if r["forward_kl_from_incumbent"] is not None]),"singular_forward_kl":sum(r["singular_forward_kl"] for r in rows),"total_variation_from_incumbent":mean([r["total_variation_from_incumbent"] for r in rows]),"out_of_support":sum(r["out_of_support"] for r in rows)}
    return {"horizon_days":horizon,"all":summary(values),"changed":summary([r for r in values if r["changed_price"]]),"unchanged":summary([r for r in values if not r["changed_price"]]),"cells":values,"interpretation":"NLL is nearest registered price-level class loss, not a continuous market likelihood. Finite-only summaries retain explicit singular/zero counts. Entropy and probability drift diagnose behavior, not a causal reason for forecasting loss."}
