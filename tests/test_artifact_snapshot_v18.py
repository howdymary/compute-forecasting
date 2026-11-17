"""Synthetic publication contracts; these are not historical GPU observations."""
import hashlib,json
import pytest
from compute_forecast.artifact_snapshot_v18 import read_public_snapshot
def fixture(tmp_path):
    root=tmp_path/"forecast-serving/probability-v18";root.mkdir(parents=True)
    raw=json.dumps({"study_id":"direct-probability-v18","synthetic":True}).encode();sha=hashlib.sha256(raw).hexdigest()
    (root/(sha+".json")).write_bytes(raw);(root/"index.json").write_text(json.dumps({"report_sha256":sha}))
    return root,sha
def test_valid_snapshot_and_tamper(tmp_path):
    root,sha=fixture(tmp_path);value,index=read_public_snapshot("direct-probability-v18",tmp_path);assert value["synthetic"] and index["report_sha256"]==sha
    (root/(sha+".json")).write_bytes(b"changed")
    with pytest.raises(ValueError,match="hash"):read_public_snapshot("direct-probability-v18",tmp_path)
def test_path_identity_cannot_escape(tmp_path):
    root,sha=fixture(tmp_path);(root/"index.json").write_text(json.dumps({"report_sha256":"../private"}))
    with pytest.raises(ValueError,match="identity"):read_public_snapshot("direct-probability-v18",tmp_path)
