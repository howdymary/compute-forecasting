"""Direct categorical future-price distribution: pure arithmetic and Tinker adapters."""
from __future__ import annotations
import hashlib,json,math,statistics
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,allow_nan=False,separators=(",",":")).encode()).hexdigest()
def levels(train,p):
    extent=max(p["distribution"]["minimum_extent"],p["distribution"]["training_max_abs_multiplier"]*max(abs(x) for t in train for x in t["returns"]))
    small=p["distribution"]["minimum_abs_log_return"]
    positive=[math.exp(math.log(small)+i*(math.log(extent)-math.log(small))/9) for i in range(10)]
    return sorted([-x for x in positive]+[0.]+positive)
def support(anchor,log_levels):
    if not math.isfinite(anchor) or anchor<=0:raise ValueError("Positive finite anchor required")
    z=[anchor*math.exp(r) for r in log_levels]
    if not all(math.isfinite(x) and x>0 for x in z) or any(a>=b for a,b in zip(z,z[1:])):raise ValueError("Invalid ordered price support")
    return z
def probabilities(logprobs):
    if not logprobs or not all(math.isfinite(x) for x in logprobs):raise ValueError("Invalid model logprobs")
    maximum=max(logprobs);weights=[math.exp(x-maximum) for x in logprobs];total=sum(weights)
    return [w/total for w in weights]
def validate_probs(p):
    if not p or any(not math.isfinite(x) or x<0 for x in p) or abs(sum(p)-1)>1e-5:raise ValueError("Invalid probability distribution")
def quantiles(p,z):
    validate_probs(p);out=[]
    for tau in (.1,.5,.9):
        cumulative=0.;value=z[-1]
        for mass,level in zip(p,z):
            cumulative+=mass
            if cumulative>=tau:value=level;break
        out.append(value)
    return out
def crps(p,z,y):
    validate_probs(p)
    return sum(mass*abs(level-y) for mass,level in zip(p,z))-.5*sum(p[i]*p[j]*abs(z[i]-z[j]) for i in range(len(z)) for j in range(len(z)))
def bin_index(z,y):return min(range(len(z)),key=lambda i:(abs(z[i]-y),i))
def prompt(task,h):
    if h not in (1,3,7):raise ValueError("Unsupported horizon")
    if any(r["date"]>task["origin"] for r in task["context"]):raise ValueError("Future observation refused")
    return json.dumps({"task":"Forecast the future advertised GPU rental price distribution","origin":task["origin"],"horizon_days":h,"unit":"USD per GPU-hour","metadata":{k:task["metadata"].get(k) for k in ("series_id","source_id","gpu_model","instrument_class","pricing_tier","benchmark_contract")},"anchor_price":task["anchor"],"history":[{"date":r["date"],"log_price_relative_to_origin":round(math.log(r["value"]/task["anchor"]),8)} for r in task["context"]],"missing_calendar_days":task["context_missing_days"]},sort_keys=True,separators=(",",":"))
def decision(task,h,log_levels):
    from tinker_cookbook.recipes.decisions import Decision
    z=support(task["anchor"],log_levels)
    choices=[(str(i),"Future price "+format(value,".10g")+" USD per GPU-hour; log change "+format(log_levels[i],".8g")+("; unchanged price" if log_levels[i]==0 else "")) for i,value in enumerate(z)]
    return Decision(prompt(task,h),choices)
def datum(task,h,log_levels,renderer):
    import tinker,torch
    from tinker_cookbook.recipes.decisions import decision_dist_datums
    z=support(task["anchor"],log_levels);y=task["outcomes"][(1,3,7).index(h)];d=decision(task,h,log_levels)
    result=decision_dist_datums(renderer,[(d,{str(bin_index(z,y)):1.})])[0]
    result.loss_fn_inputs["price_levels"]=tinker.TensorData.from_torch(torch.tensor(z,dtype=torch.float32))
    result.loss_fn_inputs["outcome_price"]=tinker.TensorData.from_torch(torch.tensor([y],dtype=torch.float32))
    return result
def custom_loss(objective,scale):
    import torch
    if objective not in ("ce","crps") or scale<=0:raise ValueError("Unknown objective or invalid scale")
    def loss(data,logprobs):
        values=[];raw=[]
        for datum,lp in zip(data,logprobs,strict=True):
            scores=lp[-1].float();p=torch.softmax(scores,dim=-1)
            z=datum.loss_fn_inputs["price_levels"].to_torch().float();y=datum.loss_fn_inputs["outcome_price"].to_torch().float()[0]
            if objective=="ce":
                target=datum.loss_fn_inputs["weights"].to_torch()[-1].float()
                v=-(target*torch.log_softmax(scores,dim=-1)).sum();values.append(v);raw.append(v.detach())
            else:
                v=(p*(z-y).abs()).sum()-.5*(p[:,None]*p[None,:]*(z[:,None]-z[None,:]).abs()).sum()
                values.append(v/scale);raw.append(v.detach())
        total=torch.stack(values).mean()
        return total,{"objective":float(total.detach()),"raw_loss":float(torch.stack(raw).mean())}
    return loss
def summarize(cells):
    def group(rows):
        return {"n":len(rows),"pinball":statistics.mean(r["loss"] for r in rows),"coverage":statistics.mean(r["q10"]<=r["outcome"]<=r["q90"] for r in rows),"width":statistics.mean(r["q90"]-r["q10"] for r in rows),"median_mae":statistics.mean(abs(r["q50"]-r["outcome"]) for r in rows),"crps":statistics.mean(r["crps"] for r in rows if r.get("crps") is not None) if any(r.get("crps") is not None for r in rows) else None,"failures":sum(r.get("fallback",False) for r in rows),"out_of_support":sum(r.get("out_of_support",False) for r in rows)}
    if not cells:return {"n":0,"primary_pinball":None}
    result=group(cells);result["by_horizon"]={str(h):group([r for r in cells if r["horizon_days"]==h]) for h in (1,3,7) if any(r["horizon_days"]==h for r in cells)}
    result["primary_pinball"]=result["by_horizon"]["7"]["pinball"];return result
