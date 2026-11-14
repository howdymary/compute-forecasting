import json
from compute_forecast.cli import main, preflight

def test_secret_values_never_enter_preflight(monkeypatch):
    monkeypatch.setenv("TINKER_API_KEY", "TEST_SECRET_VALUE_MUST_NOT_APPEAR")
    report = preflight()
    assert report["credential_presence_only"]["TINKER_API_KEY"] is True
    assert "TEST_SECRET_VALUE_MUST_NOT_APPEAR" not in json.dumps(report)

def test_smoke_is_labeled_and_contains_no_official_results(tmp_path):
    output=tmp_path/"smoke.json"
    assert main(["synthetic-smoke","--output",str(output)])==0
    value=json.loads(output.read_text())
    assert value["is_synthetic"] is True
    assert value["market_results"] is None
    assert value["official_forecast_export"] is None

def test_reproduce_blocks_without_official_contract(tmp_path,monkeypatch,capsys):
    from pathlib import Path
    from compute_forecast import cli
    spec=json.loads(Path("configs/pacific.json").read_text())
    spec["official_contract"]["verified"]=False
    file=tmp_path/"unverified-contract.json";file.write_text(json.dumps(spec))
    calls=[];monkeypatch.setattr(cli.subprocess,"run",lambda *a,**k:calls.append(a))
    assert main(["reproduce","--run-spec",str(file)])==2
    assert "BLOCKED" in capsys.readouterr().out
    assert calls==[]
