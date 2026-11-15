"""Benchmark-scoped descriptive rental-premium analysis."""
from .review_v4 import digest
def rental_pairs(study):
    series=study["history"]["series"];out=[]
    canonical=lambda value:value.upper().replace(" ","_")
    for a in series:
        if canonical(a["gpu_model"])!="A100_SXM_80GB":continue
        for b in series:
            if canonical(b["gpu_model"])!="H100_SXM_80GB" or any(a[k]!=b[k] for k in ("source_id","instrument_class","pricing_tier")):continue
            av={p["date"]:p["value"] for p in a["points"]};bv={p["date"]:p["value"] for p in b["points"]};days=sorted(set(av)&set(bv))
            if not days:continue
            day=days[-1];out.append({"id":digest([a["id"],b["id"]])[:16],"a100_series_id":a["id"],"h100_series_id":b["id"],"date":day,"a100_rate":av[day],"h100_rate":bv[day],"rental_premium":bv[day]/av[day],"source_id":a["source_id"],"instrument_class":a["instrument_class"],"pricing_tier":a["pricing_tier"],"matched_dates":len(days),"limitation":"Same collector/instrument/tier; provider populations are not matched"})
    return out
def benchmarks(study):
    out={}
    for r in study["capability"]["units_a100_reference"]:
        key=r["benchmark_set_id"]
        if r["gpu_generation"]!="H100" or not key.endswith("_precmatch"):continue
        label="cross_benchmark" if "cross_benchmark_median" in key else "llm_server" if "llm_server" in key else "llm_offline" if "llm_offline" in key else None
        if label:out[label]={"id":key,"throughput_ratio":float(r["capability_units_per_accelerator"]),"rounds":r["rounds_used"],"kind":r["kind"],"scope":"SXM 80GB, shipped repository results, precision-matched; "+label,"raw":r}
    return out
def analyze(study,pair_id,benchmark_id):
    pair=next(p for p in rental_pairs(study) if p["id"]==pair_id);b=benchmarks(study)[benchmark_id]
    ratio=pair["rental_premium"]/b["throughput_ratio"]
    return {"study":"capability-premium-v5","classification":"Retrospective descriptive current research; not a causal price effect or future accuracy claim","pair":pair,"benchmark":b,"h100_cost_per_matched_work_relative_to_a100":ratio,"conditional_h100_cost_reduction":1-ratio,"formula":"(H100 advertised rate / A100 advertised rate) / benchmark throughput ratio","limitations":["Different provider populations can confound source-level median comparisons","Benchmark throughput is not a universal workload conversion","Host, network, availability, software and energy are outside this rental-only ratio","Derived capability composites are not verified MLCommons results"],"source_pack_sha256":study["pack_sha256"],"study_artifact_sha256":digest(study)}
