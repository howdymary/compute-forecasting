"""Credential-free reconstruction of versioned public operation arithmetic."""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
def close(a,b):
    if not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12):raise ValueError("Published arithmetic does not reconstruct")
def validate_initialize(v):
    interval=v["interval"];cases=interval["cases"];n=len(cases)
    if n!=interval["n_cells"]:raise ValueError("Interval denominator mismatch")
    if n:
        for key,value in interval["metrics"].items():close(sum(c[key] for c in cases)/n,value)
    if v["new_training_updates"]!=0 or v["learning"]["status"]=="ready":raise ValueError("Original readiness status changed")
    return {"interval_cells":n,"new_training_updates":0}
def validate_feedback(v):
    traces=v["traces"];keys={(o["policy"],o["condition"],o["task_id"]) for o in traces}
    if len(keys)!=len(traces):raise ValueError("Duplicate intervention task")
    if len(traces)!=48 or v["cached_result_reveals"]!=len(traces)*6:raise ValueError("Intervention budget changed")
    if v["actual_sampler_calls"]!=sum(len(t["decisions"]) for t in traces):raise ValueError("Inference accounting mismatch")
    for r in v["results"]:
        outputs=[t for t in traces if t["policy"]==r["policy"] and t["condition"]==r["condition"]]
        reference={t["task_id"]:t for t in traces if t["policy"]==r["policy"] and t["condition"]=="feedback_only"}
        cells=[c for t in outputs for c in t["trace"]["cases"]]
        if len(outputs)!=r["n_tasks"] or len(cells)!=r["n_cells"]:raise ValueError("Intervention denominator mismatch")
        for key,field in [("pinball","loss"),("coverage","covered"),("mean_width","width")]:close(sum(c[field] for c in cells)/len(cells),r[key])
        baseline=[c for t in reference.values() for c in t["trace"]["cases"]]
        close(r["pinball"]-sum(c["loss"] for c in baseline)/len(baseline),r["delta_vs_feedback_only"])
        changed_order=sum(t["trace"]["revealed"]!=reference[t["task_id"]]["trace"]["revealed"] for t in outputs)
        changed_set=sum(set(t["trace"]["revealed"])!=set(reference[t["task_id"]]["trace"]["revealed"]) for t in outputs)
        changed_choice=sum(t["trace"]["selected_config_id"]!=reference[t["task_id"]]["trace"]["selected_config_id"] for t in outputs)
        if (changed_order,changed_set,changed_choice)!=(r["changed_action_sequences"],r["changed_reveal_sets"],r["changed_terminal_choices"]):raise ValueError("Behavioral claim mismatch")
    return {"episodes":len(traces),"conditions":len(v["results"]),"sampler_calls":v["actual_sampler_calls"],"new_optimizer_updates":v["new_optimizer_updates"]}
def check(root="."):
    root=Path(root);base=root/"results/review-v4";report={"status":"verified","credential_free":True,"operation_reports":[],"market_reports":[]}
    index=base/"operations-index.json"
    if index.exists():
        v=json.loads(index.read_bytes())
        for path,meta in v["files"].items():
            if not path.startswith("results/review-v4/") or ".." in Path(path).parts:raise ValueError("Unapproved public path")
            raw=(root/path).read_bytes()
            if len(raw)!=meta["bytes"] or hashlib.sha256(raw).hexdigest()!=meta["sha256"]:raise ValueError("Operation source hash mismatch")
            value=json.loads(raw)
            result=validate_initialize(value) if path.endswith("/initialize.json") else validate_feedback(value) if path.endswith("/feedback.json") else {"inventory_only":True}
            report["operation_reports"].append({"path":path,"sha256":meta["sha256"],**result})
    else:report["operations_status"]="pending_publication"
    for path in sorted((base/"market").glob("*.json")):
        value=json.loads(path.read_bytes())
        for decision in value["plans"]:
            probabilities=list(decision["distribution"].values())
            if any(not math.isfinite(p) or not 0<=p<=1 for p in probabilities) or abs(sum(probabilities)-1)>1e-6:raise ValueError("Invalid float32 planning probabilities")
            if decision["selected_question"]!=max(decision["distribution"],key=decision["distribution"].get):raise ValueError("Planning choice mismatch")
        if value["actual_tinker_decisions"]!=len(value["plans"]):raise ValueError("Planning count mismatch")
        report["market_reports"].append({"path":str(path.relative_to(root)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"decisions":len(value["plans"]),"accuracy_claim":None})
    for path in sorted((base/"runtime").glob("*.json")):
        value=json.loads(path.read_bytes())
        if value.get("status")!="passed" or value.get("prediction_shape")!=[8,3] or value.get("new_training_updates")!=0:raise ValueError("Runtime contract receipt differs")
        if value.get("synthetic_numerical_candidates")!=42 or value.get("synthetic_numerical_rows")!=126:raise ValueError("Synthetic numerical scope differs")
        if "synthetic" not in value.get("fixture","").lower():raise ValueError("Synthetic fixture label missing")
        report.setdefault("runtime_reports",[]).append({"path":str(path.relative_to(root)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"classification":"Contract verification, not forecasting accuracy"})
    return report
def main():
    out=Path("artifacts/public-reproduction-v4");out.mkdir(parents=True,exist_ok=True)
    result=check();(out/"operations-reproduction.json").write_text(json.dumps(result,indent=2))
    print("V4_PUBLIC_REPRODUCTION:"+json.dumps(result),flush=True)
if __name__=="__main__":main()
