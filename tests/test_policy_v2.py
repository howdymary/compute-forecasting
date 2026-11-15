"""Policy-information and sampled-action contracts."""
import json
import pytest
pytest.importorskip("modal")
from compute_forecast.policy_v2 import observation,menu,REGISTRY,INITIAL,demonstration_examples

def task():
    validation={c["id"]:{"loss":.01+i*.001,"n_cells":3,"last_label_date":"2026-07-10"} for i,c in enumerate(REGISTRY)}
    return {"task_id":"train","origin":"2026-07-18","phase":"training","observation":{"n_series":1},"validation":validation,"future_evaluator_only":{"SECRET_UNREVEALED_OUTCOME":99},"scale":.1}
def test_actor_cannot_observe_hidden_reward_or_untested_scores():
    t=task();obs=observation(t,INITIAL);encoded=json.dumps(obs)
    assert "SECRET_UNREVEALED_OUTCOME" not in encoded and "future" not in encoded
    assert [r["config_id"] for r in obs["observed_trials"]]==INITIAL

def test_every_bounded_menu_has_supported_choice_count():
    remaining=[c["id"] for c in REGISTRY if c["id"] not in INITIAL]
    pending=[()]
    while pending:
        prefix,groups=menu(remaining,pending.pop())
        assert 1<=len(groups)<=6
        for label,ids in groups:
            if len(ids)>1:pending.append((*prefix,label))

def test_soft_teacher_normalizes_and_never_accepts_evaluation_tasks():
    examples=demonstration_examples([task()],"soft",17)
    assert examples and all(abs(sum(e["targets"].values())-1)<1e-12 for e in examples)
    t=task();t["phase"]="evaluation"
    with pytest.raises(ValueError):demonstration_examples([t],"hard",17)
