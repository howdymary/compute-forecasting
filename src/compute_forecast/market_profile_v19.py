"""Read-only pack/profile preparation, current-source vintages; no forecasting or training."""
import hashlib,json,pathlib,time,urllib.request
from datetime import datetime,timezone
import modal
from .starter_probe import PACK_NAME,PACK_SHA256,verify_manifest
from .probability_v18 import digest
app=modal.App("compute-forecast-market-v19-profile")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=(modal.Image.debian_slim(python_version="3.11").pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","httpx[http2]==0.28.1").add_local_file("configs/market-state-v19-readiness.json","/root/configs/market-state-v19-readiness.json",copy=True).add_local_python_source("compute_forecast"))
def atomic(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);raw=json.dumps(v,sort_keys=True,indent=2,allow_nan=False,default=str)+"\n"
    if p.exists():assert p.read_text()==raw,"Immutable preparation conflict"
    else:p.write_text(raw)
@app.function(image=image,cpu=4,memory=8192,timeout=1200,max_containers=1,volumes={"/data":data})
def profile():
    import duckdb,pandas as pd,httpx
    start=time.monotonic();p=json.loads(pathlib.Path("/root/configs/market-state-v19-readiness.json").read_bytes())
    root=pathlib.Path("/data/pacific")/PACK_NAME;members=verify_manifest(root)
    c=duckdb.connect();pattern=str(root/"rental_observations"/"*"/"*"/"*.parquet")
    c.execute("CREATE VIEW offers AS SELECT * FROM read_parquet('"+pattern.replace("'","''")+"',hive_partitioning=false)")
    schema=c.execute("DESCRIBE offers").fetchall();cols={r[0] for r in schema}
    source="SELECT * FROM offers WHERE source_id IN ('afhubbard','gpurentalprices','fastgpu_daily') AND CAST(dt AS DATE)<=DATE '2026-11-06' AND usd_per_gpu_hour>0 AND (gpu_model LIKE 'H100%' OR gpu_model LIKE 'A100%')"
    frame=c.execute(source).df();frame["day"]=pd.to_datetime(frame["dt"]).dt.strftime("%Y-%m-%d")
    identity=[x for x in ("source_id","provider","gpu_model","instrument_class","pricing_tier","sku_raw","region_canonical","gpu_count","gpu_memory_gb","licence_id","source_url") if x in cols]
    groups=frame.groupby(["source_id","gpu_model","instrument_class","pricing_tier"],dropna=False).agg(rows=("day","size"),days=("day","nunique"),first_day=("day","min"),last_day=("day","max"),providers=("provider","nunique")).reset_index().to_dict("records")
    nulls={col:int((frame[col].isna()|frame[col].astype("string").eq("")).sum()) for col in identity}
    selected=frame[identity+["day","usd_per_gpu_hour","snapshot_ts_utc"]].copy()
    selected=selected.where(pd.notna(selected),None)
    private=pathlib.Path("/data/market-state-v19/preparation")/digest(p)
    raw=selected.to_json(orient="records",date_format="iso")
    assert len(raw.encode())<=p["limits"]["max_private_profile_bytes"],"Profile byte budget"
    private.mkdir(parents=True,exist_ok=True);target=private/"offer-inputs.json"
    if target.exists():assert hashlib.sha256(target.read_bytes()).hexdigest()==hashlib.sha256(raw.encode()).hexdigest()
    else:target.write_text(raw)
    receipts=[];quote_metadata={}
    with httpx.Client(http2=True,timeout=30,headers={"User-Agent":"ComputeForecastResearch/1.0"}) as client:
        for key in ("current_quote","current_health"):
            url=p["sources"][key];at=datetime.now(timezone.utc).isoformat()
            try:
                response=client.get(url);response.raise_for_status();body=response.content;value=response.json();sha=hashlib.sha256(body).hexdigest()
                source_dir=private/"current";source_dir.mkdir(exist_ok=True);path=source_dir/(sha+".json")
                if not path.exists():path.write_bytes(body)
                receipt={"kind":key,"url":url,"retrieved_at":at,"sha256":sha,"bytes":len(body),"http_version":response.http_version,"keys":sorted(value),"snapshot_date":value.get("date") or value.get("snapshot_date")}
                receipts.append(receipt)
                if key=="current_quote":quote_metadata={"offer_keys":sorted({k for r in value.get("offers",[]) for k in r}),"n_offers":len(value.get("offers",[])),"gpu_variants":sorted({r.get("gpu","") for r in value.get("offers",[]) if str(r.get("gpu","")).startswith(("a100","h100"))}),"generated_at":value.get("generated_at")}
            except Exception as error:receipts.append({"kind":key,"url":url,"retrieved_at":at,"status":"unavailable","error_type":type(error).__name__})
    result={"study_id":p["study_id"],"stage":"schema_and_coverage_only","readiness_protocol_sha256":digest(p),"source_sha":__import__("os").environ.get("GITHUB_SHA"),"pack_sha256":PACK_SHA256,"manifest_entries":members,"schema":[list(r) for r in schema],"identity_fields":identity,"identity_missing_rows":nulls,"groups":groups,"historical_observations":len(frame),"private_input_sha256":hashlib.sha256(raw.encode()).hexdigest(),"current_source_receipts":receipts,"current_quote_metadata":quote_metadata,"new_optimizer_updates":0,"model_calls":0,"protected_outcomes_loaded":False,"runtime_seconds":time.monotonic()-start}
    atomic(private/"profile.json",result);data.commit();return result
@app.local_entrypoint()
def main():
    value=profile.remote();root=pathlib.Path("artifacts/market-state-v19-profile");root.mkdir(parents=True,exist_ok=True)
    (root/"profile.json").write_text(json.dumps(value,indent=2,default=str)+"\n")
    print(json.dumps(value,default=str),flush=True)
