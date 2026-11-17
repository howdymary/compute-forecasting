"""Synthetic publication-contract tests; mock verification is never scientific proof."""
import importlib.util,json,pathlib,pytest
from compute_forecast.probability_v18 import digest
spec=importlib.util.spec_from_file_location("publication_contract","scripts/attest_market_v19.py");module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def setup(root):
    commitment={"origin":"2026-12-20","kind":"synthetic_unit_fixture_no_market_values"}
    (root/"index.json").write_text('{"kind":"synthetic status"}')
    (root/"commitment-synthetic.json").write_text(json.dumps(commitment))
    module.build(root);return commitment
def mocked_verification(monkeypatch):
    def verify(command,**kwargs):
        assert "--signer-workflow" in command and "--source-ref" in command
        return json.dumps([{"verificationResult":{"verifiedTimestamps":[{"timestamp":"2026-12-21T00:10:00Z"}]}}])
    monkeypatch.setattr(module.subprocess,"check_output",verify)
def test_forecast_manifest_excludes_mutable_status(tmp_path,monkeypatch):
    commitment=setup(tmp_path);manifest=json.loads((tmp_path/"commitment-manifest.json").read_text())
    assert [r["name"] for r in manifest["files"]]==["commitment-synthetic.json"]
    mocked_verification(monkeypatch);receipt=module.verify(tmp_path,"synthetic-owner/repo")["2026-12-20"]
    assert receipt["commitment_sha256"]==digest(commitment) and receipt["created_at"]=="2026-12-21T00:10:00+00:00"
def test_changed_commitment_fails_manifest_hash(tmp_path,monkeypatch):
    setup(tmp_path);(tmp_path/"commitment-synthetic.json").write_text('{"origin":"2026-12-27","kind":"tampered fixture"}')
    mocked_verification(monkeypatch)
    with pytest.raises(AssertionError):module.verify(tmp_path,"synthetic-owner/repo")
def test_predicate_date_is_not_a_verified_timestamp(tmp_path,monkeypatch):
    setup(tmp_path)
    monkeypatch.setattr(module.subprocess,"check_output",lambda *a,**kw:json.dumps([{"verificationResult":{"verifiedTimestamps":[],"statement":{"predicate":{"startedOn":"2026-12-21T00:10:00Z"}}}}]))
    with pytest.raises(AssertionError,match="verified publication timestamp"):module.verify(tmp_path,"synthetic-owner/repo")
