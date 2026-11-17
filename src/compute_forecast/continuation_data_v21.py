"""Expand source-specific training windows only; all v19 evaluation tasks stay byte-identical."""
import collections,hashlib,json,math,os,pathlib,statistics,time
from datetime import date,datetime,timedelta,timezone
import modal
from .starter_probe import PACK_NAME,PACK_SHA256,verify_manifest
from .probability_v18 import digest
from .market_state_v19 import check_asof,prompt
from .continuation_v21 import counts,validate_training
app=modal.App("compute-forecast-ce-continuation-v21-data")
volume=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","scikit-learn==1.7.1").add_local_python_source("compute_forecast")
def choose(values,limit):
    if len(values)<=limit:return values
    if limit<=0:return []
    if limit==1:return [values[0]]
    return [values[i] for i in sorted({round(i*(len(values)-1)/(limit-1)) for i in range(limit)})]
def clean(v):
    if v is None:return None
    try:
        if __import__("pandas").isna(v):return None
    except (TypeError,ValueError):pass
    return v.item() if hasattr(v,"item") else v
def stamp(s):
    d=datetime.fromisoformat(str(s).replace("Z","+00:00"))
    return d.replace(tzinfo=timezone.utc).isoformat() if d.tzinfo is None else d.astimezone(timezone.utc).isoformat()
def put(path,value):
    raw=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode();path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==raw,"Immutable preparation conflict"
    else:path.write_bytes(raw)
