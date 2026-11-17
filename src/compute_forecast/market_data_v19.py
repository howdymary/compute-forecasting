"""Build source-bound matched market-state data. No model calls or later truth."""
import collections,gzip,hashlib,json,math,pathlib,statistics,subprocess,tempfile,time
from datetime import date,datetime,timedelta,timezone
import modal
from .starter_probe import PACK_NAME,PACK_SHA256,verify_manifest
from .probability_v18 import digest,support,bin_index
from .market_state_v19 import market_features,check_asof
app=modal.App("compute-forecast-market-v19-data")
volume=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=(modal.Image.debian_slim(python_version="3.11").pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","scikit-learn==1.7.1").add_local_file("configs/market-state-v19.json","/root/configs/market-state-v19.json",copy=True).add_local_file("configs/market-state-v19-readiness.json","/root/configs/market-state-v19-readiness.json",copy=True).add_local_file("results/probability-v18/latest.json","/root/v18-pointer.json",copy=True).add_local_python_source("compute_forecast"))
def clean(v):
    if v is None:return None
    try:
        if __import__("pandas").isna(v):return None
    except (TypeError,ValueError):pass
    return v.item() if hasattr(v,"item") else v
def stamp(s):
    d=datetime.fromisoformat(str(s).replace("Z","+00:00"))
    return d.replace(tzinfo=timezone.utc).isoformat() if d.tzinfo is None else d.astimezone(timezone.utc).isoformat()
def put(p,value):
    raw=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode();p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==raw,"Immutable preparation conflict"
    else:p.write_bytes(raw)
@app.function(image=image,cpu=4,memory=8192,timeout=1800,max_containers=1,volumes={"/data":volume})
def prepare(parent_levels):
    import duckdb,pandas as pd
    start=time.monotonic();p=json.loads(pathlib.Path("/root/configs/market-state-v19.json").read_bytes());gates=json.loads(pathlib.Path("/root/configs/market-state-v19-readiness.json").read_bytes())["gates"]
    engine=digest({"data_engine":hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),"feature_engine":hashlib.sha256(pathlib.Path(__file__).with_name("market_state_v19.py").read_bytes()).hexdigest()})
    input_key=digest({"protocol_sha256":digest(p),"engine_sha256":engine});saved=pathlib.Path("/data/market-state-v19/inputs")/input_key
    if (saved/"audit.json").exists():return {"audit":json.loads((saved/"audit.json").read_bytes()),"private_key":input_key}
    root=pathlib.Path("/data/pacific")/PACK_NAME;verify_manifest(root);c=duckdb.connect();pattern=str(root/"rental_observations"/"*"/"*"/"*.parquet")
    frame=c.execute("SELECT * FROM read_parquet(?,hive_partitioning=false) WHERE source_id IN ('afhubbard','gpurentalprices','fastgpu_daily') AND CAST(dt AS DATE)<=DATE '2026-11-06' AND usd_per_gpu_hour>0 AND quality_flag='ok' AND upper(licence_id)='CC-BY-4.0' AND instrument_class IN ('hyperscaler_spot','neocloud_rate_card') AND pricing_tier IN ('spot','on_demand') AND (gpu_model LIKE 'H100%' OR gpu_model LIKE 'A100%')",[pattern]).df()
    source_notices=c.execute("SELECT source_id,licence_id,quality_flag,count(*) n FROM read_parquet(?,hive_partitioning=false) WHERE source_id IN ('afhubbard','gpurentalprices','fastgpu_daily') AND CAST(dt AS DATE)<=DATE '2026-11-06' GROUP BY ALL",[pattern]).df().to_dict("records")
    fields=["source_id","provider","gpu_model","instrument_class","pricing_tier","sku_raw","region_canonical","gpu_count","gpu_memory_gb"]
    frame["day"]=pd.to_datetime(frame["dt"]).dt.strftime("%Y-%m-%d");frame["capture_day"]=pd.to_datetime(frame["snapshot_ts_utc"]).dt.strftime("%Y-%m-%d")
    bad_days=int((frame["day"]!=frame["capture_day"]).sum());frame=frame[frame["day"]==frame["capture_day"]].copy()
    bad=(frame.groupby(fields+["snapshot_ts_utc"],dropna=False)["usd_per_gpu_hour"].nunique()>1).reset_index(name="bad")
    badkeys={digest({k:clean(r[k]) for k in fields}) for _,r in bad[bad["bad"]].iterrows()}
    grouped=frame.groupby(fields+["day"],dropna=False).agg(value=("usd_per_gpu_hour","median"),records=("usd_per_gpu_hour","size"),last_snapshot=("snapshot_ts_utc","max")).reset_index()
    panels={};byday={};excluded=collections.Counter()
    for _,r in grouped.iterrows():
        ident={k:clean(r[k]) for k in fields};key=digest(ident)
        if key in badkeys:excluded["ambiguous_same_timestamp_group"]+=1;continue
        if not ident["provider"] or not ident["sku_raw"]:excluded["missing_provider_or_sku"]+=1;continue
        sid="pack-market-v19-"+key[:24];meta={**ident,"region":ident["region_canonical"],"series_id":sid,"family":ident["gpu_model"].split()[0],"benchmark_contract":"Source-defined provider/SKU/region/node daily quote median: "+json.dumps(ident,sort_keys=True),"unit":"USD per GPU-hour","availability_assurance":"Source-reported historical snapshot timestamp in frozen Pacific vintage; not independent proof of publication"}
        row={"series_id":sid,"date":r["day"],"value":float(r["value"]),"available_at":stamp(r["last_snapshot"]),"metadata":meta,"records":int(r["records"])}
        panels.setdefault(sid,{"metadata":meta,"rows":{}})["rows"][row["date"]]=row
        byday.setdefault(row["date"],[]).append(row)
    def mkey(m):return tuple(m[k] for k in ("source_id","gpu_model","instrument_class","pricing_tier"))
    provider_sets={}
    for x in panels.values():
        if any(d<=p["data"]["train_origins_through"] for d in x["rows"]):provider_sets.setdefault(mkey(x["metadata"]),set()).add(x["metadata"]["provider"])
    buckets={}
    for sid,x in sorted(panels.items()):
        past=[d for d in x["rows"] if d<=p["data"]["train_origins_through"]]
        if len(past)<gates["min_context_observations"] or len(provider_sets.get(mkey(x["metadata"]),set()))<3:continue
        key=(x["metadata"]["provider"],x["metadata"]["family"]);buckets.setdefault(key,[]).append(sid)
    selected=[]
    while len(selected)<p["data"]["max_target_groups"] and any(buckets.values()):
        for k in sorted(buckets):
            if buckets[k] and len(selected)<p["data"]["max_target_groups"]:selected.append(buckets[k].pop(0))
    def task(sid,origin):
        x=panels[sid];values=x["rows"]
        if origin not in values:return None
        days=[(date.fromisoformat(origin)+timedelta(days=h)).isoformat() for h in p["evaluation"]["horizons"]]
        if any(d not in values for d in days):return None
        context=[r for d,r in sorted(values.items()) if (date.fromisoformat(origin)-timedelta(days=41)).isoformat()<=d<=origin]
        if len(context)<gates["min_context_observations"]:return None
        check_asof(context,origin);anchor=values[origin]["value"]
        t={"task_id":sid+"|"+origin,"series_id":sid,"metadata":x["metadata"],"origin":origin,"anchor":anchor,"context":[{k:r[k] for k in ("date","value","available_at")} for r in context],"context_missing_days":42-len(context),"target_dates":days,"outcomes":[values[d]["value"] for d in days],"returns":[math.log(values[d]["value"]/anchor) for d in days]}
        past={h:byday.get((date.fromisoformat(origin)-timedelta(days=h)).isoformat(),[]) for h in (1,3,7)}
        t["market_state"]=market_features(t,byday.get(origin,[]),origin,past_by_horizon=past)
        t["market_input_identity"]=digest({"origin_quotes":[(r["series_id"],r["value"],r["available_at"]) for r in byday.get(origin,[])],"past_quotes":{str(h):[(r["series_id"],r["value"],r["available_at"]) for r in v] for h,v in past.items()}})
        return t
    groups={k:[] for k in ("training","development","retrospective")}
    for sid in selected:
        options=[]
        for origin in sorted(panels[sid]["rows"]):
            if origin>p["data"]["train_origins_through"]:continue
            t=task(sid,origin)
            if t and max(t["target_dates"])<=p["data"]["train_labels_through"]:options.append(t)
        cap=p["data"]["max_training_windows_per_group"]
        if len(options)>cap:options=[options[i] for i in sorted({round(i*(len(options)-1)/(cap-1)) for i in range(cap)})]
        groups["training"].extend(options)
        for phase in ("development","retrospective"):
            for origin in p["data"][phase+"_origins"]:
                t=task(sid,origin)
                if t:groups[phase].append(t)
    train=groups["training"];metrics={}
    for phase,tasks in groups.items():
        metrics[phase]={"windows":len(tasks),"horizon_examples":len(tasks)*3,"contracts":len({t["series_id"] for t in tasks}),"providers":len({t["metadata"]["provider"] for t in tasks}),"origins":sorted({t["origin"] for t in tasks}),"gpu_families":dict(collections.Counter(t["metadata"]["family"] for t in tasks)),"changed_seven_day":sum(t["anchor"]!=t["outcomes"][2] for t in tasks),"peer_return_coverage":sum((t["market_state"].get("peer_return_provider_count_7d") or 0)>=2 for t in tasks)/len(tasks) if tasks else 0}
    variation={k:{"nonnull":sum(t["market_state"].get(k) is not None for t in train),"distinct":len({t["market_state"][k] for t in train if t["market_state"].get(k) is not None}),"origins":len({t["origin"] for t in train if t["market_state"].get(k) is not None})} for k in p["features"]["market_fields"]}
    varying=[k for k,v in variation.items() if v["distinct"]>1 and v["origins"]>=gates["min_feature_distinct_origins"]]
    reasons=[];a=metrics["training"]
    for field,minimum in (("windows",gates["min_training_windows"]),("contracts",gates["min_training_contracts"]),("providers",gates["min_training_providers"])):
        if a[field]<minimum:reasons.append("insufficient_training_"+field)
    if len(a["origins"])<gates["min_training_origins"]:reasons.append("insufficient_training_origins")
    for phase,minimum in (("development",gates["min_development_windows"]),("retrospective",gates["min_retrospective_windows"])):
        if metrics[phase]["windows"]<minimum:reasons.append("insufficient_"+phase+"_windows")
    if a["peer_return_coverage"]<gates["min_competitor_coverage_fraction"]:reasons.append("insufficient_paired_other_provider_return_coverage")
    if len(varying)<gates["min_varying_market_features"]:reasons.append("insufficient_varying_market_features")
    if train:
        dev=groups["development"];outside=sum(y<support(t["anchor"],parent_levels)[0] or y>support(t["anchor"],parent_levels)[-1] for t in dev for y in t["outcomes"])
        if dev and outside/(3*len(dev))>.05:reasons.append("frozen_support_inadequate_on_development")
    payload={"study_id":p["study_id"],"protocol_sha256":digest(p),"groups":groups,"log_levels":parent_levels,"selected_groups":selected,"protected_outcomes_loaded":False}
    audit={"study_id":p["study_id"],"source_sha":__import__("os").environ.get("GITHUB_SHA"),"protocol_sha256":digest(p),"dataset_sha256":digest(payload),"engine_sha256":engine,"readiness":"passed" if not reasons else "gated","training_ready":not reasons,"reasons":reasons,"phases":metrics,"feature_coverage":variation,"varying_features":varying,"quality_filtered_raw_rows":len(frame),"daily_rows":len(grouped),"snapshot_day_exclusions":bad_days,"ambiguous_groups":len(badkeys),"excluded_daily_rows":dict(excluded),"source_license_quality_counts":source_notices,"selected_groups":selected,"selected_metadata":[panels[sid]["metadata"] for sid in selected],"historical_availability":"Source-reported original snapshot timestamps in frozen pack; no independent publication-vintage proof, historical evaluation retrospective","not_in_training":p["features"]["not_in_training"],"pack_sha256":PACK_SHA256,"new_optimizer_updates":0,"provider_cost_usd":None,"runtime_seconds":time.monotonic()-start}
    put(saved/"dataset.json",payload);put(saved/"audit.json",audit);volume.commit();return {"audit":audit,"private_key":digest(p)}
@app.local_entrypoint()
def main():
    import os
    pointer=json.loads(pathlib.Path("results/probability-v18/latest.json").read_bytes());raw=pathlib.Path(pointer["report_path"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"]
    parent=json.loads(raw);result=prepare.remote(parent["log_levels"]);root=pathlib.Path("artifacts/market-state-v19-data");root.mkdir(parents=True,exist_ok=True)
    (root/"audit.json").write_text(json.dumps(result["audit"],indent=2)+"\n");(root/"input-key.json").write_text(json.dumps({"private_key":result["private_key"],"dataset_sha256":result["audit"]["dataset_sha256"]})+"\n")
    print(json.dumps(result["audit"]),flush=True)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a") as f:f.write("training_ready="+str(result["audit"]["training_ready"]).lower()+"\n")
