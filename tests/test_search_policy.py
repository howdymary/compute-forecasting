"""Tests that search decisions cannot see or optimize future evaluation outcomes."""
from copy import deepcopy
from datetime import date,timedelta
import json
import pytest
pytest.importorskip("modal")
pytest.importorskip("numpy")
from compute_forecast.search_policy import INITIAL,CANDIDATES,model_observation,question,demonstrations,finish,make_tasks
from compute_forecast.representation_study import ORIGINS,PACK_SHA256

def task():
    ids=(*INITIAL,*CANDIDATES)
    return {"task_id":"abcdef1234567890abcd","origin":"2026-07-24","phase":"training","observation":{"n_primary_series":2,"mean_log_changes":[0,0,0,0]},"validation":{c:{"loss":float(i+1),"n_cells":18,"source_run_ids":["completed-prior-run"],"last_label_date":"2026-07-24"} for i,c in enumerate(ids)},"future_evaluator_only":{c:{"loss":float(100-i),"n_cells":6} for i,c in enumerate(ids)},"future_source_run_id":"held-by-evaluator","dataset_sha256":PACK_SHA256}

def test_future_outcomes_do_not_change_the_model_prompt():
    original=task();changed=deepcopy(original)
    for row in changed["future_evaluator_only"].values():row["loss"]=938472.123
    assert question(original,list(INITIAL))==question(changed,list(INITIAL))
    assert "future_evaluator_only" not in json.dumps(model_observation(original,list(INITIAL)))
    assert "938472" not in question(changed,list(INITIAL))

def test_unmatured_trial_is_refused_before_rendering():
    value=task();value["validation"][INITIAL[0]]["last_label_date"]="2026-07-25"
    with pytest.raises(ValueError,match="nonmatured"):question(value,list(INITIAL))

def test_development_tasks_cannot_supply_training_demonstrations():
    value=task();value["phase"]="development"
    with pytest.raises(ValueError,match="only training"):demonstrations([value])

def test_training_export_has_no_future_scores_or_evaluator_identifiers():
    rows=demonstrations([task()]);encoded=json.dumps(rows)
    assert rows and all(r["teacher_last_label_date"]<="2026-07-24" for r in rows)
    assert "future_evaluator" not in encoded and "held-by-evaluator" not in encoded

def test_incumbent_uses_validation_even_when_future_oracle_would_disagree():
    value=task();revealed=[*INITIAL,*CANDIDATES[:4]]
    value["future_evaluator_only"][INITIAL[0]]["loss"]=999
    value["future_evaluator_only"][CANDIDATES[0]]["loss"]=0
    row=finish(value,revealed)
    assert row["selected_config_id"]==INITIAL[0]
    assert row["future_pinball"]==999 and row["trials"]==6

def test_grid_rejects_validation_labels_after_the_decision_cutoff():
    ids=(*INITIAL,*CANDIDATES,"drift","seasonal_naive")
    reports=[]
    for origin in ORIGINS:
        reports.append({"origin":origin,"label_end":(date.fromisoformat(origin)+timedelta(days=7)).isoformat(),"status":"completed","is_synthetic":False,"dataset_sha256":PACK_SHA256,"final_period_opened":False,"run_id":"run-"+origin,"observation":{},"results":[{"config_id":c,"exact_metrics":{"pinball":1.0,"n_cells":6}} for c in ids]})
    next(r for r in reports if r["origin"]=="2026-05-02")["label_end"]="2026-05-10"
    grid={"protocol":"representation-study-v2","code_sha":"a"*40,"final_period_opened":False,"origins":reports}
    with pytest.raises(ValueError,match="not mature"):make_tasks(grid,"a"*40)


def test_hierarchical_choices_preserve_every_untried_experiment_under_api_limits():
    from compute_forecast.search_policy import family_choices,parameter_choices
    value=task();revealed=[*INITIAL,*CANDIDATES[:3]]
    families=family_choices(value,revealed)
    assert 1<=len(families)<=6
    options=[parameter_choices(value,revealed,family) for family,_ in families]
    assert all(1<=len(stage)<=4 for stage in options)
    identifiers=[identifier for stage in options for identifier,_ in stage]
    assert len(identifiers)==len(set(identifiers))
    assert set(identifiers)==set(CANDIDATES)-set(revealed)


def test_both_hierarchical_prompts_exclude_future_evaluation_results():
    from compute_forecast.search_policy import family_question,parameter_question,family_choices
    original=task();changed=deepcopy(original)
    for row in changed['future_evaluator_only'].values():row['loss']=987654.321
    revealed=list(INITIAL);family=family_choices(original,revealed)[0][0]
    assert family_question(original,revealed)==family_question(changed,revealed)
    assert parameter_question(original,revealed,family)==parameter_question(changed,revealed,family)


def test_single_remaining_parameter_is_forced_without_removing_experiments():
    from compute_forecast.search_policy import forced_choice,family_choices,parameter_choices
    value=task();same_family=[c for c in CANDIDATES if c.startswith('ridge_level_target_only_')]
    revealed=[*INITIAL,*same_family[:3]]
    remaining=parameter_choices(value,revealed,'level__target_only')
    assert len(remaining)==1 and forced_choice(remaining)==same_family[3]
    assert forced_choice(family_choices(value,revealed)) is None
    with pytest.raises(ValueError,match='No eligible'):forced_choice([])
