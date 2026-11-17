import math,pytest
from compute_forecast.probability_v18 import probabilities,support,quantiles,crps,bin_index,prompt
def test_distribution_and_quantiles():
    p=probabilities([-1000,-1000,-1000]);assert abs(sum(p)-1)<1e-12
    z=support(2,[-.1,0,.1]);q=quantiles([.1,.8,.1],z)
    assert q[0]==z[0] and q[1]==2 and q[2]==2
    assert quantiles([0,1,0],z)==[2,2,2]
def test_proper_score_and_true_outcomes():
    z=[.9,1,1.1];true=[.3,.4,.3]
    expected=lambda p:sum(mass*crps(p,z,y) for mass,y in zip(true,z))
    assert expected(true)<expected([0,1,0])
    assert crps([0,1,0],z,2)==1
    assert bin_index(z,3)==2
def test_rejects_bad_input():
    with pytest.raises(ValueError):probabilities([float("nan")])
    with pytest.raises(ValueError):quantiles([.3,.3,.3],[1,2,3])
def test_future_poisoning():
    task={"origin":"2026-01-01","context":[{"date":"2026-01-02","value":1}]}
    with pytest.raises(ValueError):prompt(task,7)
def test_loss_metadata_excluded_from_prompt():
    task={"origin":"2026-01-01","anchor":1.,"metadata":{"series_id":"synthetic"},"context":[{"date":"2026-01-01","value":1.}],"context_missing_days":41,"outcomes":[111.234,222.345,333.456]}
    a=prompt(task,7);task["outcomes"]=[9999,8888,7777];assert prompt(task,7)==a
