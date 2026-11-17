"""Verify the public v16 arithmetic. No credentials, pack, model or inference needed."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,pathlib,statistics
from compute_forecast.direct_forecast_v12 import cell_loss
from compute_forecast.verify_evidence_v14 import verify as verify_v14
def read(p):return json.loads(p.read_text())
def close(a,b,label):
    if not math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-12):
        raise ValueError(f"{label}: {a!r} != {b!r}")
def check(root):
    root=pathlib.Path(root);cfg=read(root/"configs/direct-v14-diagnosis-v16.json")
    pointer=read(root/"results/direct-v16/latest.json")
    report_path=root/cfg["source_report"]["report_path"];original=read(report_path)
    if hashlib.sha256(report_path.read_bytes()).hexdigest()!=cfg["source_report"]["report_sha256"]:
        raise ValueError("Frozen v14 report hash mismatch")
    verify_v14(report_path.parent)
    path=root/pointer["report_path"];raw=path.read_bytes();d=json.loads(raw)
    if hashlib.sha256(raw).hexdigest()!=pointer["report_sha256"]:
        raise ValueError("Diagnostic pointer hash mismatch")
    manifest=read(path.parent/"manifest.json")
    for item in manifest["files"]:
        p=(path.parent/item["path"]).resolve()
        if not p.is_relative_to(path.parent.resolve()):raise ValueError("Manifest path traversal")
        data=p.read_bytes()
        if len(data)!=item["bytes"] or hashlib.sha256(data).hexdigest()!=item["sha256"]:
            raise ValueError("Diagnostic artifact hash mismatch: "+item["path"])
    rows=list(csv.DictReader((path.parent/"cell-contributions.csv").open()))
    counter=list(csv.DictReader((path.parent/"location-shape-counterfactuals.csv").open()))
    keys=set();saved={};expected_counter={}
    for run in original["runs"]:
        directory=report_path.parent/run["arm"]/("seed-"+str(run["seed"]))
        base=read(directory/"evaluation-base.json");trained=read(directory/"evaluation-selected.json")
        bm={(r["task_id"],r["horizon_days"]):r for r in base["cells"]}
        tm={(r["task_id"],r["horizon_days"]):r for r in trained["cells"]}
        if bm.keys()!=tm.keys():raise ValueError("Source cohort mismatch")
        for (task,h),b in bm.items():
            t=tm[task,h];k=(run["arm"],str(run["seed"]),task,str(h))
            q=["q10","q50","q90"];y=b["outcome"]
            close(y,t["outcome"],"Matched outcome")
            parts=[(max(z*(y-t[n]),(z-1)*(y-t[n]))-max(z*(y-b[n]),(z-1)*(y-b[n])))/3 for z,n in zip((.1,.5,.9),q)]
            saved[k]={"base_loss":b["loss"],"trained_loss":t["loss"],"difference":t["loss"]-b["loss"],**dict(zip(("q10_contribution","q50_contribution","q90_contribution"),parts))}
            tc=[t["q50"]+(b[n]-b["q50"]) for n in q]
            bc=[b["q50"]+(t[n]-t["q50"]) for n in q]
            if min(tc+bc)<=0:raise ValueError("Counterfactual positivity must be explicit")
            a,c=cell_loss(y,tc),cell_loss(y,bc)
            center=((a-b["loss"])+(t["loss"]-c))/2
            shape=((c-b["loss"])+(t["loss"]-a))/2
            expected_counter[k]={"base":b["loss"],"trained":t["loss"],"trained_center_base_shape":a,"base_center_trained_shape":c,"center_shapley":center,"shape_shapley":shape}
    for row in rows:
        k=tuple(row[x] for x in ("arm","seed","task_id","horizon"))
        if k in keys:raise ValueError("Duplicate contribution cell")
        keys.add(k)
        for name,value in saved[k].items():close(row[name],value,name)
        close(sum(float(row[q]) for q in ("q10_contribution","q50_contribution","q90_contribution")),row["difference"],"Quantile sum")
    if keys!=set(saved):raise ValueError("Missing or extra contribution cells")
    ck=set()
    for row in counter:
        k=tuple(row[x] for x in ("arm","seed","task_id","horizon"))
        if k in ck:raise ValueError("Duplicate counterfactual")
        ck.add(k)
        if row["valid_positive_quantiles"]!="True":raise ValueError("Unexpected invalid counterfactual")
        for name,value in expected_counter[k].items():close(row[name],value,name)
    if ck!=keys:raise ValueError("Counterfactual cohort mismatch")
    primary=[r for r in rows if r["horizon"]=="7"];g=d["global_primary"];n=len(primary)
    if n!=132 or len({r["task_id"] for r in primary})!=22:raise ValueError("Primary denominator mismatch")
    if len({r["origin"] for r in primary})!=3 or len({r["series"] for r in primary})!=10:raise ValueError("Market cohort mismatch")
    for name,field in (("base","base_loss"),("trained","trained_loss"),("difference","difference")):
        close(g[name],statistics.mean(float(r[field]) for r in primary),name)
    for q,value in g["q_contributions"].items():
        close(value,statistics.mean(float(r[q+"_contribution"]) for r in primary),q)
    for field,groups in g["groups"].items():
        close(sum(x["weighted_contribution"] for x in groups),g["difference"],field+" contribution sum")
        for group in groups:
            subset=[r for r in primary if r[field]==group["group"]]
            if len(subset)!=group["n"]:raise ValueError(field+" group denominator mismatch")
            close(group["weighted_contribution"],sum(float(r["difference"]) for r in subset)/n,field)
    pc=[r for r in counter if r["horizon"]=="7"]
    for name in ("base","trained","trained_center_base_shape","base_center_trained_shape","center_shapley","shape_shapley"):
        close(d["location_shape"][name],statistics.mean(float(r[name]) for r in pc),name)
    close(d["location_shape"]["center_shapley"]+d["location_shape"]["shape_shapley"],g["difference"],"Shapley sum")
    if any(d[k]!=0 for k in ("new_optimizer_updates","new_inference_requests","new_outcomes_retrieved")):
        raise ValueError("This diagnosis must remain artifact-only")
    print(json.dumps({"status":"verified","source_report_sha256":cfg["source_report"]["report_sha256"],"diagnostic_sha256":pointer["report_sha256"],"primary_cases":22,"repeated_model_cases":132,"market_origins":3,"new_optimizer_updates":0,"scope":"Public quantile, score, cohort, contribution and counterfactual arithmetic; private dataset composition is outside this check"}))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",default=".");check(p.parse_args().root)
