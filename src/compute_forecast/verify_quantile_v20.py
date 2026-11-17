"""Credential-free verification of v20 ensemble and scalar quantile-head arithmetic."""
import hashlib,json,pathlib
from .probability_v18 import digest,summarize
from .quantile_v20 import ensemble,head_quantiles,decompose
from .direct_forecast_v12 import cell_loss
def verify(report):
    assert report["study_id"]=="quantile-training-v20"
    assert "tinker://" not in json.dumps(report) and "private_paths" not in json.dumps(report),"Private model resource in public artifact"
    assert digest(report["protocol"])==report["protocol_sha256"]
    parent_raw=pathlib.Path(report["protocol"]["parent"]["report_path"]).read_bytes()
    assert hashlib.sha256(parent_raw).hexdigest()==report["protocol"]["parent"]["report_sha256"]
    parent=json.loads(parent_raw);runs=[r for r in parent["runs"] if r["arm"]=="price"]
    ens=report["ensembles"]
    for phase in ("development","retrospective"):
        groups=([r["retrospective"]["cells"] for r in runs] if phase=="retrospective" else [[r for case in parent["cases"] for cp in case["checkpoints"] if cp["arm"]=="price" and cp["seed"]==run["seed"] and cp["update"]==run["selected"]["update"] for r in cp["rows"]] for run in runs])
        for kind,value in ens[phase].items():
            assert ensemble(groups,kind)==value["cells"]
            assert summarize(value["cells"])==value["summary"]
    selected=min(ens["development"],key=lambda k:(ens["development"][k]["summary"]["primary_pinball"],0 if k=="quantile_average" else 1))
    assert selected==ens["selection"]["method"]
    for run in report["runs"]:
        state=run["state"]
        assert state["selected"]==min(state["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))
        sets=[run["retrospective"],run["head_zero"]]+list(run["development"].values())
        for evaluation in sets:
            assert summarize(evaluation["cells"])==evaluation["summary"]
            for r in evaluation["cells"]:
                if not r["fallback"]:
                    q,raw,cross=head_quantiles(r["head_probabilities"],r["support_prices"])
                    assert q==[r[k] for k in ("q10","q50","q90")] and raw==r["raw_head_means"] and cross==r["raw_crossing"]
                else:assert [r[k] for k in ("q10","q50","q90")]==[r["anchor"]]*3
                assert abs(cell_loss(r["outcome"],[r[k] for k in ("q10","q50","q90")])-r["loss"])<1e-12
                assert "probabilities" not in r,"Internal head weights must not be labeled predictive mass"
        original=next(x for x in runs if x["seed"]==state["seed"])
        for reference in (original["retrospective"]["cells"],run["head_zero"]["cells"],ens["retrospective"][selected]["cells"]):
            z=decompose(run["retrospective"]["cells"],reference)
            for rows in z["groups"].values():assert abs(sum(r["weighted_contribution"] for r in rows)-z["difference"])<1e-12
    assert report["new_optimizer_updates"]==sum(r["state"]["optimizer_updates"] for r in report["runs"])
    assert hashlib.sha256(pathlib.Path("results/frozen-v1/forecasts.csv").read_bytes()).hexdigest()==report["protocol"]["preservation"]["official_export_sha256"]
    return {"status":"passed","completed_runs":len(report["runs"]),"updates":report["new_optimizer_updates"],"prospective_accuracy":"not established"}
def main():
    pointer=json.loads(pathlib.Path("results/quantile-training-v20/latest.json").read_bytes())
    raw=pathlib.Path(pointer["report_path"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"]
    print(json.dumps(verify(json.loads(raw))))
if __name__=="__main__":main()
