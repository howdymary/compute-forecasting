"""Unchanged v19 categorical forecasting interface with bounded inference and explicit failures."""
import asyncio,hashlib,json,pathlib
from datetime import datetime,timezone
from .probability_v18 import digest,support,quantiles,crps,summarize
from .market_state_v19 import decision
from .direct_forecast_v12 import cell_loss
async def evaluate(tasks,sampler,renderer,levels,p,label):
    from tinker_cookbook.recipes.decisions import sample_decision
    sem=asyncio.Semaphore(p["limits"]["max_inference_concurrency"])
    async def one(task,h):
        t={**task,"arm":"price"};z=support(t["anchor"],levels);error=None
        try:
            d=renderer.render(decision(t,h,levels))
            if len(d.tokens)>p["model"]["max_context_tokens"]:raise ValueError("Context limit")
            async with sem:probs=await asyncio.wait_for(sample_decision(sampler,d),timeout=p["limits"]["inference_timeout_seconds"])
            mass=[float(probs[str(i)]) for i in range(len(z))];q=quantiles(mass,z)
        except Exception as exc:error=type(exc).__name__;mass=[float(v==0) for v in levels];q=[t["anchor"]]*3
        y=t["outcomes"][(1,3,7).index(h)]
        return {"task_id":t["task_id"],"series_id":t["series_id"],"source_id":t["metadata"]["source_id"],"gpu_model":t["metadata"]["gpu_model"],"instrument_class":t["metadata"]["instrument_class"],"origin":t["origin"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"outcome":y,"anchor":t["anchor"],"q10":q[0],"q50":q[1],"q90":q[2],"loss":cell_loss(y,q),"crps":crps(mass,z,y),"probabilities":mass,"probability_sha256":digest(mass),"support_prices":z,"fallback":error is not None,"failure_type":error,"changed_price":y!=t["anchor"],"out_of_support":y<z[0] or y>z[-1],"prompt_sha256":digest(decision(t,h,levels).text),"method":label}
    rows=await asyncio.gather(*(one(t,h) for t in tasks for h in p["data"]["horizons"]))
    return {"label":label,"created_at":datetime.now(timezone.utc).isoformat(),"cells":rows,"summary":summarize(rows)}
def compatibility(fresh,retained):
    a={(r["task_id"],r["horizon_days"]):r for r in fresh["cells"]};b={(r["task_id"],r["horizon_days"]):r for r in retained["cells"]}
    assert a.keys()==b.keys()
    q_mismatches=[];max_probability_difference=0.
    for key,x in a.items():
        y=b[key]
        assert all(x[k]==y[k] for k in ("outcome","anchor","target_date","prompt_sha256","support_prices"))
        if any(x[k]!=y[k] for k in ("q10","q50","q90")):q_mismatches.append(list(key))
        max_probability_difference=max(max_probability_difference,max(abs(v-w) for v,w in zip(x["probabilities"],y["probabilities"],strict=True)))
    return {"quantiles_match":not q_mismatches,"quantile_mismatches":q_mismatches,"max_probability_difference":max_probability_difference,"fresh_loss":fresh["summary"]["primary_pinball"],"retained_loss":retained["summary"]["primary_pinball"],"failures":fresh["summary"]["failures"]}
