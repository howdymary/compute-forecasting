"""Publish compact verified mask counts; keep full fit records in their artifact."""
from __future__ import annotations
import json,os
from pathlib import Path
import modal
from .campaign_v2 import write,now,digest
from .starter_probe import PACK_SHA256
app=modal.App("compute-forecast-v2-feature-summary")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
def summarize(report):
    if report["code_sha"]!="fc29e92ac7d448a913ea8884a570d0a70ea5f78b" or report["dataset_sha256"]!=PACK_SHA256:raise ValueError("Unverified feature audit revision")
    rows=[]
    for origin in report["origins"]:
        if origin["numerical_scores_changed"]:raise ValueError("Feature audit changed a score")
        for aux in ("target_only","raw","fixed_basket"):
            candidates=[r for r in origin["rows"] if r["aux"]==aux]
            fits=[f for r in candidates for f in r["fit_masks"] if f["used"]]
            width=6 if aux=="target_only" else 13
            cells=sum(f["rows"]*width for f in fits);aux_cells=sum(f["rows"]*7 for f in fits) if aux!="target_only" else 0
            missing=sum(f["missing_training_cells"] for f in fits);aux_missing=sum(f["missing_auxiliary_training_cells"] for f in fits)
            rows.append({"origin":origin["origin"],"aux":aux,"used_fit_masks":len(fits),"primary_fit_masks":sum(f["fit_role"]=="primary" for f in fits),"training_feature_cells":cells,"imputed_training_cells":missing,"imputed_training_fraction":missing/cells if cells else None,"auxiliary_feature_cells":aux_cells,"imputed_auxiliary_cells":aux_missing,"imputed_auxiliary_fraction":aux_missing/aux_cells if aux_cells else None,"missing_query_cells":sum(f["missing_query_cells"] for f in fits),"entirely_missing_columns":sum(f["entirely_missing_columns"] for f in fits),"unsupported_configurations":sum(bool(r.get("fallback")) for r in candidates)})
    return {"schema_version":2,"created_at":now(),"source_audit_sha":report["code_sha"],"source_run_id":"43669085854","source_url":"https://github.com/howdymary/compute-forecasting/actions/runs/43669085854","dataset_sha256":PACK_SHA256,"origins":len(report["origins"]),"rows":rows,"mask_count_semantics":"Counts include each representation, window, horizon and prequential fit; masks are shared between alpha1/100. These are computational diagnostics, not independent samples.","numerical_scores_changed":False}
@app.function(image=image,cpu=.25,memory=512,timeout=90,volumes={"/public":public})
def publish(result):
    public.reload();write(Path("/public/experimental-v2/feature-summary.json"),result);public.commit();return {"sha256":digest(result)}
@app.local_entrypoint()
def main(inputs:str="inputs"):
    matches=[p for p in Path(inputs).rglob("results.json") if json.loads(p.read_text()).get("code_sha")=="fc29e92ac7d448a913ea8884a570d0a70ea5f78b"]
    if len(matches)!=1:raise ValueError("Exactly one verified feature audit required")
    result=summarize(json.loads(matches[0].read_text()));write(Path("artifacts/v2-feature-summary/summary.json"),result);receipt=publish.remote(result)
    print("V2_FEATURE_SUMMARY:"+json.dumps({"origins":result["origins"],"rows":result["rows"],"receipt":receipt}),flush=True)
