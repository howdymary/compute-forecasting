"""Continuation scientific contracts, using explicitly synthetic task records."""
import copy,json,random
from pathlib import Path
import pytest
from compute_forecast.continuation_v21 import batches,batch_identity,validate_training,selection,expansion_gate,counts
from compute_forecast.market_state_v19 import prompt
P=json.loads(Path("configs/ce-continuation-v21.json").read_bytes())
def task(i):
    return {"task_id":"synthetic-"+str(i),"series_id":"synthetic-series","origin":"2026-01-02","anchor":2.,"metadata":{"source_id":"synthetic","provider":"synthetic","family":"A100","gpu_model":"synthetic A100","instrument_class":"synthetic_fixture","pricing_tier":"spot"},"context":[{"date":"2026-01-01","value":2.,"available_at":"2026-01-01T17:00:00Z"},{"date":"2026-01-02","value":2.,"available_at":"2026-01-02T17:00:00Z"}],"context_missing_days":40,"target_dates":["2026-01-03","2026-01-05","2026-01-09"],"outcomes":[2.,2.,1.9],"returns":[0.,0.,-.05],"market_state":{}}
def test_fixed_budget_cycles_and_reproducible_order():
    tasks=[task(i) for i in range(5)]
    plan=batches(tasks,17,100,16,480)
    assert len(plan)==100 and all(len(b)==16 for b in plan)
    assert len({(t["task_id"],h) for b in plan for t,h in b})==15
    assert batch_identity(plan)==batch_identity(batches(tasks,17,100,16,480))
    assert batch_identity(plan)!=batch_identity(batches(tasks,29,100,16,480))
def test_training_maturity_and_duplicates_fail_closed():
    t=task(0);assert validate_training([t],P)=={t["task_id"]}
    with pytest.raises(ValueError):validate_training([t,t],P)
    bad=copy.deepcopy(t);bad["target_dates"][-1]="2026-10-12"
    with pytest.raises(ValueError):validate_training([bad],P)
    bad=copy.deepcopy(t);bad["context"][-1]["available_at"]="2026-01-03T00:00:00Z"
    with pytest.raises(ValueError):validate_training([bad],P)
def test_same_price_input_cannot_consume_future_labels_or_market_evidence():
    t=task(0);old=prompt({**t,"arm":"price"},7)
    t["outcomes"]=[999.,888.,777.];t["market_state"]={"peer_return_median_7d":999999.}
    assert prompt({**t,"arm":"price"},7)==old
def test_selection_and_gate_are_development_only():
    def cp(update,loss):return {"update":update,"development":{"primary_pinball":loss,"failures":0}}
    assert selection([cp(20,.2),cp(0,.2),cp(100,.3)])["update"]==0
    result={"status":"completed","arm":"same","selected":cp(20,.097),"retrospective":{"pinball":999}}
    assert expansion_gate([result],.1)["passed"]
    result["retrospective"]["pinball"]=0
    assert expansion_gate([result],.1)["passed"]
    result["selected"]["update"]=0
    assert not expansion_gate([result],.1)["passed"]
def test_counts_do_not_create_independence_from_repeated_contexts():
    value=counts([task(0),task(1)],[-.1,0.,.1])
    assert value["windows"]==2 and value["normalized_context_patterns"]==1 and value["changed_7d"]==2
