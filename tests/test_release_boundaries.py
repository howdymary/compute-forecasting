"""Release tests must not open the dataset or make service calls."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import pytest
pytest.importorskip('modal')
pytest.importorskip('numpy')
from compute_forecast.freeze_contract import PACK_SHA,FINAL_ORIGINS,numerical_code_hashes,validate_freeze
from compute_forecast.export_submission import validate_export,scenario_outlook


def valid_freeze():
    return {'schema_version':'1','dataset_sha256':PACK_SHA,'frozen_at':(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),'final_truth_opened':False,'final_origins':list(FINAL_ORIGINS),'trial_budget':6,'common_initial':['last_value','last_value_empirical'],'policy_model':'Qwen/Qwen3.5-4B','policy_checkpoint_label':'sft_epoch_1','policy_checkpoint':'tinker://unit-test-only/sampler_weights/checkpoint','official_method':'last_value_empirical','official_selection_last_label':'2026-09-19','policy_training_run_id':1,'official_selection_run_id':2,'numerical_code_sha256':numerical_code_hashes()}


def test_numeric_code_change_invalidates_a_freeze():
    value=valid_freeze();value['numerical_code_sha256']['search_policy.py']='0'*64
    with pytest.raises(ValueError,match='code changed'):validate_freeze(value)


def test_future_or_naive_freeze_times_are_refused():
    value=valid_freeze();value['frozen_at']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    with pytest.raises(ValueError,match='freeze time'):validate_freeze(value)
    value['frozen_at']='2026-01-01T00:00:00'
    with pytest.raises(ValueError,match='freeze time'):validate_freeze(value)


def test_previously_opened_final_protocol_is_refused():
    value=valid_freeze();value['final_truth_opened']=True
    with pytest.raises(ValueError,match='before evaluation'):validate_freeze(value)


def export_rows():
    return [{'series_id':'SCHEMA_FIXTURE_ONLY','origin_date':'2026-11-06','horizon_days':str(h),'q10':'1','q50':'2','q90':'3'} for h in (1,3,7)]


def test_missing_horizon_cannot_produce_complete_submission():
    with pytest.raises(ValueError,match='incomplete'):validate_export(export_rows()[:2],{'SCHEMA_FIXTURE_ONLY'})


def test_crossing_or_nonpositive_quantiles_are_refused():
    rows=export_rows();rows[0]['q10']='4'
    with pytest.raises(ValueError,match='crossing'):validate_export(rows,{'SCHEMA_FIXTURE_ONLY'})
    rows=export_rows();rows[0]['q10']='0'
    with pytest.raises(ValueError,match='nonpositive'):validate_export(rows,{'SCHEMA_FIXTURE_ONLY'})


def test_duplicate_official_cells_are_refused():
    rows=export_rows();rows.append(deepcopy(rows[0]))
    with pytest.raises(ValueError,match='duplicate'):validate_export(rows,{'SCHEMA_FIXTURE_ONLY'})


def test_long_term_scenarios_do_not_claim_calibrated_probabilities():
    value=scenario_outlook()
    assert value['confidence_level'] is None and value['scenario_probabilities'] is None
    assert {r['years'] for r in value['results']}=={2,3}
    assert 'hypothetical' in value['resale_reference']
