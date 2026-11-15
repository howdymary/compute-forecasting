"""One fixed Chronos-2 control, separate from frozen numerical/policy selection."""
from __future__ import annotations
import csv,hashlib,json,math,os,shutil,time,uuid
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import modal
from .campaign_v2 import unpack,build_history,invoke,protocol
from .policy_v2 import make_tasks
from .starter_probe import image as base_image,volume,PACK_SHA256
app=modal.App("compute-forecast-chronos2-control-v3")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=(base_image.pip_install("torch==2.8.0",index_url="https://download.pytorch.org/whl/cpu")
       .pip_install("chronos-forecasting==2.3.2","transformers==4.57.1","huggingface-hub==0.36.0"))
def canonical(value):return json.dumps(value,sort_keys=True,allow_nan=False).encode()
def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+".pending")
    tmp.write_bytes(canonical(value));tmp.replace(path)
def metrics(cases):
    if not cases:raise ValueError("No scored cells")
    n=len(cases);loss=sum(c["loss"] for c in cases)/n;base=sum(c["baseline_loss"] for c in cases)/n
    return {"pinball":loss,"baseline_pinball":base,"skill":1-loss/base if base>1e-12 else None,"coverage":sum(c["covered"] for c in cases)/n,"mean_width":sum(c["width"] for c in cases)/n,"n_cells":n}
def validate_config(c):
    if c["model_revision"]!="29ec3766d36d6f73f0696f85560a422f50e8498c" or c["library_version"]!="2.3.2":raise ValueError("Unregistered model")
    if c["evaluation_origins"]!=protocol()["evaluation_origins"] or c["horizons"]!=[1,3,7] or c["quantiles"]!=[.1,.5,.9]:raise ValueError("Unregistered evaluation")
    if c["cross_learning"] or c["fine_tuning"] or c["covariates"] or c["official_export_changed"] or c["frozen_selector_registry_changed"]:raise ValueError("Frozen comparison violated")
