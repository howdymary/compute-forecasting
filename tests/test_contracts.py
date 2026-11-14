from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from compute_forecast.candidates import candidate_grid
from compute_forecast.contracts import (
    Evidence, Forecast, MemoryExchange, Observation, OfficialContract,
    Phase, PolicyExample, Result, Scope, canonical_hash,
)
from compute_forecast.cutoffs import accept_memory_source, eligible_evidence, visible_observations
from compute_forecast.scoring import diagnostic_skill, pinball_loss, validate_forecast_groups

CUTOFF = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)


def scope(**updates):
    return Scope(study="benchmark", phase="development", task_id="task-1", market_cutoff=CUTOFF, **updates)


def evidence(**updates):
    kwargs = dict(
        run_id=uuid4(), actor_id="evidence", scope=scope(), created_at=CUTOFF + timedelta(days=8),
        url="https://example.invalid/versioned-fixture", title="SYNTHETIC evidence fixture",
        retrieved_at=CUTOFF + timedelta(days=8),
        verified_available_at=CUTOFF - timedelta(days=10),
        version_locator="immutable-fixture-v1", snapshot_sha256="a" * 64,
        claim="Fixture claim", supporting_excerpt="Fixture excerpt",
        historical_status="verified",
    )
    kwargs.update(updates)
    return Evidence(**kwargs)


def test_grid_is_24_unique_configs():
    grid = candidate_grid()
    assert len(grid) == len({c.config_id for c in grid}) == 24


def test_hash_ignores_dictionary_order():
    assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})


def test_future_observation_and_late_publication_cannot_enter_origin():
    rows = [
        Observation(target_key="fixture", period=date(2026, 11, 5), available_at=CUTOFF, value=1, unit="fixture"),
        Observation(target_key="fixture", period=date(2026, 11, 7), available_at=CUTOFF, value=999, unit="fixture"),
        Observation(target_key="fixture", period=date(2026, 11, 5), available_at=CUTOFF + timedelta(seconds=1), value=999, unit="fixture"),
    ]
    assert visible_observations(rows, origin_period=date(2026, 11, 6), cutoff=CUTOFF) == [rows[0]]


def test_timezone_is_required():
    with pytest.raises(ValidationError):
        Scope(study="benchmark", phase="train", task_id="x", market_cutoff=datetime(2026, 11, 6))


def test_unknown_or_future_evidence_is_not_historical():
    assert eligible_evidence(evidence(), scope())
    assert not eligible_evidence(evidence(historical_status="unknown"), scope())
    assert not eligible_evidence(evidence(verified_available_at=CUTOFF + timedelta(days=1)), scope())


def test_verified_evidence_requires_snapshot_proof():
    with pytest.raises(ValidationError):
        evidence(snapshot_sha256=None)


def test_current_news_and_final_memory_are_isolated():
    item = evidence(scope=Scope(study="current_research", phase="development", task_id="task-1"))
    assert not accept_memory_source(item, scope())
    item = evidence(scope=Scope(study="benchmark", phase="final", task_id="task-1", market_cutoff=CUTOFF))
    assert not accept_memory_source(item, scope())


def test_research_timestamp_is_not_backdated_to_market_cutoff():
    item = evidence()
    assert item.created_at > item.scope.market_cutoff
    assert eligible_evidence(item, scope())


def test_new_experiment_result_can_be_used_if_underlying_data_was_eligible():
    result = Result(
        run_id=uuid4(), actor_id="worker", scope=scope(), experiment_id=uuid4(),
        created_at=CUTOFF + timedelta(days=8),
        split="development", scores=(), scorer_status="internal_only",
        origin_count=1, runtime_seconds=0.1, max_input_available_at=CUTOFF,
    )
    assert result.created_at > CUTOFF
    assert accept_memory_source(result, scope())


def test_result_cannot_claim_official_score_without_verified_scorer():
    with pytest.raises(ValidationError):
        Result(
            run_id=uuid4(), actor_id="worker", scope=scope(), experiment_id=uuid4(),
            split="development", scores=(), scorer_status="internal_only",
            official_aggregate=0.1, origin_count=1, runtime_seconds=0.1,
            max_input_available_at=CUTOFF,
        )


def test_result_rejects_post_origin_inputs():
    with pytest.raises(ValidationError):
        Result(
            run_id=uuid4(), actor_id="worker", scope=scope(), experiment_id=uuid4(),
            split="development", scores=(), scorer_status="internal_only",
            origin_count=1, runtime_seconds=0.1,
            max_input_available_at=CUTOFF + timedelta(seconds=1),
        )


def test_training_rejects_final_tasks_and_unmeasured_teachers():
    kwargs = dict(
        task_id="x", split="final", observation={}, eligible_config_ids=("a",),
        chosen_config_id="a", teacher_result_ids=(uuid4(),),
        training_data_cutoff=CUTOFF, teacher_rule_version="1",
    )
    with pytest.raises(ValidationError):
        PolicyExample(**kwargs)
    kwargs.update(split="train", teacher_result_ids=())
    with pytest.raises(ValidationError):
        PolicyExample(**kwargs)


def test_benchmark_memory_never_uses_project_audience():
    with pytest.raises(ValidationError):
        MemoryExchange(
            run_id=uuid4(), actor_id="scientist", scope=scope(),
            operation="read", agent_identity="task-1-scientist",
            audience="project", request_id="request-1",
        )


@pytest.mark.parametrize("actual,predicted,q,expected", [(3, 2, .1, .1), (1, 2, .9, .1), (2, 2, .5, 0)])
def test_pinball_definition(actual, predicted, q, expected):
    assert pinball_loss(actual, predicted, q) == pytest.approx(expected)


def test_zero_baseline_skill_is_undefined():
    assert diagnostic_skill(0, 0) is None
    assert diagnostic_skill(.5, 1) == .5


def test_forecast_completeness_and_quantile_crossing():
    run_id = uuid4()
    rows = [
        Forecast(
            target_key="fixture", origin_ts=CUTOFF, horizon_days=1, quantile=q,
            value=v, unit_from_registry="fixture", config_id="fixture", run_id=run_id,
        ) for q, v in ((.1, 1), (.5, 2), (.9, 3))
    ]
    validate_forecast_groups(rows)
    with pytest.raises(ValueError):
        validate_forecast_groups(rows[:-1])
    with pytest.raises(ValueError):
        validate_forecast_groups([*rows, rows[0]])
    with pytest.raises(ValueError):
        validate_forecast_groups([rows[0].model_copy(update={"value": 5}), *rows[1:]])


def test_official_contract_fails_closed():
    with pytest.raises(RuntimeError, match="Official integration is blocked"):
        OfficialContract().require_ready()
