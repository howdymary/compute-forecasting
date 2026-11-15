import json,random
import pytest
from compute_forecast.policy_v2 import recover_prefix

def prefix():
    rng=random.Random(17)
    for _ in range(13):rng.randrange(4)
    updates=[{"update":i,"rollout_iteration":i+3} for i in range(1,11)]
    traces=[{"step":s,"phase":"training","reward_label_end":"2026-07-31"} for s in range(1,14) for _ in range(4)]
    return rng,updates,traces,{"update":10,"rollout_iteration":13}

def test_resume_preserves_rng_and_cumulative_iteration_budget():
    rng,updates,traces,recovery=prefix()
    step,restored=recover_prefix(updates,traces,recovery,json.loads(json.dumps(rng.getstate())),60)
    assert [restored.randrange(9) for _ in range(20)]==[rng.randrange(9) for _ in range(20)]
    assert list(range(step+1,61))==list(range(14,61))
    assert len(list(range(step+1,61)))==47

def test_resume_refuses_missing_trajectory_and_lookahead():
    rng,updates,traces,recovery=prefix()
    with pytest.raises(ValueError):recover_prefix(updates,traces[:-1],recovery,rng.getstate(),60)
    traces[0]["phase"]="evaluation"
    with pytest.raises(ValueError):recover_prefix(updates,traces,recovery,rng.getstate(),60)

def test_resume_does_not_discard_uncheckpointed_optimizer_work():
    rng,updates,traces,recovery=prefix()
    updates.append({"update":11,"rollout_iteration":14})
    with pytest.raises(ValueError):recover_prefix(updates,traces,recovery,rng.getstate(),60)
