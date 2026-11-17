"""Build a new source-bound distribution dataset from the immutable pack on Modal."""
from __future__ import annotations
import collections,hashlib,json,math,os,pathlib,statistics,tempfile,time
from datetime import datetime,timezone
import modal
from .starter_probe import PACK_NAME,PACK_SHA256,verify_manifest
from .pacific_value_v5 import build_history,invoke,rows
from .direct_data_v12 import task
from .probability_v18 import digest,levels,support,bin_index
app=modal.App("compute-forecast-probability-v18-data")
volume=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=(modal.Image.debian_slim(python_version="3.11").pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","pyarrow>=16,<24").env({"GITHUB_SHA":os.environ.get("GITHUB_SHA","unknown")}).add_local_file("configs/direct-probability-v18.json","/root/configs/direct-probability-v18.json",copy=True).add_local_python_source("compute_forecast"))
@app.function(image=image,cpu=4,memory=8192,timeout=1800,max_containers=1,volumes={"/data":volume})
def prepare():
    begin=time.monotonic();volume.reload()
    p=json.loads(pathlib.Path("/root/configs/direct-probability-v18.json").read_text())
    root=pathlib.Path("/data/pacific")/PACK_NAME;count=verify_manifest(root);assert count==672
    work=pathlib.Path(tempfile.mkdtemp(prefix="probability-v18-"))
    hist,catalog,hp,cp=build_history(root,work,p["data"]["history_cutoff"])
    approved=[m for m in catalog if m.get("tier")==p["data"]["tier"] and m.get("table")==p["data"]["table"] and m.get("source_id") in p["data"]["source_ids"] and m.get("instrument_class") in p["data"]["instrument_classes"] and m.get("licence_id")==p["data"]["licence_id"] and m.get("gpu_model","").upper().startswith(tuple(p["data"]["gpu_prefixes"]))]
    approved.sort(key=lambda m:m["series_id"]);panels={m["series_id"]:{} for m in approved}
    for row in hist:
        if row["series_id"] not in panels:continue
        value=float(row["value"]);assert math.isfinite(value) and value>0 and row["date"]<=p["data"]["history_cutoff"]
        assert row["date"] not in panels[row["series_id"]],"Duplicate observation"
        panels[row["series_id"]][row["date"]]=value
    groups={name:[] for name in ("training","development","retrospective")};coverage=[]
    for meta in approved:
        values=panels[meta["series_id"]];candidates=[]
        for origin in sorted(values):
            if origin>p["data"]["train_origins_through"]:continue
            t=task(values,meta,origin,p)
            if t and max(t["target_dates"])<=p["data"]["train_labels_through"]:candidates.append(t)
        cap=p["data"]["max_training_windows_per_series"]
        if len(candidates)>cap:candidates=[candidates[i] for i in sorted({round(i*(len(candidates)-1)/(cap-1)) for i in range(cap)})]
        groups["training"].extend(candidates)
        for phase in ("development","retrospective"):
            for origin in p["data"][phase+"_origins"]:
                t=task(values,meta,origin,p)
                if t:groups[phase].append(t)
        coverage.append({"series_id":meta["series_id"],"metadata":meta,"observations":len(values),"first_date":min(values) if values else None,"last_date":max(values) if values else None,"training_windows":len(candidates),"price_steps":sum(a!=b for a,b in zip(values.values(),list(values.values())[1:])),"history_sha256":digest(values)})
    train=groups["training"];assert train and all(max(t["target_dates"])<=p["data"]["train_labels_through"] for t in train)
    log_levels=levels(train,p);scale=statistics.median(t["anchor"] for t in train)
    diagnostics={}
    for phase,tasks in groups.items():
        nearest=[];persistent=[];outside=0;total=0;zero={str(h):0 for h in p["data"]["horizons"]}
        for t in tasks:
            assert all(r["date"]<=t["origin"] for r in t["context"])
            assert max(t["target_dates"])<="2026-11-06"
            z=support(t["anchor"],log_levels)
            for h,y in zip(p["data"]["horizons"],t["outcomes"]):
                outside+=int(y<z[0] or y>z[-1]);total+=1
                if h==7:nearest.append(abs(z[bin_index(z,y)]-y));persistent.append(abs(t["anchor"]-y))
                zero[str(h)]+=int(y==t["anchor"])
        diagnostics[phase]={"windows":len(tasks),"horizon_examples":total,"series":len({t["series_id"] for t in tasks}),"origins":sorted({t["origin"] for t in tasks}),"source_windows":dict(collections.Counter(t["metadata"]["source_id"] for t in tasks)),"gpu_windows":dict(collections.Counter(t["metadata"]["gpu_model"] for t in tasks)),"instrument_windows":dict(collections.Counter(t["metadata"]["instrument_class"] for t in tasks)),"zero_labels_by_horizon":zero,"out_of_support":outside,"in_support_fraction":1-outside/total if total else None,"median_seven_day_quantization_ae":statistics.median(nearest) if nearest else None,"median_seven_day_persistence_ae":statistics.median(persistent) if persistent else None}
    dev=diagnostics["development"]
    reasons=[]
    if diagnostics["training"]["series"]<=6:reasons.append("training_not_broader_than_v14")
    if diagnostics["training"]["source_windows"].get("fastgpu_daily",0)==0:reasons.append("no_FastGPU_training")
    if len(train)<64 or len(groups["development"])<10 or len(groups["retrospective"])<10:reasons.append("insufficient_tasks")
    if dev["in_support_fraction"] is None or dev["in_support_fraction"]<.95:reasons.append("development_support_inadequate")
    if dev["median_seven_day_quantization_ae"] is None or dev["median_seven_day_quantization_ae"]>dev["median_seven_day_persistence_ae"]+1e-12:reasons.append("quantization_worse_than_persistence_median")
    references=[];native_sha=hashlib.sha256((root/"starter/baselines.py").read_bytes()).hexdigest()
    for origin in sorted(set(p["data"]["development_origins"]+p["data"]["retrospective_origins"])):
        dest=work/origin;dest.mkdir();history,_,history_file,_=build_history(root,dest,origin)
        ids=dest/"series.txt";ids.write_text("\n".join(panels)+"\n")
        for method in p["evaluation"]["references"]:
            out=dest/(method+".csv")
            invoke(root,dest,method,["baselines.py","--history",history_file,"--origin",origin,"--series-ids","@"+str(ids),"--method",method,"--frozen","--out",out])
            emitted={(r["series_id"],int(r["horizon_days"])):r for r in rows(out)}
            for t in groups["development"]+groups["retrospective"]:
                if t["origin"]!=origin:continue
                for h in p["data"]["horizons"]:
                    row=emitted.get((t["series_id"],h));fallback=row is None
                    q=[t["anchor"]]*3 if fallback else [float(row[k]) for k in ("q10","q50","q90")]
                    references.append({"series_id":t["series_id"],"origin":origin,"horizon_days":h,"method":method,"q10":q[0],"q50":q[1],"q90":q[2],"fallback":fallback})
    payload={"study_id":p["study_id"],"protocol_sha256":digest(p),"groups":groups,"log_levels":log_levels,"crps_scale":scale,"references":references,"coverage":coverage,"protected_outcomes_loaded":False}
    overlap={}
    for phase,tasks in groups.items():
        shape=collections.Counter(digest([r["value"] for r in t["context"]]) for t in tasks)
        overlap[phase]={"distinct_value_histories":len(shape),"largest_repetition":max(shape.values()) if shape else 0}
    audit={"study_id":p["study_id"],"protocol_sha256":digest(p),"dataset_sha256":digest(payload),"source_sha":os.environ.get("GITHUB_SHA"),"created_at":datetime.now(timezone.utc).isoformat(),"manifest_entries":count,"pack_sha256":PACK_SHA256,"history_sha256":hashlib.sha256(hp.read_bytes()).hexdigest(),"catalog_sha256":hashlib.sha256(cp.read_bytes()).hexdigest(),"native_baseline_sha256":native_sha,"phases":diagnostics,"context_shapes":overlap,"coverage":coverage,"log_levels":log_levels,"crps_scale":scale,"training_ready":not reasons,"gate_reasons":reasons,"publication":"Pacific CC BY 4.0 approved exact-source daily-statistic targets; row identities and component attribution retained; raw offers excluded","collection_vintage":"Frozen Pacific pack v0.1.1; historical date labels do not establish original real-time availability","cohort_selection":"Fixed November 6 headline catalog metadata, declared retrospective; not a reconstruction of the origin-time eligible universe","source_attribution":"Pacific Machines (2026), gpu-price-pack v0.1.1-handover. Approved source-specific component metadata retained.","new_optimizer_updates":0,"provider_cost_usd":None,"runtime_seconds":time.monotonic()-begin,"protected_outcomes_loaded":False,"prospective_accuracy":"not established"}
    return {"dataset":payload,"audit":audit}
@app.local_entrypoint()
def main():
    result=prepare.remote()
    private=pathlib.Path("inputs/probability-v18");private.mkdir(parents=True,exist_ok=True)
    public=pathlib.Path("artifacts/probability-v18-audit");public.mkdir(parents=True,exist_ok=True)
    (private/"dataset.json").write_text(json.dumps(result["dataset"],indent=2,allow_nan=False)+"\n")
    for dest in (private,public):(dest/"audit.json").write_text(json.dumps(result["audit"],indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:result["audit"][k] for k in ("study_id","training_ready","gate_reasons","phases","runtime_seconds")}),flush=True)
