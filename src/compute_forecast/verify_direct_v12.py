"""Credential-free reconstruction of published direct-model arithmetic."""
import argparse,hashlib,json
from pathlib import Path
from .direct_forecast_v12 import cell_loss,summarize,matched
def verify(root):
    root=Path(root);manifest=json.loads((root/"manifest.json").read_text())
    for f in manifest["files"]:
        path=root/f["path"]
        assert path.is_relative_to(root) and path.is_file()
        raw=path.read_bytes()
        assert len(raw)==f["bytes"] and hashlib.sha256(raw).hexdigest()==f["sha256"],f["path"]
    report=json.loads((root/"report.json").read_text())
    assert not report["audit"]["protected_outcomes_loaded"]
    assert all(s["metadata"]["instrument_class"] in ("hyperscaler_spot","neocloud_rate_card") for s in report["audit"]["series"])
    for state in report["runs"]:
        directory=root/("seed-"+str(state["seed"]))
        selected=json.loads((directory/"evaluation-selected.json").read_text());base=json.loads((directory/"evaluation-base.json").read_text())
        for payload in (selected,base):
            for r in payload["cells"]:
                assert abs(r["loss"]-cell_loss(r["outcome"],[r["q10"],r["q50"],r["q90"]]))<1e-10
            assert summarize(payload["cells"])==payload["summary"]
        assert matched(selected["cells"],base["cells"])==state["comparison_to_base"]
        assert state["selected"]==min(state["checkpoints"],key=lambda r:(r["development"]["primary_pinball"],r["update"]))
        for cp in state["checkpoints"]:
            dev=json.loads((directory/("development-"+str(cp["update"])+".json")).read_text())
            assert dev["summary"]==cp["development"]
        for reference in state["references"].values():
            assert summarize(reference["cells"])==reference["summary"]
            assert matched(selected["cells"],reference["cells"])==reference["comparison"]
    print(json.dumps({"status":"verified","study_id":report["study_id"],"completed_seeds":[r["seed"] for r in report["runs"]],"cohort":report["audit"]["phase_tasks"],"prospective_accuracy":"pending"}))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--results",required=True);verify(p.parse_args().results)
