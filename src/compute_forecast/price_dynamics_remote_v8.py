"""Registered v8 remote experiment. Immutable private inputs; versioned public summaries."""
from __future__ import annotations
import csv,hashlib,json,os,tempfile,time,uuid
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
import modal
from .starter_probe import PACK_NAME,PACK_SHA256,verify_manifest
from .pacific_value_v5 import build_history,invoke,rows,write_csv
from .price_dynamics_v8 import digest,pooled,replay,calibrate,loss,summarize,paired,ordered
app=modal.App("compute-forecast-price-dynamics-v8")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=(modal.Image.debian_slim(python_version="3.11").pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","pyarrow>=16,<24","httpx>=0.28,<1")
    .env({"GITHUB_SHA":os.environ.get("GITHUB_SHA","unknown")}).add_local_file("configs/price-dynamics-v8.json","/root/configs/price-dynamics-v8.json",copy=True).add_local_python_source("compute_forecast"))
def config():return json.loads(Path("configs/price-dynamics-v8.json").read_bytes())
def encoded(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def put(path,value):
    raw=encoded(value);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=raw:raise ValueError("Immutable artifact conflict")
    if not path.exists():path.write_bytes(raw)
def dates(a,b):
    d=date.fromisoformat(a)
    while d.isoformat()<=b:
        yield d.isoformat();d+=timedelta(days=1)
@app.function(image=image,cpu=4,memory=8192,timeout=900,max_containers=1,volumes={"/data":data})
def prepare(run_id):
    import duckdb,pandas as pd,statistics
    started=time.perf_counter();p=config();root=Path("/data/pacific")/PACK_NAME
    verify_manifest(root)
    engine_hash=hashlib.sha256(Path(__file__).with_name("price_dynamics_v8.py").read_bytes()).hexdigest()
    registry=Path("/data/price-dynamics-v8/registry")/digest({"protocol":p,"engine_sha256":engine_hash})
    if (registry/"completed.json").exists():raise ValueError("Exact configuration already completed; reuse its artifacts")
    registry.mkdir(parents=True,exist_ok=True)
    put(registry/(run_id+".json"),{"run_id":run_id,"configuration_sha256":digest(p),"engine_sha256":engine_hash})
    work=Path(tempfile.mkdtemp(prefix="price-dynamics-v8-"))
    hist,cat,_,_=build_history(root,work,p["history_cutoff"])
    by_id={r["series_id"]:r for r in cat}
    absent=set(p["series_ids"])-set(by_id)
    if absent:raise ValueError("Registered IDs not in official catalog: "+str(absent))
    panels={}
    for sid in p["series_ids"]:
        meta=dict(by_id[sid]);meta.update(family=meta["gpu_model"].split()[0],unit=p["unit"])
        if meta["source_id"] not in p["sources"] or meta["instrument_class"] not in p["instruments"]:raise ValueError("Cohort boundary")
        panels[sid]={"meta":meta,"values":{r["date"]:float(r["value"]) for r in hist if r["series_id"]==sid},"offers":{},"reconstruction":{}}
    # Eligibility depends only on available target observations, before candidate results.
    eligible=[{"series_id":sid,"origin":o,"horizon":h,"target":(date.fromisoformat(o)+timedelta(days=h)).isoformat()} for sid,x in panels.items() for o in p["origins"] for h in p["horizons"] if o in x["values"] and (date.fromisoformat(o)+timedelta(days=h)).isoformat() in x["values"]]
    excluded=[{"series_id":sid,"origin":o,"horizon":h,"reason":"missing_origin_or_target_observation"} for sid,x in panels.items() for o in p["origins"] for h in p["horizons"] if o not in x["values"] or (date.fromisoformat(o)+timedelta(days=h)).isoformat() not in x["values"]]
    sql=duckdb.connect();pattern=str(root/"rental_observations"/"*"/"*"/"*.parquet")
    raw=sql.execute("SELECT * FROM read_parquet(?,hive_partitioning=false) WHERE source_id='afhubbard' AND CAST(dt AS DATE)<=DATE '2026-11-06' AND usd_per_gpu_hour>0 AND (gpu_model LIKE 'H100%' OR gpu_model LIKE 'A100%')",[pattern]).df()
    raw["day"]=pd.to_datetime(raw["dt"]).dt.strftime("%Y-%m-%d")
    raw["captured"]=pd.to_datetime(raw["snapshot_ts_utc"],utc=True)
    if (raw["captured"].dt.strftime("%Y-%m-%d")!=raw["day"]).any():raise ValueError("Snapshot-day identity")
    identity=p["replay"]["identity"];audits=[]
    for sid,x in panels.items():
        meta=x["meta"];g=raw[(raw["gpu_model"]==meta["gpu_model"])&(raw["instrument_class"]==meta["instrument_class"])&(raw["pricing_tier"]==meta["pricing_tier"])].copy()
        missing=g[identity].isna().any(axis=1)|g[identity].astype("string").eq("").any(axis=1)
        g["_missing"]=missing
        g["_key"]=g[identity].astype("string").fillna("<missing>").apply(lambda r:digest(list(map(str,r))),axis=1)
        for day,part in g.groupby("day"):
            last=part.sort_values("captured").drop_duplicates("_key",keep="last")
            quotes={str(r["_key"]):float(r["usd_per_gpu_hour"]) for _,r in last.iterrows()}
            x["offers"][day]=quotes
            target=x["values"].get(day)
            all_median=round(float(part["usd_per_gpu_hour"].median()),4)
            basket_median=round(statistics.median(quotes.values()),4)
            ambiguous=int((part.groupby(["_key","captured"])["usd_per_gpu_hour"].nunique()>1).sum())
            x["reconstruction"][day]={"raw_matches":target is not None and abs(all_median-target)<=1e-10,"basket_matches":target is not None and abs(basket_median-target)<=1e-10,"absolute_basket_error":None if target is None else abs(basket_median-target),"missing_identity_rows":int(part["_missing"].sum()),"same_timestamp_identity_collisions":ambiguous,"rows":len(part),"identities":len(quotes)}
        checks=x["reconstruction"]
        audits.append({"series_id":sid,"official_target":meta["benchmark_contract"],"source_url":meta["source_url"],"licence_id":meta["licence_id"],"days":len(checks),"raw_target_exact_days":sum(r["raw_matches"] for r in checks.values()),"last_quote_basket_exact_days":sum(r["basket_matches"] for r in checks.values()),"missing_identity_rows":int(missing.sum()),"obs_id_collisions":int(g["obs_id"].duplicated().sum()),"same_timestamp_identity_collisions":sum(r["same_timestamp_identity_collisions"] for r in checks.values()),"max_basket_error":max((r["absolute_basket_error"] or 0 for r in checks.values()),default=None),"collection_completeness_attestations":0})
    selected=[r for r in hist if r["series_id"] in panels]
    reference={};methods=["drift","last_value","last_value_empirical"]
    for o in dates(p["calibration_forecast_start"],max(p["origins"])):
        d=work/o;d.mkdir()
        past=[r for r in selected if r["date"]<=o];path=d/"history.csv"
        write_csv(path,past,list(past[0]))
        reference[o]={}
        for method in methods if o in p["origins"] else ["drift"]:
            f=d/(method+".csv")
            invoke(root,d,method,["baselines.py","--history",path,"--origin",o,"--method",method,"--series-ids",",".join(p["series_ids"]),"--horizons","1,3,7","--frozen","--out",f])
            reference[o][method]={r["series_id"]+"|"+r["horizon_days"]:[float(r[k]) for k in ("q10","q50","q90")] for r in rows(f)}
    inputs={"protocol_sha256":digest(p),"panels":panels,"eligible":eligible,"excluded":excluded,"references":reference,"audit":audits,"prepared_at":datetime.now(timezone.utc).isoformat(),"starter_hashes":{name:hashlib.sha256((root/"starter"/name).read_bytes()).hexdigest() for name in ("baselines.py","build_series.py","scorer.py")},"pack_sha256":PACK_SHA256}
    path=Path("/data/price-dynamics-v8/runs")/run_id/"inputs.json"
    if len(encoded(inputs))>p["resources"]["private_storage_bytes"]:raise ValueError("Storage budget")
    put(path,inputs);data.commit()
    return {"run_id":run_id,"registry_key":registry.name,"engine_sha256":engine_hash,"input_sha256":digest(inputs),"protocol_sha256":digest(p),"eligible":len(eligible),"excluded":len(excluded),"audit":audits,"prepare_seconds":time.perf_counter()-started}
@app.function(image=image,cpu=4,memory=8192,timeout=1800,max_containers=3,volumes={"/data":data})
def evaluate_horizon(run_id,h):
    started=time.perf_counter();p=config();data.reload()
    inp=json.loads((Path("/data/price-dynamics-v8/runs")/run_id/"inputs.json").read_bytes())
    if inp["protocol_sha256"]!=digest(p):raise ValueError("Protocol changed")
    eligible={(r["series_id"],r["origin"],r["horizon"]):r for r in inp["eligible"] if r["horizon"]==h}
    cells=[];past={sid:{m:[] for m in ("A","C","E")} for sid in inp["panels"]};failed=[];scenarios=[]
    for origin in dates(p["calibration_forecast_start"],max(p["origins"])):
        available={sid:{"meta":x["meta"],"values":{d:v for d,v in x["values"].items() if d<=origin}} for sid,x in inp["panels"].items()}
        for sid,x in inp["panels"].items():
            key=sid+"|"+str(h);q=inp["references"].get(origin,{}).get("drift",{}).get(key)
            if q is None:continue
            base={"A":(ordered(q),{"fallback":None})}
            base["C"]=pooled(available[sid]["values"],x["meta"],available,origin,h,q)
            checks=[r for d,r in x["reconstruction"].items() if d<=origin]
            reason="target_reconstruction_or_identity_gate" if not checks or any(not r["raw_matches"] or not r["basket_matches"] or r["missing_identity_rows"] or r["same_timestamp_identity_collisions"] for r in checks) else None
            if reason:base["E"]=(list(q),{"fallback":reason,"scenarios":0,"composition_scenarios":0})
            else:base["E"]=replay({d:v for d,v in x["offers"].items() if d<=origin},origin,h,q)
            forecasts=dict(base)
            for raw,cal in (("A","B"),("C","D"),("E","F")):
                matured=[r for r in past[sid][raw] if r["target"]<=origin]
                qs,diag=calibrate(base[raw][0],matured,origin,h)
                diag["base_fallback"]=base[raw][1].get("fallback")
                if diag["fallback"] is None and diag["base_fallback"]:diag["fallback"]="calibrated_registered_base_fallback"
                forecasts[cal]=(qs,diag)
            target=(date.fromisoformat(origin)+timedelta(days=h)).isoformat();truth=x["values"].get(target)
            if (sid,origin,h) in eligible:
                if truth is None:raise ValueError("Locked eligible truth disappeared")
                for m,(qs,diag) in forecasts.items():
                    cells.append({"method":m,"series_id":sid,"origin":origin,"target":target,"horizon":h,"truth":truth,"anchor":x["values"][origin],"quantiles":qs,"loss":loss(qs,truth),"changed":truth!=x["values"][origin],"diagnostic":diag})
                for m in p["references"]:
                    qs=inp["references"][origin][m].get(key)
                    if qs is None:raise ValueError("Official reference missing eligible cell")
                    cells.append({"method":m,"series_id":sid,"origin":origin,"target":target,"horizon":h,"truth":truth,"anchor":x["values"][origin],"quantiles":ordered(qs),"loss":loss(qs,truth),"changed":truth!=x["values"][origin],"diagnostic":{"fallback":None}})
            # Stored future labels cannot enter calibration until their target matures.
            # Full targets live in the evaluator only; forecasting functions never receive them.
            if truth is not None:
                for m,(qs,diag) in base.items():past[sid][m].append({"origin":origin,"target":target,"horizon":h,"truth":truth,"quantiles":qs})
    expected={k for k in eligible}
    for m in list(p["arms"])+p["references"]:
        actual={(r["series_id"],r["origin"],r["horizon"]) for r in cells if r["method"]==m}
        if actual!=expected:raise ValueError("Matched cohort failure: "+m)
    return {"horizon":h,"cells":cells,"seconds":time.perf_counter()-started,"model_executions":sum(len(v[m]) for v in past.values() for m in v)}
@app.function(image=image,cpu=.25,memory=512,timeout=120,max_containers=1,volumes={"/public":public})
def publish(study):
    from .public_results import private_guard
    private_guard(study);root=Path("/public/price-dynamics-v8");root.mkdir(parents=True,exist_ok=True)
    raw=encoded(study);sha=hashlib.sha256(raw).hexdigest()
    put(root/"artifacts"/(sha+".json"),study)
    tmp=root/"index.pending";tmp.write_bytes(raw);tmp.replace(root/"index.json");public.commit()
    return {"sha256":sha,"url":"/api/price-dynamics-v8","bytes":len(raw)}

@app.function(image=image,cpu=2,memory=4096,timeout=300,volumes={"/data":data})
def verify_official(cells,registry_key,run_id):
    import math
    root=Path("/data/pacific")/PACK_NAME;work=Path(tempfile.mkdtemp(prefix="v8-score-"));p=config()
    _,_,truth,catalog=build_history(root,work,"2026-11-06");reports=[]
    for method in list(p["arms"])+p["references"]:
        ours=[r for r in cells if r["method"]==method]
        fc=work/(method+".csv");report=work/(method+"-score.json");per=work/(method+"-cells.csv")
        records=[{"series_id":r["series_id"],"origin_date":r["origin"],"horizon_days":r["horizon"],"q10":r["quantiles"][0],"q50":r["quantiles"][1],"q90":r["quantiles"][2]} for r in ours]
        write_csv(fc,records,list(records[0]))
        invoke(root,work,"score-"+method,["scorer.py","--forecast",fc,"--truth",truth,"--history",truth,"--catalog",catalog,"--series-ids",",".join(p["series_ids"]),"--horizons","1,3,7","--no-missing-as-baseline","--out",report,"--per-cell",per])
        scored=rows(per);expected={(r["series_id"],r["origin"],r["horizon"]):r for r in ours}
        if len(scored)!=len(expected):raise ValueError("Official scorer denominator mismatch")
        field=next((k for k in scored[0] if k in ("pinball","pinball_loss","loss","mean_pinball")),None)
        if field is None:raise ValueError("Unknown official loss column: "+str(scored[0].keys()))
        for r in scored:
            key=(r["series_id"],r["origin_date"],int(r["horizon_days"]))
            if key not in expected or not math.isclose(float(r[field]),expected[key]["loss"],rel_tol=1e-10,abs_tol=1e-12):raise ValueError("Official scorer disagreement")
        reports.append({"method":method,"verified_cells":len(scored),"official_report":json.loads(report.read_bytes())})
    put(Path("/data/price-dynamics-v8/registry")/registry_key/"completed.json",{"run_id":run_id,"verified":True})
    data.commit();return reports

def main():
    p=config();run_id=os.environ.get("GITHUB_RUN_ID",uuid.uuid4().hex)
    with app.run():
        prep=prepare.remote(run_id)
        parts=list(evaluate_horizon.starmap([(run_id,h) for h in p["horizons"]],order_outputs=True))
        cells=[r for part in parts for r in part["cells"]]
        official=verify_official.remote(cells,prep["registry_key"],run_id)
        inp_audit=prep["audit"];summary=[summarize(cells,m,h) for h in (1,3,7) for m in list(p["arms"])+p["references"]]
        pairs=[paired(cells,c,r,h) for h in p["horizons"] for c,r in (("C","A"),("E","A"),("B","A"),("D","C"),("F","E"))]
        study={"schema_version":8,"study_id":p["study_id"],"classification":p["classification"],"created_at":datetime.now(timezone.utc).isoformat(),"source_sha":os.environ["GITHUB_SHA"],"run_id":run_id,"protocol":p,"protocol_sha256":digest(p),"input_sha256":prep["input_sha256"],"engine_sha256":prep["engine_sha256"],"official_scorer_verification":official,"cohort":{"series_ids":p["series_ids"],"origins":p["origins"],"eligible_cells":prep["eligible"],"missing_target_pairs":prep["excluded"],"temporal_origins":len(p["origins"]),"independence":"Series and horizons dependent; source offer counts are not sample size"},"summary":summary,"pairs":pairs,"cells":cells,"target_audit":inp_audit,"resource_usage":{"prepare_seconds":prep["prepare_seconds"],"workers":[{k:v for k,v in x.items() if k!="cells"} for x in parts],"provider_cost_dollars":None,"optimizer_updates":0},"prospective":{"status":"registered_pending_compatible_fresh_aggregate_capture","forecasts_issued":0,"accuracy_established":False},"official_export_sha256":"67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80","protected_outcomes_loaded":False}
        receipt=publish.remote(study)
    out=Path("artifacts/price-dynamics-v8");out.mkdir(parents=True,exist_ok=True)
    put(out/"study.json",study);put(out/"publication.json",receipt)
    print("V8_RESULT:"+json.dumps({"summary":summary,"pairs":pairs,"audit":inp_audit,"receipt":receipt}),flush=True)
if __name__=="__main__":main()
