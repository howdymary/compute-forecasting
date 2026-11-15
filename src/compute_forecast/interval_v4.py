"""Registered horizon-specific signed-residual intervals; no coverage guarantee."""
from datetime import date,timedelta
import math
def quantile(xs,q):
    xs=sorted(float(x) for x in xs)
    if not xs or any(not math.isfinite(x) for x in xs):raise ValueError("Invalid residuals")
    p=(len(xs)-1)*q;a=int(p);b=min(a+1,len(xs)-1)
    return xs[a]+(p-a)*(xs[b]-xs[a])
def empirical_interval(values,at,lead,window=180,minimum=30,half_life=28,minimum_effective=20):
    at=date.fromisoformat(at) if isinstance(at,str) else at
    values={date.fromisoformat(k) if isinstance(k,str) else k:float(v) for k,v in values.items()}
    if lead<1 or at not in values:return {"status":"pending_missing_anchor","quantiles":None}
    if any(d>at for d in values):raise ValueError("Calibration received later observations")
    pairs=[]
    for start,y in sorted(values.items()):
        end=start+timedelta(days=lead)
        if at-timedelta(days=window)<=end<=at and end in values:
            if not all(math.isfinite(v) and v>0 for v in (y,values[end])):raise ValueError("Invalid rate")
            pairs.append((end,values[end]-y))
    if len(pairs)<minimum:return {"status":"pending_insufficient_residuals","residual_count":len(pairs),"minimum":minimum,"quantiles":None}
    weights=[2**(-(at-end).days/half_life) for end,_ in pairs]
    effective=sum(weights)**2/sum(w*w for w in weights)
    if effective<minimum_effective:return {"status":"pending_insufficient_effective_residuals","residual_count":len(pairs),"effective_residuals":effective,"quantiles":None}
    ordered=sorted(zip([r for _,r in pairs],weights));total=sum(weights)
    def weighted(q):
        cumulative=0.
        for residual,w in ordered:
            cumulative+=w
            if cumulative>=q*total:return residual
        return ordered[-1][0]
    qs=[values[at]+weighted(q) for q in (.1,.5,.9)]
    if qs!=sorted(qs) or any(not math.isfinite(v) or v<=0 for v in qs):return {"status":"failed_invalid_native_quantiles","quantiles":None,"residual_count":len(pairs)}
    return {"status":"completed","quantiles":qs,"residual_count":len(pairs),"last_label_date":max(d for d,_ in pairs).isoformat(),"effective_lead_days":lead,"method":"persistence plus recency-weighted empirical signed-residual quantiles","half_life_days":half_life,"effective_residuals":effective,"coverage_guarantee":False}
