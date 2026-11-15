import copy,json
from pathlib import Path
from compute_forecast.capability_v5 import rental_pairs,benchmarks,analyze
def study():
    return json.loads(Path("results/value-v5/runs/43757456253/study.json").read_bytes())
def test_pairing_uses_catalog_labels_and_excludes_contract_mismatch():
    s=study();p=rental_pairs(s)
    assert len(p)==1 and p[0]["matched_dates"]==89 and p[0]["source_id"]=="gpurentalprices"
    a=next(v for v in s["history"]["series"] if v["id"]==p[0]["a100_series_id"]);a["pricing_tier"]="synthetic_incompatible"
    assert rental_pairs(s)==[]
def test_precision_scope_remains_workload_specific():
    s=study();b=benchmarks(s)
    assert set(b)=={"cross_benchmark","llm_server","llm_offline"}
    assert b["llm_server"]["throughput_ratio"]>b["cross_benchmark"]["throughput_ratio"]
    assert all(r["id"].endswith("_precmatch") for r in b.values())
def test_cost_ratio_retains_limitations_and_provenance():
    s=study();p=rental_pairs(s)[0];r=analyze(s,p["id"],"cross_benchmark")
    assert 0<r["h100_cost_per_matched_work_relative_to_a100"]<1
    assert r["source_pack_sha256"]==s["pack_sha256"] and len(r["limitations"])>=4
