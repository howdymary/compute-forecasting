"""Explicitly synthetic score-accounting contracts, not market performance."""
import pytest
from compute_forecast.probability_analysis_v18 import diagnostics,paired
from compute_forecast.direct_forecast_v12 import cell_loss
def fixture(offset):
    cases=[];cells=[]
    for i in range(6):
        t={"task_id":str(i),"anchor":1.,"metadata":{"source_id":"synthetic-"+str(i%2),"gpu_model":"A100 synthetic","instrument_class":"synthetic"}}
        y=1. if i%2 else 1.2;q=[.9+offset,1+offset,1.3+offset]
        r={"task_id":str(i),"series_id":str(i%2),"origin":"2026-01-"+str(1+i//2).zfill(2),"horizon_days":7,"outcome":y,"q10":q[0],"q50":q[1],"q90":q[2],"loss":cell_loss(y,q),"crps":None}
        cases.append(t);cells.append(r)
    return cases,cells
def test_contributions_reconstruct_and_zero_skill_is_undefined():
    cases,base=fixture(0);_,candidate=fixture(.1);v=paired(candidate,base,cases)
    for axis in v["contributions"]:assert sum(r["weighted_contribution"] for r in axis["groups"])==pytest.approx(v["difference"])
    for r in base:r["loss"]=0
    assert paired(candidate,base,cases)["skill_vs_reference"] is None
def test_quantile_and_event_denominators():
    cases,rows=fixture(0);v=diagnostics(rows,cases)
    assert v["price_changed"]["changed"]["n"]==3 and v["price_changed"]["unchanged"]["n"]==3
    all=v["all"]["all"]
    assert sum(all["quantile_pinball"].values())/3==pytest.approx(all["pinball"])
    assert all["origins"]==3
