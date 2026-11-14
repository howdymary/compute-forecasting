"""The public entrypoint must stay hosted, causal, and fail on partial execution."""
import json
from types import SimpleNamespace
import pytest
from compute_forecast import cli

def ready_spec(tmp_path):
    value=json.loads(__import__('pathlib').Path('configs/pacific.json').read_text())
    value['official_contract'].update(verified=True,target_definitions_verified=True,origin_timezone_verified=True,export_schema_verified=True,scorer_verified=True,license_status='restricted',starter_reference='verified-test-reference',starter_sha256=cli.EXPECTED_ARCHIVE_SHA)
    value['data'].update(sha256=cli.EXPECTED_ARCHIVE_SHA,redistribution_allowed=False)
    file=tmp_path/'spec.json';file.write_text(json.dumps(value));return str(file)

def hosted(monkeypatch):
    for name,value in {'GITHUB_ACTIONS':'true','GITHUB_REF_NAME':'compute-observatory','GITHUB_SHA':'a'*40,'MODAL_TOKEN_ID':'unit-test-only','MODAL_TOKEN_SECRET':'unit-test-only','TINKER_API_KEY':'unit-test-only'}.items():monkeypatch.setenv(name,value)
    monkeypatch.setattr(cli.shutil,'which',lambda _: '/remote/modal')

def test_workstation_execution_is_refused_before_any_process(tmp_path,monkeypatch):
    hosted(monkeypatch);monkeypatch.delenv('GITHUB_ACTIONS')
    calls=[];monkeypatch.setattr(cli.subprocess,'run',lambda *a,**k:calls.append(a))
    assert cli.main(['reproduce','--run-spec',ready_spec(tmp_path)])==2
    assert calls==[]

def test_verified_reproduction_executes_cache_prerequisite_before_the_grid(tmp_path,monkeypatch):
    hosted(monkeypatch);calls=[]
    monkeypatch.setattr(cli.subprocess,'run',lambda command,**kwargs:calls.append((command,kwargs)))
    assert cli.main(['reproduce','--run-spec',ready_spec(tmp_path)])==0
    assert len(calls)==2 and calls[0][0][3]=='compute_forecast.starter_probe'
    assert calls[1][0][3]=='compute_forecast.representation_study'
    assert all(kwargs['check'] is True for _,kwargs in calls)

def test_failed_prerequisite_cannot_be_reported_as_success(tmp_path,monkeypatch):
    hosted(monkeypatch);calls=[]
    def fail(command,**kwargs):
        calls.append(command);raise cli.subprocess.CalledProcessError(2,command)
    monkeypatch.setattr(cli.subprocess,'run',fail)
    assert cli.main(['reproduce','--run-spec',ready_spec(tmp_path)])==2
    assert len(calls)==1

def test_policy_training_requires_the_complete_temporal_grid(tmp_path,monkeypatch):
    hosted(monkeypatch);calls=[]
    monkeypatch.setattr(cli.subprocess,'run',lambda *a,**k:calls.append(a))
    assert cli.main(['reproduce','--run-spec',ready_spec(tmp_path),'--train-policy'])==2
    assert calls==[]
