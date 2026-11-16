import json,math
import pytest
from compute_forecast.direct_forecast_v12 import parse,price_quantiles,cell_loss,matched,messages,conversation
def fixture():
    return {"origin":"2026-07-01","anchor":2.0,"metadata":{"series_id":"synthetic.a100","gpu_model":"A100"},"context":[{"date":"2026-06-30","value":1.9},{"date":"2026-07-01","value":2.0}],"context_missing_days":40,"target_dates":["2026-07-02","2026-07-04","2026-07-08"],"outcomes":[2.1,2.0,1.8],"evidence":[]}
def test_outcome_likelihood_is_not_collapsed_quantile_labels():
    v=json.loads(conversation(fixture())[-1]["content"])
    assert set(v)=={"r1","r3","r7"}
    assert v["r1"]==pytest.approx(math.log(2.1/2),abs=1e-8)
    assert "outcomes" not in messages(fixture())[1]["content"]
def test_future_poisoning_refused():
    t=fixture();t["context"].append({"date":"2026-07-02","value":9})
    with pytest.raises(ValueError):messages(t)
def test_strict_json_and_finite_values():
    assert parse('{"r1":0,"r3":0,"r7":0}')==[0,0,0]
    for bad in ['{"r1":true,"r3":0,"r7":0}','{"r1":NaN,"r3":0,"r7":0}','{"r1":21,"r3":0,"r7":0}','{"r1":0,"r3":0}']:
        with pytest.raises(ValueError):parse(bad)
def test_inverse_scale_and_quantile_order():
    qs=price_quantiles([[-.1,0,.1],[0,.1,.2],[.1,.2,.3]],2)
    assert all(0<a<=b<=c for a,b,c in qs)
    assert qs[0][1]==pytest.approx(2)
    assert price_quantiles([[0,0,0]]*64,2)==[[2,2,2]]*3
def test_pinball_and_cohort_identity():
    assert cell_loss(2,[2,2,2])==0
    with pytest.raises(ValueError):cell_loss(2,[2,1,3])
    rows=[{"series_id":"synthetic","origin":"2026-07-01","horizon_days":7,"loss":0}]
    assert matched(rows,rows)["skill"] is None
    with pytest.raises(ValueError):matched(rows,[])
def test_evidence_gate_is_explicit():
    with pytest.raises(ValueError):messages(fixture(),"price_evidence")
