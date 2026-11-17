"""Direct quantile heads and fixed ensemble contracts. Head weights are not a predictive CDF."""
from __future__ import annotations
import json,math,statistics
from .probability_v18 import digest,validate_probs,quantiles,support,summarize
from .direct_forecast_v12 import cell_loss
TAUS=(.1,.5,.9)
def identity(row):return (row["task_id"],row["horizon_days"])
def checked(cells):
    result={identity(r):r for r in cells}
    if len(result)!=len(cells):raise ValueError("Duplicate forecast cell")
    return result
def ensemble(groups,kind):
    if kind not in ("quantile_average","probability_pool") or len(groups)!=3:raise ValueError("Three fixed equal-weight parents required")
    maps=[checked(g) for g in groups];keys=set(maps[0])
    if any(set(m)!=keys for m in maps):raise ValueError("Unmatched ensemble cohorts")
    output=[]
    for key in sorted(keys):
        rows=[m[key] for m in maps];a=rows[0]
        for r in rows:
            if any(r[k]!=a[k] for k in ("outcome","anchor","target_date","support_prices")):raise ValueError("Incompatible ensemble input")
            validate_probs(r["probabilities"])
            if [r[k] for k in ("q10","q50","q90")]!=quantiles(r["probabilities"],r["support_prices"]):raise ValueError("Parent quantiles do not reconstruct")
        mass=[statistics.mean(r["probabilities"][j] for r in rows) for j in range(len(a["support_prices"]))]
        q=[statistics.mean(r[k] for r in rows) for k in ("q10","q50","q90")] if kind=="quantile_average" else quantiles(mass,a["support_prices"])
        r={k:a[k] for k in ("task_id","series_id","source_id","gpu_model","instrument_class","origin","horizon_days","target_date","outcome","anchor","changed_price","support_prices")}
        r.update(method=kind,q10=q[0],q50=q[1],q90=q[2],loss=cell_loss(a["outcome"],q),crps=None,probabilities=mass if kind=="probability_pool" else None,fallback=any(v["fallback"] for v in rows),parent_prediction_hashes=[digest(v) for v in rows],out_of_support=a["out_of_support"])
        output.append(r)
    return output
def head_quantiles(heads,z):
    if len(heads)!=3 or any(len(p)!=len(z) for p in heads):raise ValueError("Three aligned scalar heads required")
    if any(not math.isfinite(v) or v<=0 for v in z) or any(a>=b for a,b in zip(z,z[1:])):raise ValueError("Invalid support")
    for p in heads:validate_probs(p)
    raw=[sum(a*b for a,b in zip(p,z,strict=True)) for p in heads]
    return sorted(raw),raw,any(a>b for a,b in zip(raw,raw[1:]))
def decision(task,h,tau,levels):
    from tinker_cookbook.recipes.decisions import Decision
    from .market_state_v19 import prompt
    if tau not in TAUS:raise ValueError("Unsupported quantile")
    value=json.loads(prompt({**task,"arm":"price"},h))
    value["task"]="Encode one future rental-price quantile as a weighted mean of candidate numeric levels"
    value["quantile_tau"]=tau
    value["encoding"]="Answer-token softmax weights encode a scalar mean over the numeric levels. These weights are not a predictive probability distribution."
    text=json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)
    z=support(task["anchor"],levels)
    return Decision(text,[(str(i),"Numerical encoding level "+format(v,".10g")+" USD per GPU-hour") for i,v in enumerate(z)])
def datum(task,h,tau,levels,renderer):
    import tinker,torch
    from tinker_cookbook.recipes.decisions import decision_dist_datums
    z=support(task["anchor"],levels);y=task["outcomes"][(1,3,7).index(h)]
    # This dummy one-hot only constructs candidate-token tensors. The custom loss ignores CE weights.
    d=decision_dist_datums(renderer,[(decision(task,h,tau,levels),{"0":1.})])[0]
    d.loss_fn_inputs["price_levels"]=tinker.TensorData.from_torch(torch.tensor(z,dtype=torch.float32))
    d.loss_fn_inputs["outcome_price"]=tinker.TensorData.from_torch(torch.tensor([y],dtype=torch.float32))
    d.loss_fn_inputs["quantile_tau"]=tinker.TensorData.from_torch(torch.tensor([tau],dtype=torch.float32))
    return d
