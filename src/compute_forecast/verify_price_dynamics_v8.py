"""Credential-free reconstruction from the committed permitted v8 result."""
import argparse,hashlib,json,math
from pathlib import Path
from .price_dynamics_v8 import digest,loss,summarize,paired,ordered
SHA="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
def verify(path):
    raw=Path(path).read_bytes();v=json.loads(raw);cells=v["cells"]
    assert v["study_id"]=="price-dynamics-v8" and not v["protected_outcomes_loaded"]
    assert digest(v["protocol"])==v["protocol_sha256"]
    assert v["official_export_sha256"]==SHA
    if Path("results/frozen-v1/forecasts.csv").exists():assert hashlib.sha256(Path("results/frozen-v1/forecasts.csv").read_bytes()).hexdigest()==SHA
    methods=list(v["protocol"]["arms"])+v["protocol"]["references"];keys={}
    for method in methods:
        rows=[r for r in cells if r["method"]==method];kk=[(r["series_id"],r["origin"],r["horizon"]) for r in rows]
        assert len(set(kk))==len(kk),"duplicate forecast cells";keys[method]=set(kk)
        assert len(kk)==v["cohort"]["eligible_cells"]
        for r in rows:
            assert r["series_id"] in v["cohort"]["series_ids"] and r["origin"] in v["cohort"]["origins"]
            assert r["target"]<=v["protocol"]["history_cutoff"]
            ordered(r["quantiles"]);assert math.isclose(loss(r["quantiles"],r["truth"]),r["loss"],rel_tol=1e-12,abs_tol=1e-14)
            assert r["changed"]==(r["truth"]!=r["anchor"])
        assert keys[method]==keys["A"],"unmatched methods"
    for row in v["summary"]:
        rebuilt=summarize(cells,row["method"],row["horizon"])
        for k in ("n","origins","series","loss","coverage","width","fallbacks"):assert rebuilt[k]==row[k],("summary",k)
    for row in v["pairs"]:
        rebuilt=paired(cells,row["candidate"],row["reference"],row["horizon"])
        assert rebuilt==row,"Paired uncertainty differs"
    for row in v["official_scorer_verification"]:assert row["verified_cells"]==len(keys[row["method"]])
    assert len(keys["A"])+v["cohort"]["missing_target_pairs"]==len(v["cohort"]["series_ids"])*len(v["cohort"]["origins"])*3
    report={"status":"passed","artifact_sha256":hashlib.sha256(raw).hexdigest(),"methods":len(methods),"eligible_cells_per_method":len(keys["A"]),"verified_forecast_scores":len(cells),"source_hashes":{"protocol":v["protocol_sha256"],"inputs":v["input_sha256"],"engine":v["engine_sha256"]},"scope":"Published arithmetic only; private inputs and official scorer execution have separate receipts"}
    return report
def main():
    parser=argparse.ArgumentParser();parser.add_argument("study");args=parser.parse_args();print("V8_PUBLIC_VERIFICATION:"+json.dumps(verify(args.study)),flush=True)
if __name__=="__main__":main()
