"""Synthetic remote fixtures for prospective integrity; no market observations."""
import json
from datetime import datetime,timezone
import pytest
pytest.importorskip("modal")
from compute_forecast import price_dynamics_future_v8 as f
def fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(f,"ROOT",tmp_path)
    snapshot={"synthetic":True,"series":{"example":{"2026-11-22":2}}}
    sh=f.digest(snapshot);f.put(tmp_path/"issuance-inputs"/(sh+".json"),snapshot)
    c={"study_id":"price-dynamics-v8-future","kind":"primary_weekly","origin":"2026-11-22","cutoff":"2026-11-22T23:59:59+00:00","issued_at":"2026-11-23T00:10:00+00:00","deadline":"2026-11-23T00:30:00+00:00","snapshot_sha256":sh,"configuration_sha256":f.configuration_hash(),"forecasts":[{"series_id":"synthetic.example","origin":"2026-11-22","horizon":7,"method":"A","target":"2026-11-29","resolution_at":"2026-11-30T00:00:00+00:00","quantiles":[1,2,3]}]}
    return c
def test_immutable_snapshot_and_config(tmp_path,monkeypatch):
    c=fixture(tmp_path,monkeypatch);at=datetime(2026,11,30,tzinfo=timezone.utc)
    assert f.verify_bound_commitment(c,at)
    path=tmp_path/"issuance-inputs"/(c["snapshot_sha256"]+".json");path.write_text('{"synthetic":"changed"}')
    with pytest.raises(ValueError,match="input"):f.verify_bound_commitment(c,at)
def test_unmatured_outcomes_not_scored(tmp_path,monkeypatch):
    c=fixture(tmp_path,monkeypatch)
    f.put(tmp_path/"commitments"/"2026-11-22.json",c)
    monkeypatch.setattr(f,"observations",lambda:{"synthetic.example":{"2026-11-29":2}})
    r=f.evaluate(datetime(2026,11,25,tzinfo=timezone.utc))
    assert r["scored"]==[] and r["pending_cells"]==1 and not r["accuracy_established"]
    c["configuration_sha256"]="bad"
    with pytest.raises(ValueError,match="configuration"):f.verify_bound_commitment(c,datetime(2026,11,30,tzinfo=timezone.utc))