def tensor_loss(logits,z,y,scale):
    import torch
    if logits.shape[-2]!=3 or logits.shape[-1]!=len(z) or scale<=0:raise ValueError("Bad head tensor or scale")
    p=torch.softmax(logits,dim=-1);raw=(p*z).sum(-1);q=torch.sort(raw,dim=-1).values
    tau=torch.tensor(TAUS,dtype=q.dtype,device=q.device)
    residual=y[...,None]-q
    loss=torch.maximum(tau*residual,(tau-1)*residual).mean()/scale
    return loss,q,raw
def custom_loss(scale):
    import torch
    def loss(data,logprobs):
        if not data or len(data)%3 or len(data)!=len(logprobs):raise ValueError("Incomplete quantile triples")
        values=[];cross=[];raw_losses=[]
        for i in range(0,len(data),3):
            trio=data[i:i+3]
            ts=[float(d.loss_fn_inputs["quantile_tau"].to_torch()[0]) for d in trio]
            if any(abs(a-b)>1e-6 for a,b in zip(ts,TAUS)):raise ValueError("Quantile triple order differs")
            zs=[d.loss_fn_inputs["price_levels"].to_torch().float() for d in trio]
            ys=[d.loss_fn_inputs["outcome_price"].to_torch().float()[0] for d in trio]
            if any(not torch.equal(z,zs[0]) for z in zs) or any(not torch.equal(y,ys[0]) for y in ys):raise ValueError("Mismatched quantile group")
            logits=torch.stack([lp[-1].float() for lp in logprobs[i:i+3]])
            v,q,raw=tensor_loss(logits,zs[0],ys[0],scale)
            values.append(v);raw_losses.append(v.detach()*scale);cross.append(float(bool((raw[:-1]>raw[1:]).any())))
        total=torch.stack(values).mean()
        return total,{"scaled_pinball":float(total.detach()),"dollar_pinball":float(torch.stack(raw_losses).mean()),"raw_crossing_fraction":statistics.mean(cross)}
    return loss
def expansion_gate(state,parent_loss):
    chosen=state["selected"];base=state["checkpoints"][0]["development"]["primary_pinball"];v=chosen["development"]["primary_pinball"]
    return {"passed":chosen["update"]>0 and v<=.98*base and v<=.98*parent_loss and chosen["development"]["failures"]==0,"selected_loss":v,"head_zero_loss":base,"parent_loss":parent_loss,"threshold":.98,"statistical_claim":False}
def decompose(candidate,reference):
    a,b=checked(candidate),checked(reference)
    if set(a)!=set(b):raise ValueError("Unmatched comparison")
    rows=[]
    for key in sorted(a):
        x,y=a[key],b[key]
        if any(x[k]!=y[k] for k in ("outcome","anchor","target_date")):raise ValueError("Truth mismatch")
        parts=[]
        for tau,k in zip(TAUS,("q10","q50","q90")):
            def loss(q):
                residual=x["outcome"]-q
                return max(tau*residual,(tau-1)*residual)
            parts.append((loss(x[k])-loss(y[k]))/3)
        delta=x["loss"]-y["loss"]
        if abs(sum(parts)-delta)>1e-12:raise ValueError("Quantile contributions do not reconcile")
        rows.append({"task_id":key[0],"horizon_days":key[1],"series_id":x["series_id"],"origin":x["origin"],"gpu_model":x["gpu_model"],"changed_price":x["changed_price"],"difference":delta,"quantile_contributions":parts})
    primary=[r for r in rows if r["horizon_days"]==7]
    groups={}
    for dimension in ("origin","series_id","gpu_model","changed_price"):
        groups[dimension]=[{"value":v,"n":len(g),"mean_difference":statistics.mean(r["difference"] for r in g),"weighted_contribution":sum(r["difference"] for r in g)/len(primary)} for v in sorted({r[dimension] for r in primary},key=str) for g in [[r for r in primary if r[dimension]==v]]]
    return {"n_primary":len(primary),"difference":statistics.mean(r["difference"] for r in primary),"groups":groups,"cells":rows,"uncertainty":"Three reused dependent origins; no population confidence or prospective claim"}
