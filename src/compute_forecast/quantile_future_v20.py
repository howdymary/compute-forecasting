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
