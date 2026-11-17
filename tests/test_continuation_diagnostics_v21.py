"""Synthetic contracts for retained-distribution diagnostics."""
import math
import pytest
from compute_forecast.continuation_diagnostics_v21 import vector_metrics,evaluate
def test_identity_and_singular_distributions_are_not_silently_dropped():
    same=vector_metrics([.25,.5,.25],[.25,.5,.25],[-1,0,1],[1.,2.,3.],2.)
    assert same["total_variation_from_incumbent"]==0 and same["forward_kl_from_incumbent"]==0
    assert same["nearest_level_nll"]==math.log(2)
    collapsed=vector_metrics([0.,1.,0.],[.25,.5,.25],[-1,0,1],[1.,2.,3.],1.)
    assert collapsed["entropy_nats"]==0 and collapsed["singular_forward_kl"] and collapsed["forward_kl_from_incumbent"] is None
    assert collapsed["zero_target_mass"] and collapsed["nearest_level_nll"] is None
def test_invalid_mass_and_unmatched_truth_fail_closed():
    with pytest.raises(ValueError):vector_metrics([.5,.5,.5],[.25,.5,.25],[-1,0,1],[1.,2.,3.],2.)
    r={"task_id":"explicit_synthetic","horizon_days":7,"anchor":2.,"outcome":2.,"target_date":"2026-01-08","origin":"2026-01-01","series_id":"synthetic","support_prices":[1.,2.,3.],"probabilities":[.25,.5,.25],"changed_price":False}
    value=evaluate([r],[r],[-1,0,1]);assert value["all"]["n"]==1 and value["changed"]["n"]==0
    with pytest.raises(ValueError):evaluate([r],[{**r,"outcome":3.}],[-1,0,1])
