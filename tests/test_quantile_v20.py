"""Focused contracts for direct quantile training and fixed ensemble comparisons."""
import copy,math
import pytest
from compute_forecast.quantile_v20 import *
def test_gradient_matches_finite_difference():
    torch=pytest.importorskip("torch")
    logits=torch.tensor([[-1.,.3,.9],[.5,-.7,.1],[.2,.4,-.2]],dtype=torch.double,requires_grad=True)
    z=torch.tensor([1.,2.,4.],dtype=torch.double);y=torch.tensor(2.6,dtype=torch.double)
    assert torch.autograd.gradcheck(lambda a:tensor_loss(a,z,y,2.)[0],(logits,),eps=1e-6,atol=1e-6)
def test_proper_asymmetric_loss_and_ordered_decode():
    torch=pytest.importorskip("torch")
    z=torch.tensor([1.,2.,4.]);y=torch.tensor(2.5)
    scores=torch.tensor([[6.,0.,0.],[0.,6.,0.],[0.,0.,6.]],requires_grad=True)
    v,q,raw=tensor_loss(scores,z,y,1.)
    expected=sum(max(t*(2.5-float(x)),(t-1)*(2.5-float(x))) for t,x in zip(TAUS,q))/3
    assert float(v)==pytest.approx(expected);v.backward();assert torch.isfinite(scores.grad).all() and scores.grad.abs().sum()>0
    q,raw,cross=head_quantiles([[0.,0.,1.],[0.,1.,0.],[1.,0.,0.]],[1.,2.,4.])
    assert q==[1.,2.,4.] and raw==[4.,2.,1.] and cross
def test_ensemble_cohorts_and_convex_pinball():
    def row(p):
        q=quantiles(p,[1.,2.,4.])
        return dict(task_id="synthetic",series_id="synthetic",source_id="fixture",gpu_model="fixture",instrument_class="fixture",origin="2026-01-01",horizon_days=7,target_date="2026-01-08",outcome=2.5,anchor=2.,support_prices=[1.,2.,4.],probabilities=p,q10=q[0],q50=q[1],q90=q[2],loss=cell_loss(2.5,q),fallback=False,changed_price=True,out_of_support=False)
    parents=[[row(p)] for p in ([.2,.7,.1],[.05,.9,.05],[.1,.1,.8])]
    q=ensemble(parents,"quantile_average")[0];pool=ensemble(parents,"probability_pool")[0]
    assert q["loss"]<=statistics.mean(g[0]["loss"] for g in parents)+1e-12
    assert q["probabilities"] is None and pool["probabilities"] is not None
    bad=copy.deepcopy(parents);bad[1][0]["outcome"]=3.
    with pytest.raises(ValueError):ensemble(bad,"probability_pool")
def test_diagnostics_reconstruct_and_gate_keeps_zero():
    def row(q):return dict(task_id="synthetic",series_id="s",origin="2026-01-01",horizon_days=7,target_date="2026-01-08",outcome=2.5,anchor=2.,gpu_model="fixture",changed_price=True,q10=q[0],q50=q[1],q90=q[2],loss=cell_loss(2.5,q))
    result=decompose([row([1.,2.,3.])],[row([1.,2.,4.])])
    for groups in result["groups"].values():assert sum(x["weighted_contribution"] for x in groups)==pytest.approx(result["difference"])
    assert not expansion_gate({"selected":{"update":0,"development":{"primary_pinball":.1,"failures":0}},"checkpoints":[{"development":{"primary_pinball":.1}}]},.2)["passed"]
def test_candidate_prompt_excludes_labels():
    pytest.importorskip("tinker_cookbook")
    t=dict(origin="2026-01-02",anchor=2.,metadata={},context=[{"date":"2026-01-01","value":2.,"available_at":"2026-01-01T00:00:00Z"},{"date":"2026-01-02","value":2.,"available_at":"2026-01-02T00:00:00Z"}],context_missing_days=40,market_state={},outcomes=[999.,999.,999.])
    d=decision(t,7,.1,[-.1,0.,.1])
    assert "999" not in d.text and '"quantile_tau":0.1' in d.text
    t["context"][-1]["date"]="2026-01-03"
    with pytest.raises(ValueError):decision(t,7,.1,[-.1,0.,.1])
