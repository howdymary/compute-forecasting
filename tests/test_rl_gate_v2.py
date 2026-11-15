import pytest
pytest.importorskip("modal")
from compute_forecast.policy_v2 import reachable_training_rewards,REGISTRY,INITIAL
def training_task():
    ids=[c["id"] for c in REGISTRY]
    return {"task_id":"gate","phase":"training","scale":1.0,"validation":{c:{"loss":10.0 if c in INITIAL else 1+i} for i,c in enumerate(ids)},"future_evaluator_only":{c:{"loss":20.0+i} for i,c in enumerate(ids)}}
def test_gate_checks_the_actual_clipped_reward_not_unclipped_loss_variation():
    result=reachable_training_rewards(training_task())
    assert result["possible_winners"]>1 and result["possible_terminal_reward_range"]==0
    assert result["reward_is_clipped"]
def test_gate_refuses_evaluation_outcomes():
    task=training_task();task["phase"]="evaluation"
    with pytest.raises(ValueError):reachable_training_rewards(task)
