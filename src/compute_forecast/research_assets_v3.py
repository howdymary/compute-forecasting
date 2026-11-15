"""Publish independently licensed context and a bounded pair of real saved traces."""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path
from datetime import datetime,timezone
import modal
from .history_contract_v3 import APPROVED,HISTORY_RUN,LICENSE_SHA,digest,validate_assets
app=modal.App("compute-forecast-research-assets-v3")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
def compact(trace):
    return {**{k:trace[k] for k in ("task_id","origin","group","selected_config_id","revealed","pinball","n_cells")},
      "steps":[{"step":s["step"],"selected_config_id":s["selected_config_id"],"validation_pinball":s["revealed_validation_result"]["loss"]} for s in trace["steps"]]}
def pairs_from_inputs(root):
    found=[]
    for p in Path(root).rglob("policy-report.json"):
        v=json.loads(p.read_text())
        if v.get("run_id")=="c24ee0b5943f48c2bfa17032598f42f4":found.append((p,v))
    if len(found)!=1:raise ValueError("Expected the operational development-selected soft17 SFT artifact")
    report_path,report=found[0]
    if report["selected_update"]!=100:raise ValueError("Frozen selection changed")
    files={key:report_path.parent/name for key,name in (("feedback","trained-evaluation.json"),("hidden","no-observation.json"))}
    reports={k:json.loads(p.read_text()) for k,p in files.items()}
    if len(reports["feedback"]["traces"])!=4 or {t["task_id"] for t in reports["feedback"]["traces"]}!={t["task_id"] for t in reports["hidden"]["traces"]}:raise ValueError("Unmatched traces")
    hidden={t["task_id"]:t for t in reports["hidden"]["traces"]}
    pairs=[{"task_id":t["task_id"],"origin":t["origin"],"group":t["group"],"feedback":compact(t),"hidden":compact(hidden[t["task_id"]])} for t in reports["feedback"]["traces"]]
    return {"run_id":report["run_id"],"selected_update":100,"mode":"sft","objective":"soft","seed":17,"selection":"Operational SFT run selected on development, not evaluation","source_workflow_run":43665821333,"artifact_sha256":{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()},"pairs":pairs}
@app.function(image=image,cpu=.25,memory=512,timeout=120,volumes={"/data":data,"/public":public})
def publish(traces,source_sha,workflow_run):
    file=Path("/data/phase3-history/upstream")/HISTORY_RUN/"candidate-private.json"
    candidate=json.loads(file.read_text());audit=candidate["summary"]
    if audit["run_id"]!=HISTORY_RUN or audit["source"]["license_sha256"]!=LICENSE_SHA or audit["post_cutoff_price_objects_downloaded"]!=0:raise ValueError("Unverified source")
    series=[]
    for sid,label in APPROVED.items():
        a=next(x for x in audit["candidates"] if x["series_id"]==sid)
        points=candidate["curves"][sid]
        if not a["hardware_mapping_verified"] or digest(points)!=a["points_sha256"]:raise ValueError("Unverified hardware or altered points")
        series.append({"id":"hubbard-independent-"+("a100-40" if "A100" in sid else "t4"),"label":label+" · hyperscaler spot · independent context","gpu_model":label,"benchmark_series_context":sid,"unit":"USD per GPU-hour","market":"hyperscaler spot advertised offers","statistic":"daily median across quality-ok AWS/Azure/GCP observations","region":"mixed listed regions; changing composition, not a fixed basket","providers":["aws","azure","gcp"],"frequency":"UTC daily; observed dates only","benchmark_overlay_allowed":False,"benchmark_max_absolute_difference":a["max_absolute_difference"],"benchmark_overlap_days":a["overlap_days"],"observations":len(points),"missing_calendar_days":a["missing_calendar_days"],"points_sha256":a["points_sha256"],"points":points})
    history={"kind":"independent_historical_context","benchmark_overlay_allowed":False,"benchmark_input_claim":False,"cutoff":"2026-11-06","source":audit["source"],"audit_run_id":HISTORY_RUN,"source_workflow_run":audit["workflow_run_id"],"series":series,
      "explanation":"Independent CC BY4 upstream history is shown separately. Strict predeclared overlap checks did not establish exact numerical identity with the competition series; no continuous history-to-forecast line or automatic dollar anchor is supplied.",
      "permission_decisions":[
       {"source":"Hubbard independently retrieved archive","decision":"publish derived standalone A100 40GB and T4 context only","governing_url":audit["source"]["license_evidence_url"],"checked_at":audit["source"]["retrieved_at"],"basis":"Explicit data license covers the S3 archive and mirrors; CC BY4 attribution, license link and changes retained."},
       {"source":"Private competition compilation (all 37 headline series)","decision":"historical values remain unpublished","governing_url":"https://iterate.inc/ai-research?welcome=true","checked_at":audit["source"]["retrieved_at"],"basis":"Source catalog labels do not resolve the compilation redistribution permission. No private-pack values were published."},
       {"source":"GPU Rental Prices upstream history CSV","decision":"not plotted as benchmark history","governing_url":"https://gpurentalprices.com/data","checked_at":audit["source"]["retrieved_at"],"basis":"Explicit CC BY4 data page, but cheapest-per-day history is not the median competition target."},
       {"source":"FastGPU historical compilation","decision":"historical values remain unpublished","governing_url":"https://huggingface.co/datasets/fastgpu/cloud-gpu-prices","checked_at":audit["source"]["retrieved_at"],"basis":"No verified independently licensed matching historical archive was retrieved; private compilation permission unresolved."}]}
    payload=validate_assets({"schema_version":3,"published_at":datetime.now(timezone.utc).isoformat(),"code_sha":source_sha,"workflow_run_id":workflow_run,"history_context":history,"paired_traces":traces})
    raw=json.dumps(payload,indent=2,allow_nan=False).encode();root=Path("/public/phase3");root.mkdir(exist_ok=True)
    pending=root/"explorer.pending";pending.write_bytes(raw);pending.replace(root/"explorer.json");public.commit()
    return {"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"history_series":len(series),"observations":sum(len(s["points"]) for s in series),"private_pack_values_published":False,"code_sha":source_sha}
@app.local_entrypoint()
def main(inputs:str="inputs"):
    result=publish.remote(pairs_from_inputs(inputs),os.environ["GITHUB_SHA"],os.environ["GITHUB_RUN_ID"])
    root=Path("artifacts");root.mkdir(exist_ok=True);(root/"research-assets-publication.json").write_text(json.dumps(result,indent=2))
    print("RESEARCH_ASSETS_PUBLICATION:"+json.dumps(result),flush=True)
