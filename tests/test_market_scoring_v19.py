"""Time and receipt gates fail closed before reading future truth."""
from compute_forecast import market_future_v19 as f
from datetime import datetime,timezone
import json
from pathlib import Path
P=json.loads(Path("configs/market-state-v19-prospective.json").read_text())
def test_analysis_gate_never_reads_outcomes(monkeypatch):
    monkeypatch.setattr(f,"validate",lambda *a:True)
    monkeypatch.setattr(f,"snapshots",lambda *a:(_ for _ in ()).throw(AssertionError("Truth was touched")))
    result=f.score({},object(),"2027-04-11T23:59:59+00:00",P,{})
    assert result["status"]=="pending_fixed_analysis_date" and not result["outcomes_loaded"]
def test_receipt_required_after_gate(monkeypatch):
    monkeypatch.setattr(f,"validate",lambda *a:True)
    monkeypatch.setattr(f,"snapshots",lambda *a:(_ for _ in ()).throw(AssertionError("Truth was touched")))
    result=f.score({},object(),"2027-04-12T00:00:01+00:00",P,{})
    assert result["status"]=="pending_verified_publication_receipt" and not result["outcomes_loaded"]
def test_late_publication_is_ineligible(monkeypatch):
    monkeypatch.setattr(f,"validate",lambda *a:True)
    commitment={"origin":"2026-12-20"}
    receipt={"commitment_sha256":f.digest(commitment),"created_at":"2026-12-21T01:00:01+00:00"}
    result=f.score(commitment,object(),"2027-04-12T00:00:01+00:00",P,{},receipt)
    assert result["status"]=="ineligible_late_publication"
