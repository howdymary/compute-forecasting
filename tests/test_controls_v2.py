import pytest
pytest.importorskip("modal")
pytest.importorskip("sklearn")
pytest.importorskip("scipy")
from compute_forecast.controls_v2 import configuration_vector,select_trials
from compute_forecast.policy_v2 import REGISTRY
def test_all_registered_configurations_have_distinct_control_representations():
    assert len({tuple(configuration_vector(c["id"])) for c in REGISTRY})==len(REGISTRY)
def test_adaptive_control_cannot_read_future_outcomes_to_choose_trials():
    class Forbidden(dict):
        def __getitem__(self,key):raise AssertionError("Future outcome read during selection")
    task={"scale":.1,"validation":{c["id"]:{"loss":.01+i*.001} for i,c in enumerate(REGISTRY)},"future_evaluator_only":Forbidden()}
    ids=select_trials(task)
    assert len(ids)==6 and len(set(ids))==6
