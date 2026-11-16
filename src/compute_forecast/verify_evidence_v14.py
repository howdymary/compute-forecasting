"""Credential-free hash, quantile and matched-cohort reconstruction."""
import argparse,hashlib,json,pathlib,statistics
from datetime import date,timedelta
from .direct_forecast_v12 import cell_loss,summarize,matched,price_quantiles,digest
def verify(root):
    root=pathlib.Path(root).resolve();manifest=json.loads((root/"manifest.json").read_text())
    for item in manifest["files"]:
        f=(root/item["path"]).resolve();assert f.is_relative_to(root) and f.is_file()
        raw=f.read_bytes();assert len(raw)==item["bytes"] and hashlib.sha256(raw).hexdigest()==item["sha256"]
    report=json.loads((root/"report.json").read_text());assert digest(report["protocol"])==report["protocol_sha256"]
    vintages=json.loads((root/"bls-vintages.json").read_text())
    assert vintages["ready"]
    source_rows={r["content_sha256"]:r for r in vintages["records"]}
    cells={};canonical_cohort=None
    def cohort(rows):
        keys=[(r["series_id"],r["origin"],r["horizon_days"]) for r in rows]
        assert len(keys)==len(set(keys)),"Duplicate evaluation cell"
        for r in rows:
            assert 0<r["q10"]<=r["q50"]<=r["q90"]
            assert date.fromisoformat(r["target_date"])==date.fromisoformat(r["origin"])+timedelta(days=r["horizon_days"])
            assert abs(cell_loss(r["outcome"],[r["q10"],r["q50"],r["q90"]])-r["loss"])<1e-12
        return set(keys)
    for case in report["development_cases"]:
        assert digest(case["history"])==case["history_sha256"]
        assert all(r["date"]<=case["origin"] for r in case["history"])
        feature=case["bls"];assert feature["available_at"]<=case["origin"]+"T23:59:59+00:00"
        source=source_rows[feature["source_content_sha256"]]
        assert feature["source_row_sha256"]==source["values"]["source_row_sha256"]

    for run in report["runs"]:
        arm,seed=run["arm"],run["seed"];directory=root/arm/("seed-"+str(seed))
        for filename in ["evaluation-base.json","evaluation-selected.json"]+["development-"+str(c["update"])+".json" for c in run["checkpoints"]]:
            value=json.loads((directory/filename).read_text());assert value["summary"]==summarize(value["cells"])
            for task in value["tasks"]:
                assert task["sampling_seed"] is None
                assert task["sample_sha256"]==digest(task["sample_returns"])
                assert task["valid_samples"]==len(task["sample_returns"])
                assert task["valid_samples"]+task["invalid_samples"]==task["returned_samples"]==task["requested_samples"]
                assert task["distinct_vectors"]==len({tuple(v) for v in task["sample_returns"]})
                case=next((c for c in report["development_cases"] if c["task_id"]==task["task_id"]),None)
                # Recover anchor from source-bound development case, or retained forecast inverse.
                if case:anchor=case["anchor"]
                else:
                    anchor=report["task_anchors"][task["task_id"]]
                for row in task["cells"]:
                    assert abs(cell_loss(row["outcome"],[row["q10"],row["q50"],row["q90"]])-row["loss"])<1e-12
                if anchor is not None and not task["fallback"]:
                    qs=price_quantiles(task["sample_returns"],anchor)
                    assert qs==[[r[k] for k in ("q10","q50","q90")] for r in task["cells"]]
        chosen=min(run["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))
        assert chosen==run["selected"]
        selected=json.loads((directory/"evaluation-selected.json").read_text());cells[(arm,seed)]=selected["cells"]
        base=json.loads((directory/"evaluation-base.json").read_text())
        eligible=cohort(selected["cells"])
        if canonical_cohort is None:canonical_cohort=eligible
        assert eligible==canonical_cohort==cohort(base["cells"]),"Mismatched evaluation cohort"
        assert selected["summary"]==run["retrospective"] and base["summary"]==run["base"]
        assert matched(selected["cells"],base["cells"])==run["comparison_to_base"]
        for name,reference in run["references"].items():
            assert cohort(reference["cells"])==eligible
            assert summarize(reference["cells"])==reference["summary"]
            assert matched(selected["cells"],reference["cells"])==reference["comparison"]
        diagnostics=run.get("sampling_diagnostics")
        if diagnostics:
            assert diagnostics["valid_samples"]==sum(t["valid_samples"] for t in selected["tasks"])
            assert diagnostics["zero_width_cells"]==sum(r["q10"]==r["q90"] for r in selected["cells"])
        for case in report["development_cases"]:
            for shown in case["forecasts"]:
                if (shown["arm"],shown["seed"])!=(arm,seed):continue
                original=json.loads((directory/("development-"+str(shown["update"])+".json")).read_text())
                task=next(t for t in original["tasks"] if t["task_id"]==case["task_id"])
                assert shown["cells"]==task["cells"],"Displayed forecast differs from retained prediction"

    for comparison in report["comparisons"]:
        seed=comparison["seed"];a,b=cells[("price_evidence",seed)],cells[("price_only",seed)]
        assert matched(a,b)==comparison["all_horizons"]
        assert matched([r for r in a if r["horizon_days"]==7],[r for r in b if r["horizon_days"]==7])==comparison["seven_day"]
    if report["comparisons"]:
        summary=report["paired_summary"];origins={}
        for comparison in report["comparisons"]:
            for origin,delta in comparison["seven_day"]["by_origin"].items():origins.setdefault(origin,[]).append(delta)
        means={o:statistics.mean(ds) for o,ds in sorted(origins.items())}
        assert summary["paired_seeds"]==len(report["comparisons"]) and summary["origin_mean_differences"]==means
        assert summary["mean_seed_primary_difference"]==statistics.mean(c["seven_day"]["mean_difference"] for c in report["comparisons"])
    assert not report["audit"]["protected_outcomes_loaded"] and not report["news_used"]
    print(json.dumps({"status":"verified","runs":len(report["runs"]),"matched_seeds":len(report["comparisons"]),"prospective_accuracy":"pending"}))
if __name__=="__main__":
    q=argparse.ArgumentParser();q.add_argument("--results",required=True);verify(q.parse_args().results)
