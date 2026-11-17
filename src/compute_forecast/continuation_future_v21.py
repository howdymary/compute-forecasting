"""Separate categorical continuation panel; never changes existing study gates."""
import copy
from .probability_v18 import digest,quantiles,support
from .market_state_v19 import prompt
from .market_future_v19 import prepare,validate as source_validate,score as source_score
def effective_protocol(raw,parent,expanded_ready=True):
    p=copy.deepcopy(parent)
    assert raw["first_eligible_origin"]==p["first_eligible_origin"] and raw["final_analysis_not_before"]==p["final_analysis_not_before"]
    assert raw["origins"]==p["limits"]["max_weekly_origins"]==16
    p.update(study_id=raw["study_id"],methods=[m for m in raw["methods"] if expanded_ready or m!="expanded"],registered_continuation_protocol=raw)
    p["limits"]["max_probability_requests_per_origin"]=raw["limits"]["max_probability_requests_per_origin"]
    return p
def validate(value,p,lock):
    source_validate(value,p,lock)
    tasks={t["series_id"]:t for t in value["price_inputs"]}
    identities={r["arm"]:r["checkpoint_id"] for r in lock["records"]}
    for r in value["rows"]:
        t=tasks[r["series_id"]];actual=[r[k] for k in ("q10","q50","q90")]
        if r["fallback"]:assert actual==[t["anchor"]]*3
        if r["method"]=="official_drift":continue
        assert r["probability_sha256"]==digest(r["probabilities"])
        assert r["checkpoint_id"]==identities[r["method"]]
        assert r["support_prices"]==support(t["anchor"],lock["log_levels"])
        assert quantiles(r["probabilities"],r["support_prices"])==actual
        assert r["prompt_sha256"]==digest(prompt({**t,"arm":"price"},r["horizon_days"]))
    return value
def score(value,records,at,p,lock,receipt=None):
    validate(value,p,lock)
    return source_score(value,records,at,p,lock,receipt)
def final_analysis(cells,p,lock,resolutions):
    from .market_analysis_v19 import paired
    selected=lock["primary_arm"]
    contrasts=[(m,"incumbent") for m in p["methods"] if m in ("same","expanded")]
    if "expanded" in p["methods"]:contrasts.append(("expanded","same"))
    contrasts += [(m,"official_drift") for m in p["methods"] if m!="official_drift"]
    values=[paired(cells,a,b) for a,b in contrasts]
    origins={r["origin"] for r in cells if r["horizon_days"]==7}
    complete=len(origins)==16 and len(resolutions)==16 and all(r["status"]=="resolved" for r in resolutions)
    rates={m:sum(r["fallback"] for r in cells if r["method"]==m and r["horizon_days"]==7)/sum(r["method"]==m and r["horizon_days"]==7 for r in cells) if any(r["method"]==m and r["horizon_days"]==7 for r in cells) else None for m in p["methods"]}
    def better(a,b):
        v=next((v for v in values if v.get("contrast")==a+" minus "+b),{})
        return v.get("estimate") is not None and v["estimate"]<0 and all(v.get("block_sensitivity",{}).get(str(n)) and v["block_sensitivity"][str(n)]["upper"]<0 for n in (2,4)) and rates[a] is not None and rates[b] is not None and rates[a]<=rates[b]
    updates={r["arm"]:r["update"] for r in lock["records"]}
    gain=complete and selected!="incumbent" and updates[selected]>0 and better(selected,"incumbent")
    data=complete and "expanded" in updates and updates["same"]>0 and updates["expanded"]>0 and better("expanded","same")
    return {"study_id":p["study_id"],"comparisons":values,"effective_origins":len(origins),"fully_resolved_registered_panel":complete,"failure_rates":rates,"registered_continuation_criterion_met":gain,"additional_data_criterion_met":data,"no_automatic_promotion":True,"decision":"Report fixed-panel evidence and limitations" if gain else "Retain incumbent; negative or inconclusive","interpretation":"Origin-block intervals are sensitivity analyses, not guaranteed coverage. Continuation and corpus effects are separate."}