@app.function(image=image,cpu=4,memory=8192,timeout=1800,max_containers=1,volumes={"/data":volume,"/public":public})
def evaluate(grid,config,source_sha,run_id):
    import importlib.metadata
    import numpy as np
    import pandas as pd
    import torch
    from chronos import Chronos2Pipeline
    from huggingface_hub import snapshot_download
    validate_config(config);started=time.perf_counter();torch.manual_seed(0);torch.set_num_threads(4)
    tasks,_=make_tasks(grid);tasks=[t for t in tasks if t["phase"]=="evaluation"]
    if len(tasks)!=4:raise ValueError("Selector task scope changed")
    expected={(t["origin"],c["series_id"],c["horizon_days"]) for t in tasks for c in t["future_evaluator_only"]["last_value"]["cases"]}
    if len(expected)!=12:raise ValueError("Selector scored-cell scope changed")
    registered_hash=hashlib.sha256(canonical(config)).hexdigest()
    run_root=Path("/data/phase3-chronos")/run_id;run_root.mkdir(parents=True)
    atomic(run_root/"registration.json",{"config":config,"config_sha256":registered_hash,"source_sha":source_sha,"created_at":datetime.now(timezone.utc).isoformat(),"results_observed":False})
    volume.commit()
    local=snapshot_download(config["model_id"],revision=config["model_revision"],cache_dir="/data/phase3-model-cache",allow_patterns=["*.json","*.safetensors"])
    weight=Path(local)/"model.safetensors"
    with weight.open("rb") as stream:weight_sha=hashlib.file_digest(stream,"sha256").hexdigest()
    pipeline=Chronos2Pipeline.from_pretrained(local,device_map="cpu",dtype=torch.float32)
    model_loaded=time.perf_counter();temp,root=unpack();cases=[];contexts=[]
    def predict(hist,sid,origin,length):
        rr=hist[hist["series_id"]==sid].sort_values("day")
        if rr.empty or rr["day"].max()>date.fromisoformat(origin) or rr["day"].duplicated().any():raise ValueError("Invalid origin-bounded context")
        idx=pd.date_range(rr["day"].min(),origin,freq="D")
        series=pd.Series(rr["value"].to_numpy(dtype=np.float32),index=pd.to_datetime(rr["day"])).reindex(idx)
        if not np.isfinite(series.to_numpy()).any():raise ValueError("No finite context")
        inputs=torch.tensor(series.to_numpy(dtype=np.float32))
        with torch.inference_mode():
            quantiles,_=pipeline.predict_quantiles(inputs=[inputs],prediction_length=length,quantile_levels=[.1,.5,.9],cross_learning=False)
        arr=quantiles[0].detach().cpu().numpy()
        if arr.shape!=(1,length,3):raise ValueError("Unexpected model output shape: "+str(arr.shape))
        arr=arr[0]
        if not np.isfinite(arr).all() or not (np.diff(arr,axis=1)>=0).all():raise ValueError("Native model quantiles are invalid; no repair/fallback is permitted")
        contexts.append({"series_id":sid,"origin":origin,"first_date":idx.min().date().isoformat(),"last_calendar_date":idx.max().date().isoformat(),"observed_values":int(series.notna().sum()),"missing_calendar_days":int(series.isna().sum()),"calendar_length":len(series),"model_context_limit":pipeline.model_context_length})
        return arr
    for origin in config["evaluation_origins"]:
        current=[t for t in tasks if t["origin"]==origin];sids=sorted({s for t in current for s in t["series_ids"]})
        work=temp/origin;work.mkdir();hist,cat=build_history(root,work,origin)
        selected=cat[cat["series_id"].isin(sids)].copy();selected.to_csv(work/"primary.csv",index=False)
        rows=[]
        for sid in sids:
            pred=predict(hist,sid,origin,7)
            for h in [1,3,7]:
                qs=pred[h-1].tolist();rows.append({"series_id":sid,"origin_date":origin,"horizon_days":h,"q10":qs[0],"q50":qs[1],"q90":qs[2]})
        forecast=work/"chronos.csv"
        with forecast.open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=["series_id","origin_date","horizon_days","q10","q50","q90"]);writer.writeheader();writer.writerows(rows)
        end=(date.fromisoformat(origin)+timedelta(days=7)).isoformat()
        if end>"2026-11-06":raise ValueError("Protected post-cutoff truth must never be loaded")
        invoke(root,work,"truth",["build_series.py","--pack",str(root),"--cutoff",end,"--members-from",str(work/"catalog.csv"),"--out",str(work/"truth.csv"),"--catalog",str(work/"truth-cat.csv"),"--report",str(work/"truth-report.json")])
        invoke(root,work,"score",["scorer.py","--forecast",str(forecast),"--truth",str(work/"truth.csv"),"--history",str(work/"history.csv"),"--frozen-cutoff",origin,"--catalog",str(work/"primary.csv"),"--tier","headline","--out",str(work/"score.json"),"--per-cell",str(work/"cells.csv")])
        official=json.loads((work/"score.json").read_text())
        if official["forecast_validation"]["n_problems"] or official["cells"]["missing_forecast"]:raise ValueError("Official scorer rejected the control")
        with (work/"cells.csv").open() as f:
            for row in csv.DictReader(f):
                try:loss=float(row["loss"]);base=float(row["baseline_loss"]);y=float(row["y"]);lo=float(row["q10"]);hi=float(row["q90"])
                except (ValueError,TypeError):continue
                if math.isfinite(loss) and math.isfinite(base):cases.append({"origin":origin,"series_id":row["series_id"],"horizon_days":int(row["horizon_days"]),"loss":loss,"baseline_loss":base,"covered":lo<=y<=hi,"width":hi-lo})
        shutil.copytree(work,run_root/origin,dirs_exist_ok=True)
    actual={(c["origin"],c["series_id"],c["horizon_days"]) for c in cases}
    if actual!=expected or len(cases)!=12:raise ValueError("Comparator is not on the identical selector cohort")
    by_horizon={str(h):metrics([c for c in cases if c["horizon_days"]==h]) for h in [1,3,7]}
    by_series={sid:metrics([c for c in cases if c["series_id"]==sid]) for sid in sorted({c["series_id"] for c in cases})}
    prospective={"status":"not_issued","reason":"Eligibility/time/old commitment must be verified"}
    if config["prospective"]["enabled"]:
        issued=datetime.now(timezone.utc);origin=date.fromisoformat(config["prospective"]["origin_utc"])
        if issued.date()==origin and all(date.fromisoformat(d)>issued.date() for d in config["prospective"]["target_dates"]):
            public.reload();old_manifest=json.loads(Path("/public/experimental-v2/prospective-manifest.json").read_text())
            if old_manifest["forecast_sha256"]!=config["prospective"]["matched_baseline_commitment"]:raise ValueError("Original prospective commitment changed")
            old_path=Path("/data/campaign-v2/prospective")/(old_manifest["run_id"]+".json")
            old=json.loads(old_path.read_text())
            if hashlib.sha256(canonical(old)).hexdigest()!=old_manifest["forecast_sha256"]:raise ValueError("Original private prospective record hash mismatch")
            ids=sorted({r["series_id"] for r in old["rows"]})
            if len(ids)!=14 or old["forecast_origin"]!=origin.isoformat():raise ValueError("Prospective matched scope changed")
            work=temp/"prospective";work.mkdir();hist,cat=build_history(root,work,"2026-11-06");rows=[]
            last=date(2026,11,6);max_lead=(date.fromisoformat(config["prospective"]["target_dates"][-1])-last).days
            for sid in ids:
                pred=predict(hist,sid,last.isoformat(),max_lead)
                for h,target in zip([1,3,7],config["prospective"]["target_dates"]):
                    lead=(date.fromisoformat(target)-last).days;qs=pred[lead-1].tolist()
                    rows.append({"series_id":sid,"origin_date":origin.isoformat(),"target_date":target,"horizon_days":h,"q10":qs[0],"q50":qs[1],"q90":qs[2]})
            record={"schema_version":1,"method":"fixed_chronos2_control_v3","issued_at":issued.isoformat(),"origin_utc":origin.isoformat(),"data_cutoff":"2026-11-06","model_revision":config["model_revision"],"registration_sha256":registered_hash,"rows":rows}
            atomic(run_root/"prospective-private.json",record)
            prospective={"status":"pending_outcomes","issued_at":issued.isoformat(),"origin_utc":origin.isoformat(),"data_cutoff":"2026-11-06","target_dates":config["prospective"]["target_dates"],"series_ids":ids,"forecast_count":len(rows),"forecast_sha256":hashlib.sha256(canonical(record)).hexdigest(),"hash_basis":"SHA256 of UTF-8 json.dumps(private_record, sort_keys=True, allow_nan=False), default separators and ensure_ascii=True","matched_baseline_commitment":old_manifest["forecast_sha256"],"not_before_score_utc":config["prospective"]["not_before_score_utc"],"private_forecasts_retained":True,"outcomes_loaded":False,"market_freshness":config["prospective"]["market_freshness"]}
    report={"schema_version":1,"status":"completed","kind":"additional_retrospective_control_not_a_selector_arm","run_id":run_id,"created_at":datetime.now(timezone.utc).isoformat(),"source_sha":source_sha,"config_sha256":registered_hash,"config":config,"model_weights_sha256":weight_sha,"scope":{"cells":12,"tasks":4,"temporal_origins":config["evaluation_origins"],"series_ids":sorted(by_series),"retrospective":True,"protected_final_period_used":False},"metrics":metrics(cases),"by_horizon":by_horizon,"by_series":by_series,"by_origin":{o:metrics([c for c in cases if c["origin"]==o]) for o in config["evaluation_origins"]},"scored_cell_keys":[list(k) for k in sorted(actual)],"context_audit":contexts,"prospective":prospective,"runtime_seconds":time.perf_counter()-started,"model_download_and_load_seconds":model_loaded-started,"device":"cpu","modal_call_id":modal.current_function_call_id(),"provider_cost_usd":None,"cost_status":"No attributable receipt in this execution; unknown is not zero","packages":{n:importlib.metadata.version(n) for n in ["chronos-forecasting","torch","transformers","numpy","pandas","huggingface-hub"]},"future_competition_truth_loaded":False,"official_export_changed":False,"selector_registry_changed":False}
    atomic(run_root/"report.json",report);volume.commit()
    public.reload();atomic(Path("/public/phase3/chronos-control.json"),report);public.commit();shutil.rmtree(temp);return report
@app.local_entrypoint()
def main(inputs:str="inputs"):
    config=json.loads(Path("configs/chronos-control-v3.json").read_text());validate_config(config)
    files=list(Path(inputs).rglob("grid.json"));grids=[json.loads(p.read_text()) for p in files]
    grids=[g for g in grids if g.get("code_sha")==config["grid_source_sha"]]
    if not grids or len({hashlib.sha256(canonical(g)).hexdigest() for g in grids})!=1:raise ValueError("Ambiguous immutable numerical grid")
    run=uuid.uuid4().hex;result=evaluate.remote(grids[0],config,os.environ["GITHUB_SHA"],run)
    out=Path("artifacts");out.mkdir(exist_ok=True)
    (out/"chronos-control-v3.json").write_text(json.dumps(result,indent=2)+"\n")
    print("CHRONOS_CONTROL_V3:"+json.dumps(result),flush=True)
