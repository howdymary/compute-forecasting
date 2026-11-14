from datetime import date

import pytest

from compute_forecast.policy_warmup import METHODS, choices, history_features, prepare_cases, question, read_run_csv


def test_history_statistics_do_not_treat_gaps_as_daily_changes():
    rows = [
        {"date": "2026-07-20", "value": "1"},
        {"date": "2026-07-22", "value": "2"},
        {"date": "2026-07-24", "value": "4"},
    ]
    result = history_features(rows, date(2026, 7, 24))
    assert result["observations_in_last_28_calendar_days"] == 3
    assert result["consecutive_daily_changes"] == 0
    assert result["mean_daily_log_change"] is None
    assert result["log_change_1_day"] is None


def test_history_feature_builder_refuses_later_observations():
    with pytest.raises(RuntimeError, match="REFUSED"):
        history_features([{"date": "2026-07-25", "value": "999"}], date(2026, 7, 24))


def test_decision_prompt_excludes_teacher_labels_and_future_results():
    case = {
        "observation": {"horizon_days": 7, "history_statistics": {"unique_values_in_window": 2}},
        "chosen_config_id": "seasonal_naive",
        "series_id": "PRIVATE_ASSET_NAME",
        "origin": "2026-07-24",
        "losses_for_evaluator_only": {"future_outcome": "SECRET_FUTURE_VALUE"},
    }
    prompt = question(case)
    for hidden in ("seasonal_naive", "PRIVATE_ASSET_NAME", "2026-07-24", "SECRET_FUTURE_VALUE"):
        assert hidden not in prompt


def test_training_labels_cannot_cross_preregistered_boundary():
    report = {"cutoff": "2026-07-24", "is_synthetic": False,
              "refusal_check_passed": True, "label_cutoff": "2026-08-01"}
    with pytest.raises(RuntimeError, match="training outcomes"):
        prepare_cases(report, None, "train")


def test_final_origin_cannot_be_used_for_warmup():
    report = {"cutoff": "2026-09-27", "is_synthetic": False, "refusal_check_passed": True}
    with pytest.raises(RuntimeError, match="unexpected"):
        prepare_cases(report, None, "train")


def test_volume_artifact_digest_is_checked_before_parsing():
    class FixtureVolume:
        def read_file(self, path):
            assert path == "/runs/fixture/history.csv"
            return iter([b"series_id,date,value\nfixture,2026-07-24,1\n"])
    report = {"artifact_prefix": "/data/runs/fixture", "artifacts": [{"path": "history.csv", "sha256": "0"*64}]}
    with pytest.raises(RuntimeError, match="digest mismatch"):
        read_run_csv(FixtureVolume(), report, "history.csv")


def test_choice_order_is_reproducible_and_independent_of_outcomes():
    first = {"case_id": "0123456789abcdef0000", "losses_for_evaluator_only": {"last_value": 0}}
    second = {"case_id": first["case_id"], "losses_for_evaluator_only": {"last_value": 999}}
    assert choices(first) == choices(second)
    assert {label for label, _ in choices(first)} == set(METHODS)
