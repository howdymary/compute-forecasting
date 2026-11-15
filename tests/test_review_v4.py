import copy
import pytest
from compute_forecast.review_v4 import attribution,indexed,mechanism,read_archive
def report(losses,policy="test"):
    cases=[{"series_id":"synthetic","horizon_days":h,"loss":loss,"baseline_loss":0,"width":.2,"covered":True} for h,loss in zip((1,3,7),losses)]
    return {"policy":policy,"pinball":sum(losses)/3,"n_cells":3,"traces":[{"origin":"2000-01-01","n_cells":3,"cases":cases}]}
def test_attribution_reconstructs_and_zero_baseline():
    a=report([.1,.2,.3]);b=report([.2,.2,.2]);v=attribution(a,b,"fixture")
    assert abs(sum(x["weighted_contribution"] for x in v["groups"]["horizon"])-v["delta"])<1e-12
    assert v["groups"]["series"][0]["relative_skill"] is None
def test_unmatched_and_duplicate_cells_refused():
    a=report([.1,.2,.3]);b=copy.deepcopy(a);b["traces"][0]["cases"][0]["series_id"]="other"
    with pytest.raises(ValueError):attribution(a,b,"bad")
    a["traces"][0]["cases"][1]["horizon_days"]=1
    with pytest.raises(ValueError):indexed(a)
def test_corrupt_archive_refused():
    with pytest.raises(ValueError,match="checksum"):read_archive(b"not the registered archive")
def test_equal_loss_does_not_prove_predictions():
    from compute_forecast.review_v4 import TREE,INITIAL
    choices=INITIAL+TREE
    t={"task_id":"synthetic","origin":"2000-01-01","series_ids":["synthetic"],"validation":{c:{"loss":0,"n_cells":3,"last_label_date":"1999-12-31"} for c in choices},"future_evaluator_only":{c:{"loss":.2,"cases":report([.2]*3)["traces"][0]["cases"]} for c in choices}}
    trace={"task_id":"synthetic","revealed":choices,"selected_config_id":choices[0],"pinball":.2,"n_cells":3,"cases":t["future_evaluator_only"][choices[0]]["cases"]}
    v=mechanism([t],{"traces":[trace]},{"traces":[{**trace,"revealed":INITIAL+list(reversed(TREE))}]})
    assert v["tasks"][0]["prediction_equivalence"] is None
    assert v["tasks"][0]["same_reveal_set"] and not v["tasks"][0]["same_order"]
