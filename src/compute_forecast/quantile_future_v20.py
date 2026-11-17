"""Separate v20 future contracts; unchanged v19 capture and temporal rules are reused."""
import copy,math
from .probability_v18 import digest,quantiles,support
from .quantile_v20 import head_quantiles
from .market_future_v19 import prepare as source_prepare,validate as source_validate,score as source_score
def effective_protocol(protocol,parent):
    p=copy.deepcopy(parent)
    assert protocol["first_eligible_origin"]==p["first_eligible_origin"] and protocol["final_analysis_not_before"]==p["final_analysis_not_before"]
    p.update(study_id=protocol["study_id"],methods=protocol["methods"],registered_quantile_protocol=protocol)
    assert p["limits"]["max_weekly_origins"]==protocol["origins"]
    return p
def validate(value,p,lock):
    source_validate(value,p,lock)
    tasks={t["series_id"]:t for t in value["price_inputs"]}
    for r in value["rows"]:
        anchor=tasks[r["series_id"]]["anchor"];actual=[r[k] for k in ("q10","q50","q90")]
        if r["fallback"]:
            assert actual==[anchor]*3
            continue
        method=r["method"]
        if method!="official_drift":assert r["support_prices"]==support(anchor,lock["log_levels"])
        if method.startswith("quantile_head"):
            q,raw,cross=head_quantiles(r["head_probabilities"],r["support_prices"])
            assert q==actual and raw==r["raw_head_means"] and cross==r["raw_crossing"]
            assert "probabilities" not in r
        elif method in ("frozen_v19_price17","uniform_quantile_average","uniform_probability_pool"):
            parents=r["parent_probability_vectors"];assert len(parents)==3
            z=r["support_prices"];qs=[quantiles(m,z) for m in parents]
            expected=qs[0] if method=="frozen_v19_price17" else [sum(x[j] for x in qs)/3 for j in range(3)] if method=="uniform_quantile_average" else quantiles([sum(m[j] for m in parents)/3 for j in range(len(z))],z)
            assert expected==actual
        elif method!="official_drift":raise ValueError("Unknown frozen method")
    return value
def score(value,records,at,p,lock,receipt=None):
    validate(value,p,lock)
    return source_score(value,records,at,p,lock,receipt)

def final_analysis(cells,p,selected_ensemble,resolutions,selected_update):
    from .market_analysis_v19 import paired
    selected="quantile_head_selected_seed17";refs=("frozen_v19_price17",selected_ensemble)
    comparisons=[paired(cells,selected,r) for r in refs+("quantile_head_zero_seed17","official_drift")]
    origins={r["origin"] for r in cells if r["horizon_days"]==7}
    complete=len(origins)==p["limits"]["max_weekly_origins"] and len(resolutions)==p["limits"]["max_weekly_origins"] and all(v["status"]=="resolved" for v in resolutions)
    methods=(selected,)+refs+("quantile_head_zero_seed17",)
    primary={m:[r for r in cells if r["method"]==m and r["horizon_days"]==7] for m in methods}
    rates={m:sum(r["fallback"] for r in rows)/len(rows) if rows else None for m,rows in primary.items()}
    def supported(reference):
        v=next(v for v in comparisons if v.get("contrast")==selected+" minus "+reference) if any(v.get("contrast")==selected+" minus "+reference for v in comparisons) else {}
        bound=v.get("estimate") is not None and v["estimate"]<0 and all(v.get("block_sensitivity",{}).get(str(n)) is not None and v["block_sensitivity"][str(n)]["upper"]<0 for n in (2,4))
        return bound and rates[selected] is not None and rates[reference] is not None and rates[selected]<=rates[reference]
    system=complete and all(supported(r) for r in refs)
    weights=complete and selected_update>0 and supported("quantile_head_zero_seed17")
    return {"study_id":p["study_id"],"comparisons":comparisons,"effective_origins":len(origins),"fully_resolved_registered_panel":complete,"failure_rates":rates,"registered_positive_criterion_met":system,"secondary_weight_update_evidence":weights,"interpretation":"System comparison and head-zero weight-update comparison are separate. Neither implies universal improvement; block intervals are sensitivity analyses, not guaranteed coverage.","decision":"System criterion met; report effect and limitations, no automatic deployment" if system else "Incumbent retained; negative or inconclusive under the registered fixed analysis","no_automatic_promotion":True}
