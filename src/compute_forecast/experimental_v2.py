"""Publish allowlisted derived experimental results; never serve private volumes."""
from __future__ import annotations
import json,os,statistics,time
from pathlib import Path
import modal
from .campaign_v2 import now,protocol,write,digest
from .starter_probe import volume
app=modal.App("compute-forecast-v2-publication")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
def sanitize(value):
    encoded=json.dumps(value,allow_nan=False)
    for forbidden in ("tinker://","sk-","Authorization","MODAL_TOKEN_SECRET","TINKER_API_KEY","raw_response","permitted_private_method_context"):
        if forbidden in encoded:raise ValueError("Private material in public payload")
    return value
def aggregate_grid(grid):
    rows=[]
    for phase,key in (("training","training_origins"),("development","development_origins"),("evaluation","evaluation_origins")):
        origins=[r for r in grid.get("origins",[]) if r["origin"] in protocol()[key] and r["status"]=="completed"]
        for config in grid.get("registry",[]):
            methods=[next(m for m in r["methods"] if m["config_id"]==config["id"]) for r in origins]
            cases=[c for m in methods for c in m["cases"]]
            if not cases:continue
            def score(cs):
                loss=statistics.mean(c["loss"] for c in cs);base=statistics.mean(c["baseline_loss"] for c in cs)
                return {"pinball":loss,"baseline_pinball":base,"skill":1-loss/base if base>1e-12 else None,"coverage":statistics.mean(c["covered"] for c in cs),"mean_width":statistics.mean(c["width"] for c in cs),"n_cells":len(cs)}
            rows.append({"phase":phase,"config":config,**score(cases),"temporal_origins":len(origins),"by_horizon":{str(h):score([c for c in cases if c["horizon_days"]==h]) for h in (1,3,7)},"by_series":{sid:score([c for c in cases if c["series_id"]==sid]) for sid in sorted({c["series_id"] for c in cases})},"fallbacks":sum(sum(m["fallbacks"].values()) for m in methods),"quantile_order_repairs":sum(m["quantile_order_repairs"] for m in methods)})
    return {"rows":rows,"executions":[{k:r.get(k) for k in ("origin","status","run_id","runtime_seconds","modal_call_id","cache_hit","new_numerical_execution")} for r in grid.get("origins",[])],"code_sha":grid.get("code_sha"),"registry_count":len(grid.get("registry",[]))}
@app.function(image=image,cpu=.25,memory=512,timeout=150,volumes={"/data":volume,"/public":public})
def publish(snapshot):
    volume.reload();public.reload()
    curves=[]
    for path in sorted(Path("/data/campaign-v2/policies").glob("*.json")):
        p=json.loads(path.read_text());curves.append({"run_id":p["run_id"],"seed":p["seed"],"objective":p["objective"],"mode":p["mode"],"created_at":p["created_at"],"checkpoints":[{k:c[k] for k in ("update","checkpoint_id","development_pinball")} for c in p.get("checkpoints",[])],"selected_checkpoint_id":p.get("selected",{}).get("checkpoint_id")})
    snapshot.update(schema_version=2,published_at=now(),protocol=protocol(),checkpoint_runs=curves,source_sha=snapshot.get("source_sha"),status="running" if snapshot.get("campaign_status")!="completed" else "completed")
    audit_paths=sorted(Path("/data/campaign-v2/audit").glob("*.json"))
    if audit_paths:
        a=json.loads(audit_paths[-1].read_text());snapshot["audit"]={"dataset_sha256":a["dataset_sha256"],"manifest_entries":a["manifest_entries"],"runtime_seconds":a["runtime_seconds"],"observations":[{"origin":r["origin"],"headline_catalog_count":len(r["headline_catalog"]),"eligible":r["eligible_daily_h100_a100"]} for r in a["observations"]]}
    sanitize(snapshot);path=Path("/public/experimental-v2/summary.json");write(path,snapshot);public.commit()
    return {"public_sha256":digest(snapshot),"checkpoint_runs":len(curves),"completed_policy_runs":len(snapshot.get("policy_reports",[])),"published_at":snapshot["published_at"]}
@app.local_entrypoint()
def main(inputs:str="inputs",output:str="artifacts/v2-publication"):
    root=Path(inputs);snapshot={"source_sha":os.environ.get("GITHUB_SHA"),"policy_reports":[],"campaign_status":os.environ.get("CAMPAIGN_STATUS","running"),"source_run_id":os.environ.get("CAMPAIGN_RUN_ID"),"usage":{"tinker_cost":None,"modal_cost":None,"remaining_credits":None,"cost_status":"Provider cost and remaining balance unavailable; unknown is not zero"}}
    grid=list(root.rglob("grid.json"))
    if grid:snapshot["forecasting"]=aggregate_grid(json.loads(grid[0].read_text()))
    for p in root.rglob("policy-report.json"):
        report=json.loads(p.read_text());report["artifact_file"]=str(p.relative_to(root));snapshot["policy_reports"].append(report)
    ev=list(root.rglob("evidence-summary.json"))
    if ev:snapshot["evidence_collection"]=json.loads(ev[0].read_text())
    evidence=list(root.rglob("evidence.json"))
    if evidence:
        p=json.loads(evidence[0].read_text());snapshot["evidence_sources"]=[{k:s.get(k) for k in ("source_id","url","title","topic","published_at","retrieved_at","content_sha256")} for s in p["sources"]]
        snapshot["evidence_request_count"]=len(p["requests"])
    receipt=publish.remote(snapshot);write(Path(output)/"publication.json",receipt);print("V2_PUBLICATION:"+json.dumps(receipt))
