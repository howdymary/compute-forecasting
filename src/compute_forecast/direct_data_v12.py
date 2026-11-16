"""Prepare direct forecasting data remotely; no numerical experiment is rerun."""
from __future__ import annotations
import csv,hashlib,json,math,os,tempfile,time
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
import modal
from .starter_probe import PACK_NAME,PACK_SHA256,verify_manifest
from .pacific_value_v5 import build_history,invoke,rows
app=modal.App("compute-forecast-direct-v12-data")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=(modal.Image.debian_slim(python_version="3.11").pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","pyarrow>=16,<24").env({"GITHUB_SHA":os.environ.get("GITHUB_SHA","unknown")}).add_local_file("configs/direct-forecast-v12.json","/root/configs/direct-forecast-v12.json",copy=True).add_local_python_source("compute_forecast"))
def config():return json.loads(Path("configs/direct-forecast-v12.json").read_text())
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,allow_nan=False,separators=(",",":")).encode()).hexdigest()
def put(p,v):
    raw=(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode();p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists() and p.read_bytes()!=raw:raise ValueError("Immutable output conflict")
    if not p.exists():p.write_bytes(raw)
def task(values,meta,origin,p):
    day=date.fromisoformat(origin);start=(day-timedelta(days=p["data"]["context_calendar_days"]-1)).isoformat()
    context=[{"date":d,"value":v} for d,v in sorted(values.items()) if start<=d<=origin]
    if origin not in values or len(context)<p["data"]["min_context_observations"]:return None
    targets=[(day+timedelta(days=h)).isoformat() for h in p["data"]["horizons"]]
    if any(d not in values for d in targets):return None
    anchor=values[origin]
    return {"task_id":digest([meta["series_id"],origin])[:24],"series_id":meta["series_id"],"metadata":meta,"origin":origin,"anchor":anchor,"context":context,"context_missing_days":p["data"]["context_calendar_days"]-len(context),"target_dates":targets,"outcomes":[values[d] for d in targets],"returns":[math.log(values[d]/anchor) for d in targets],"evidence":[]}
@app.function(image=image,cpu=4,memory=8192,timeout=1200,max_containers=1,volumes={"/data":data})
def prepare():
    started=time.perf_counter();p=config();base=Path(os.environ.get("DIRECT_V12_DATA_ROOT","/data"));root=base/"pacific"/PACK_NAME
    count=verify_manifest(root);assert count==672
    out=base/"direct-forecast-v12"/digest(p);out.mkdir(parents=True,exist_ok=True)
    if (out/"audit.json").exists():return json.loads((out/"audit.json").read_text())
    work=Path(tempfile.mkdtemp(prefix="direct-v12-"))
    hist,catalog,history_path,catalog_path=build_history(root,work,p["data"]["history_cutoff"])
    approved=[m for m in catalog if m.get("tier")=="headline" and m.get("table")=="daily_statistics" and m.get("source_id") in p["data"]["source_ids"] and m.get("gpu_model","").upper().startswith(tuple(p["data"]["gpu_prefixes"]))]
    selected=[];counts={}
    for m in sorted(approved,key=lambda m:m["series_id"]):
        key=(m["source_id"],m["gpu_model"].split()[0].upper())
        if counts.get(key,0)<p["data"]["max_per_source_family"] and len(selected)<p["data"]["max_series"]:
            selected.append(m);counts[key]=counts.get(key,0)+1
    approved=selected
    panels={m["series_id"]:{} for m in approved}
    for r in hist:
        if r["series_id"] in panels:
            v=float(r["value"])
            if not math.isfinite(v) or v<=0:raise ValueError("Non-positive target")
            if r["date"]>p["data"]["history_cutoff"]:raise ValueError("Future contamination")
            if r["date"] in panels[r["series_id"]]:raise ValueError("Duplicate target date")
            panels[r["series_id"]][r["date"]]=v
    groups={"training":[],"development":[],"retrospective":[]};coverage=[]
    for meta in approved:
        values=panels[meta["series_id"]];candidates=[]
        for origin in sorted(values):
            if origin>p["data"]["train_origins_through"]:continue
            t=task(values,meta,origin,p)
            if t and max(t["target_dates"])<=p["data"]["train_labels_through"]:candidates.append(t)
        n=p["data"]["max_training_windows_per_series"]
        if len(candidates)>n:
            indices=sorted({round(i*(len(candidates)-1)/(n-1)) for i in range(n)})
            candidates=[candidates[i] for i in indices]
        groups["training"].extend(candidates)
        for phase,key in [("development","development_origins"),("retrospective","retrospective_origins")]:
            for origin in p["data"][key]:
                t=task(values,meta,origin,p)
                if t:groups[phase].append(t)
        vals=[v for _,v in sorted(values.items())]
        coverage.append({"series_id":meta["series_id"],"metadata":meta,"observations":len(values),"first_date":min(values) if values else None,"last_date":max(values) if values else None,"training_windows":len(candidates),"price_steps":sum(a!=b for a,b in zip(vals,vals[1:])),"history_sha256":digest(values)})
    if any(max(t["target_dates"])>p["data"]["train_labels_through"] for t in groups["training"]):raise ValueError("Immature labels")
    distinct=len({t["origin"] for t in groups["training"]})
    gate=len(groups["training"])>=p["gates"]["min_training_windows"] and distinct>=p["gates"]["min_distinct_training_origins"] and len(groups["development"])>=p["gates"]["min_development_tasks"] and len(groups["retrospective"])>=p["gates"]["min_retrospective_tasks"]
    baselines=[]
    for origin in sorted(set(p["data"]["development_origins"]+p["data"]["retrospective_origins"])):
        dest=work/origin;dest.mkdir();_,_,hp,cp=build_history(root,dest,origin)
        for method in p["evaluation"]["references"]:
            output=dest/(method+".csv")
            invoke(root,dest,method,["baselines.py","--history",hp,"--catalog",cp,"--tier","headline","--origin",origin,"--method",method,"--frozen","--out",output])
            for r in rows(output):
                if r["series_id"] in panels and int(r["horizon_days"]) in p["data"]["horizons"]:baselines.append({**r,"method":method})
    payload={"protocol_sha256":digest(p),"groups":groups,"baselines":baselines,"coverage":coverage,"historical_availability":"Frozen pack date labels; not proof of original real-time availability","protected_outcomes_loaded":False}
    put(out/"dataset.json",payload)
    audit={"study_id":p["study_id"],"protocol_sha256":digest(p),"source_sha":os.environ.get("GITHUB_SHA"),"created_at":datetime.now(timezone.utc).isoformat(),"manifest_entries":count,"pack_sha256":PACK_SHA256,"dataset_sha256":digest(payload),"history_sha256":hashlib.sha256(history_path.read_bytes()).hexdigest(),"catalog_sha256":hashlib.sha256(catalog_path.read_bytes()).hexdigest(),"series":coverage,"phase_tasks":{k:len(v) for k,v in groups.items()},"distinct_training_origins":distinct,"phase_origins":{k:sorted({t["origin"] for t in v}) for k,v in groups.items()},"phase_cells":{k:len(v)*3 for k,v in groups.items()},"changed_training_vectors":sum(any(abs(x)>1e-10 for x in t["returns"]) for t in groups["training"]),"price_only_ready":gate,"evidence_ready":False,"evidence_gate_reason":"No origin-safe varying supplementary feature table registered yet; current-news retrieval cannot enter historical examples","prospective_accuracy":"pending","runtime_seconds":time.perf_counter()-started,"provider_cost_usd":None,"modal_call_id":modal.current_function_call_id() if not os.environ.get("DIRECT_V12_DATA_ROOT") else None,"protected_outcomes_loaded":False,"permission":"Approved source-derived history under Pacific CC BY 4.0; source attribution retained","private_dataset_exposed":False}
    put(out/"audit.json",audit)
    if not os.environ.get("DIRECT_V12_DATA_ROOT"):data.commit()
    return audit
@app.local_entrypoint()
def main(hosted:bool=False):
    report=prepare.local() if hosted else prepare.remote();dest=Path("artifacts/direct-v12");dest.mkdir(parents=True,exist_ok=True)
    if hosted:
        source=Path(os.environ["DIRECT_V12_DATA_ROOT"])/"direct-forecast-v12"/report["protocol_sha256"]/"dataset.json"
        (dest/"dataset.json").write_bytes(source.read_bytes())
        (dest/"ATTRIBUTION.txt").write_text("Pacific Machines (2026), gpu-price-pack v0.1.1-handover. CC BY 4.0 compilation. Approved source-derived target windows only; no raw offers or restricted marketplace sources. Component source_id and exact contract metadata are retained in each task. Source permissions: docs/DATA_SOURCES.md.\n")
    (dest/"audit.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2,allow_nan=False))
