import pytest
from compute_forecast.notebook_diagnostics import interval_summary,build

def test_coverage_and_width_preserve_denominator():
    s=interval_summary({"n_cells":12,"coverage":.75,"mean_width":.08,"pinball":.01})
    assert s["covered_cells"]==9 and s["n_cells"]==12
    assert s["coverage_gap"]==pytest.approx(-.05) and s["mean_width"]==.08
    with pytest.raises(ValueError,match="disagrees"):
        interval_summary({"n_cells":3,"coverage":.5,"mean_width":.08,"pinball":.01})

def test_feedback_tie_does_not_become_identical_actions_or_zero_pending_counts():
    m=lambda label:{"policy":label,"pinball":.01,"n_cells":12,"coverage":.75,"mean_width":.08}
    p={"run_id":"recorded-fixture","mode":"sft","seed":17,"objective":"hard","selected_update":20,"actual_optimizer_updates":100,"comparisons":[m("selected_sft_hard"),m("starting_policy"),m("selected_no_observation")]}
    d=build({"policy_reports":[p]})
    f=d["feedback"][0]
    assert f["same_forecast_loss"] and f["changed_action_sequences"] is None
    assert f["trace_status"]=="pending matched trace analysis"
    a={"run_id":p["run_id"],"ablations":[{"condition":"no_observation","tasks":4,"tasks_with_changed_action_sequence":3,"tasks_with_changed_selected_forecaster":2}]}
    measured=build({"policy_reports":[p],"analysis":{"policies":[a]}})["feedback"][0]
    assert measured["same_forecast_loss"] and measured["changed_action_sequences"]==3 and measured["changed_final_choices"]==2

def test_ledger_counts_only_completed_operational_calls_and_unique_reports():
    cycles=[{"status":"completed","actual_trials":6,"new_executions":5,"actual_cross_role_reads":8},{"status":"running","actual_trials":6,"new_executions":5,"actual_cross_role_reads":8}]
    d=build({"policy_reports":[],"autonomy_runs":cycles})
    assert d["ledger"]["operational_trials"]==6 and d["ledger"]["fresh_operational_modal_calls"]==5
    assert d["ledger"]["cached_result_reveals_per_task"]==6
    with pytest.raises(ValueError,match="Duplicate"):
        build({"policy_reports":[{"run_id":"same"},{"run_id":"same"}]})
