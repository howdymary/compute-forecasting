import base64
import pytest
from compute_forecast import final_findings_v2 as report

def test_incomplete_reports_cannot_publish_completed_findings():
    with pytest.raises(ValueError,match="Complete six-SFT/three-RL"):
        report.validate({"policy_reports":[]})

def test_metagame_and_other_refs_are_rejected_before_api_calls(monkeypatch):
    monkeypatch.setenv("GITHUB_REF","refs/heads/metagame")
    monkeypatch.setattr(report,"gh",lambda *args,**kwargs:pytest.fail("Unexpected API call"))
    with pytest.raises(ValueError,match="Wrong publication branch"):
        report.publish({},"")

def test_publication_refuses_unapproved_paths_before_creating_blobs(monkeypatch):
    monkeypatch.setenv("GITHUB_REF","refs/heads/compute-observatory")
    monkeypatch.setenv("GITHUB_REPOSITORY","howdymary/compute-forecasting")
    mutations=[]
    def api(path,method="GET",body=None):
        if method!="GET":mutations.append(path);pytest.fail("Unexpected mutation")
        if "/git/ref/" in path:return {"object":{"sha":"head"}}
        if "/git/commits/" in path:return {"tree":{"sha":"tree"}}
        return {"content":base64.b64encode(b"[Experimental Research v2](example)").decode()}
    monkeypatch.setattr(report,"gh",api)
    with pytest.raises(ValueError,match="Unexpected publication path"):
        report.publish({"metagame.txt":"bad"},"replacement")
    assert mutations==[]
