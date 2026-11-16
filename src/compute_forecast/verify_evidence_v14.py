"""Credential-free hash, quantile and matched-cohort reconstruction."""
import argparse,hashlib,json,pathlib
from .direct_forecast_v12 import cell_loss,summarize,matched,price_quantiles,digest
def verify(root):
    root=pathlib.Path(root).resolve();manifest=json.loads((root/"manifest.json").read_text())
    for item in manifest["files"]:
        f=(root/item["path"]).resolve();assert f.is_relative_to(root) and f.is_file()
        raw=f.read_bytes();assert len(raw)==item["bytes"] and hashlib.sha256(raw).hexdigest()==item["sha256"]
    report=json.loads((root/"report.json").read_text());assert digest(report["protocol"])==report["protocol_sha256"]
    cells={}
    for run in report["runs"]:
        arm,seed=run["arm"],run["seed"];directory=root/arm/("seed-"+str(seed))
        for filename in ["evaluation-base.json","evaluation-selected.json"]+["development-"+str(c["update"])+".json" for c in run["checkpoints"]]:
            value=json.loads((directory/filename).read_text());assert value["summary"]==summarize(value["cells"])
            for task in value["tasks"]:
                assert task["sampling_seed"] is None
                assert task["distinct_vectors"]==len({tuple(v) for v in task["sample_returns"]})
                case=next((c for c in report["development_cases"] if c["task_id"]==task["task_id"]),None)
                # Recover anchor from source-bound development case, or retained forecast inverse.
                if case:anchor=case["anchor"]
                else:
                    row=task["cells"][0];anchor=task.get("anchor")
                for row in task["cells"]:
                    assert abs(cell_loss(row["outcome"],[row["q10"],row["q50"],row["q90"]])-row["loss"])<1e-12
                if anchor is not None and not task["fallback"]:
                    qs=price_quantiles(task["sample_returns"],anchor)
                    assert qs==[[r[k] for k in ("q10","q50","q90")] for r in task["cells"]]
        chosen=min(run["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))
        assert chosen==run["selected"]
        selected=json.loads((directory/"evaluation-selected.json").read_text());cells[(arm,seed)]=selected["cells"]
        assert selected["summary"]==run["retrospective"]
    for comparison in report["comparisons"]:
        seed=comparison["seed"];a,b=cells[("price_evidence",seed)],cells[("price_only",seed)]
        assert matched(a,b)==comparison["all_horizons"]
        assert matched([r for r in a if r["horizon_days"]==7],[r for r in b if r["horizon_days"]==7])==comparison["seven_day"]
    assert not report["audit"]["protected_outcomes_loaded"] and not report["news_used"]
    print(json.dumps({"status":"verified","runs":len(report["runs"]),"matched_seeds":len(report["comparisons"]),"prospective_accuracy":"pending"}))
if __name__=="__main__":
    q=argparse.ArgumentParser();q.add_argument("--results",required=True);verify(q.parse_args().results)