@app.function(image=image,cpu=4,memory=8192,timeout=2400,max_containers=1,volumes={"/data":volume})
def prepare(p,old_pointer,source_sha):
    import duckdb,pandas as pd
    started=time.monotonic();parent=pathlib.Path("/data/market-state-v19/inputs")/old_pointer["private_key"]
    original=json.loads((parent/"dataset.json").read_bytes());assert digest(original)==p["parent"]["dataset_sha256"]==old_pointer["dataset_sha256"]
    assert len(original["groups"]["training"])==314 and len(original["log_levels"])==19
    engine=digest({name:hashlib.sha256(pathlib.Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ("continuation_data_v21.py","continuation_v21.py","market_state_v19.py")})
    key=digest({"protocol":digest(p),"parent_dataset":digest(original),"engine":engine});target=pathlib.Path("/data/ce-continuation-v21/inputs")/key
    if (target/"audit.json").exists():return {"audit":json.loads((target/"audit.json").read_bytes()),"input_key":key}
    root=pathlib.Path("/data/pacific")/PACK_NAME;members=verify_manifest(root);con=duckdb.connect()
    pattern=str(root/"rental_observations"/"*"/"*"/"*.parquet")
    frame=con.execute("SELECT * FROM read_parquet(?,hive_partitioning=false) WHERE source_id IN ('afhubbard','gpurentalprices','fastgpu_daily') AND CAST(dt AS DATE)<=DATE '2026-10-11' AND usd_per_gpu_hour>0 AND isfinite(usd_per_gpu_hour) AND quality_flag='ok' AND upper(licence_id)='CC-BY-4.0' AND instrument_class IN ('hyperscaler_spot','neocloud_rate_card') AND pricing_tier IN ('spot','on_demand') AND (gpu_model LIKE 'H100%' OR gpu_model LIKE 'A100%')",[pattern]).df()
    source_counts=frame.groupby(["source_id","licence_id","instrument_class","pricing_tier"],dropna=False).size().reset_index(name="rows").to_dict("records")
    fields=["source_id","provider","gpu_model","instrument_class","pricing_tier","sku_raw","region_canonical","gpu_count","gpu_memory_gb"]
    frame["day"]=pd.to_datetime(frame["dt"]).dt.strftime("%Y-%m-%d");frame["capture_day"]=pd.to_datetime(frame["snapshot_ts_utc"]).dt.strftime("%Y-%m-%d")
    mismatched_days=int((frame["day"]!=frame["capture_day"]).sum());frame=frame[frame["day"]==frame["capture_day"]].copy()
    bad=(frame.groupby(fields+["snapshot_ts_utc"],dropna=False)["usd_per_gpu_hour"].nunique()>1).reset_index(name="bad")
    badkeys={digest({k:clean(r[k]) for k in fields}) for _,r in bad[bad["bad"]].iterrows()}
    grouped=frame.groupby(fields+["day"],dropna=False).agg(value=("usd_per_gpu_hour","median"),records=("usd_per_gpu_hour","size"),last_snapshot=("snapshot_ts_utc","max")).reset_index()
    panels={};exclusions=collections.Counter()
    for _,row in grouped.iterrows():
        ident={k:clean(row[k]) for k in fields};key_id=digest(ident)
        if key_id in badkeys:exclusions["ambiguous_group"]+=1;continue
        if not ident["provider"] or not ident["sku_raw"]:exclusions["missing_provider_or_sku"]+=1;continue
        sid="pack-market-v19-"+key_id[:24]
        meta={**ident,"region":ident["region_canonical"],"series_id":sid,"family":ident["gpu_model"].split()[0],"benchmark_contract":"Source-defined provider/SKU/region/node daily quote median: "+json.dumps(ident,sort_keys=True),"unit":"USD per GPU-hour","availability_assurance":"Source-reported historical snapshot timestamp in frozen Pacific vintage; not independent proof of publication"}
        panels.setdefault(sid,{"metadata":meta,"rows":{}})["rows"][row["day"]]={"date":row["day"],"value":float(row["value"]),"available_at":stamp(row["last_snapshot"])}
    def task(sid,origin):
        panel=panels[sid];rows=panel["rows"]
        if origin not in rows or origin>p["data"]["train_origins_through"]:return None
        targets=[(date.fromisoformat(origin)+timedelta(days=h)).isoformat() for h in p["data"]["horizons"]]
        if max(targets)>p["data"]["train_labels_through"] or any(d not in rows for d in targets):return None
        context=[r for d,r in sorted(rows.items()) if (date.fromisoformat(origin)-timedelta(days=41)).isoformat()<=d<=origin]
        if len(context)<p["data"]["min_context_observations"]:return None
        check_asof(context,origin);anchor=rows[origin]["value"];y=[rows[d]["value"] for d in targets]
        if any(rows[d]["available_at"][:10]>p["data"]["train_labels_through"] for d in targets):return None
        return {"task_id":sid+"|"+origin,"series_id":sid,"metadata":panel["metadata"],"origin":origin,"anchor":anchor,"context":context,"context_missing_days":42-len(context),"target_dates":targets,"target_available_at":[rows[d]["available_at"] for d in targets],"outcomes":y,"returns":[math.log(v/anchor) for v in y],"market_state":{},"market_input_identity":"withheld_price_only"}
    original_tasks=original["groups"]["training"];mandatory={t["task_id"]:t for t in original_tasks};mismatches=[]
    for old in original_tasks:
        new=task(old["series_id"],old["origin"]) if old["series_id"] in panels else None
        if new is None or any(prompt({**old,"arm":"price"},h)!=prompt({**new,"arm":"price"},h) for h in (1,3,7)) or new["outcomes"]!=old["outcomes"]:mismatches.append(old["task_id"])
    import bisect
    eligible={}
    for sid,panel in sorted(panels.items()):
        days=sorted(panel["rows"]);dayset=set(days);origins=[]
        for index,origin in enumerate(days):
            if origin>p["data"]["train_origins_through"]:break
            targets=[(date.fromisoformat(origin)+timedelta(days=h)).isoformat() for h in (1,3,7)]
            if max(targets)>p["data"]["train_labels_through"] or any(d not in dayset for d in targets):continue
            left=(date.fromisoformat(origin)-timedelta(days=41)).isoformat()
            if index-bisect.bisect_left(days,left)+1>=p["data"]["min_context_observations"]:origins.append(origin)
        if origins:eligible[sid]=origins
    selected=list(dict.fromkeys(t["series_id"] for t in original_tasks));buckets={}
    for sid in sorted(eligible):
        if sid in selected:continue
        m=panels[sid]["metadata"];bucket=(m["source_id"],m["provider"],m["family"],m["instrument_class"],m["pricing_tier"])
        buckets.setdefault(bucket,[]).append(sid)
    while len(selected)<p["data"]["max_training_groups"] and any(buckets.values()):
        for bucket in sorted(buckets):
            if buckets[bucket] and len(selected)<p["data"]["max_training_groups"]:selected.append(buckets[bucket].pop(0))
    extra={}
    for sid in selected:
        old_count=sum(t["series_id"]==sid for t in original_tasks)
        candidates=[t for origin in eligible.get(sid,[]) if (t:=task(sid,origin)) is not None and t["task_id"] not in mandatory]
        extra[sid]=choose(candidates,max(0,p["data"]["max_windows_per_group"]-old_count))
    expanded=list(original_tasks);queues={sid:list(tasks) for sid,tasks in extra.items()}
    while len(expanded)<p["data"]["max_expanded_windows"] and any(queues.values()):
        for sid in sorted(queues):
            if queues[sid] and len(expanded)<p["data"]["max_expanded_windows"]:expanded.append(queues[sid].pop(0))
    validate_training(original_tasks,p);validate_training(expanded,p)
    a,b=counts(original_tasks,original["log_levels"]),counts(expanded,original["log_levels"]);g=p["readiness"];reasons=[]
    if mismatches:reasons.append("original_target_or_prompt_reconstruction_mismatch")
    for value,minimum,reason in ((b["windows"],g["min_expanded_windows"],"insufficient_expanded_windows"),(b["groups"]-a["groups"],g["min_added_groups"],"insufficient_additional_groups"),(len(b["origins"]),g["min_distinct_expanded_origins"],"insufficient_expanded_temporal_coverage"),(b["changed_7d"],g["min_expanded_changed_7d_windows"],"insufficient_changed_price_training_windows"),(b["providers"],g["min_providers"],"insufficient_provider_coverage")):
        if value<minimum:reasons.append(reason)
    if b["out_of_support_fraction"]>g["max_training_out_of_support_fraction"]:reasons.append("frozen_support_inadequate_for_expanded_corpus")
    assert all(t["task_id"] in {x["task_id"] for x in expanded} for t in original_tasks)
    payload={"study_id":p["study_id"],"protocol_sha256":digest(p),"parent_dataset_sha256":digest(original),"log_levels":original["log_levels"],"training":{"same":original_tasks,"expanded":expanded},"groups":{"development":original["groups"]["development"],"retrospective":original["groups"]["retrospective"]},"expanded_ready":not reasons}
    encoded=json.dumps(payload,sort_keys=True,allow_nan=False,separators=(",",":")).encode()
    if len(encoded)>p["limits"]["max_private_input_bytes"]:raise ValueError("Registered input byte limit; no optimization")
    audit={"study_id":p["study_id"],"protocol_sha256":digest(p),"dataset_sha256":digest(payload),"parent_dataset_sha256":digest(original),"engine_sha256":engine,"source_sha":source_sha,"same_ready":True,"expanded_ready":not reasons,"expanded_gate_reasons":reasons,"training_corpus_sha256":{arm:digest(tasks) for arm,tasks in payload["training"].items()},"counts":{"same":a,"expanded":b},"evaluation_unchanged":{"development_sha256":digest(payload["groups"]["development"]),"retrospective_sha256":digest(payload["groups"]["retrospective"]),"development_windows":len(payload["groups"]["development"]),"retrospective_windows":len(payload["groups"]["retrospective"])},"original_reconstruction_mismatches":mismatches[:20],"source_license_counts":source_counts,"quality_filtered_raw_rows":len(frame),"daily_groups":len(grouped),"snapshot_day_exclusions":mismatched_days,"ambiguous_groups":len(badkeys),"excluded_daily_rows":dict(exclusions),"selected_metadata":[panels[sid]["metadata"] for sid in selected if sid in panels],"pack_sha256":PACK_SHA256,"manifest_entries":members,"manifest_plus_manifest_file":members+1,"input_bytes":len(encoded),"new_optimizer_updates":0,"new_model_calls":0,"runtime_seconds":time.monotonic()-started,"provider_cost_usd":None,"historical_availability":p["data"]["historical_availability"],"source_attribution":"Pacific Machines gpu-price-pack v0.1.1-handover, CC BY 4.0 compilation; approved source IDs afhubbard, gpurentalprices, fastgpu_daily retain component attribution; no raw redistribution"}
    put(target/"dataset.json",payload);put(target/"audit.json",audit);volume.commit();return {"audit":audit,"input_key":key}
@app.local_entrypoint()
def main():
    p=json.loads(pathlib.Path("configs/ce-continuation-v21.json").read_bytes());pointer=json.loads(pathlib.Path(p["parent"]["input_pointer"]).read_bytes())
    result=prepare.remote(p,pointer,os.environ["GITHUB_SHA"]);out=pathlib.Path("artifacts/ce-continuation-v21-preflight");out.mkdir(parents=True,exist_ok=True)
    (out/"audit.json").write_text(json.dumps(result["audit"],indent=2,allow_nan=False)+"\n")
    (out/"input-key.json").write_text(json.dumps({"input_key":result["input_key"],"dataset_sha256":result["audit"]["dataset_sha256"]},indent=2)+"\n")
    print(json.dumps({"same_ready":True,"expanded_ready":result["audit"]["expanded_ready"],"counts":{k:{z:v[z] for z in ("windows","groups","providers","changed_7d")} for k,v in result["audit"]["counts"].items()},"reasons":result["audit"]["expanded_gate_reasons"]}),flush=True)
