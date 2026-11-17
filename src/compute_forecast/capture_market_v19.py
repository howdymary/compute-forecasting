"""Retain source-day vintages; no forecasting, training or public raw-data endpoint."""
from __future__ import annotations
import hashlib,json,os,pathlib,time
from datetime import datetime,timezone
import modal
from .market_state_v19 import normalize_latest
from .probability_v18 import digest
app=modal.App("compute-forecast-market-v19-capture")
volume=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").pip_install("httpx[http2]==0.28.1").add_local_python_source("compute_forecast")
def write(path,value):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(value,sort_keys=True,allow_nan=False,indent=2)+"\n").encode()
    temp=path.with_suffix(".pending");temp.write_bytes(raw);temp.replace(path);return hashlib.sha256(raw).hexdigest()
@app.function(image=image,cpu=1,memory=1024,timeout=180,max_containers=1,volumes={"/data":volume})
def capture():
    import httpx
    started=time.monotonic();at=datetime.now(timezone.utc);stamp=at.isoformat();root=pathlib.Path("/data/market-state-v19/capture")
    protocol=json.loads(pathlib.Path("configs/market-state-v19-prospective.json").read_bytes())
    if at>=datetime.fromisoformat(protocol["limits"]["stop_after_utc"]):raise ValueError("Registered capture stop reached")
    prior=list((root/"attempts").glob("*.json"))
    if len(prior)>=protocol["limits"]["max_source_snapshots"]:raise ValueError("Registered capture-attempt limit reached")
    result={"study_id":"market-state-v19","attempted_at":stamp,"status":"failed","new_optimizer_updates":0,"provider_cost_usd":None}
    attempt_id=stamp.replace(":","").replace(".","-")
    try:
        raw={}
        with httpx.Client(http2=True,timeout=40,follow_redirects=True) as client:
            for name,url in (("latest","https://gpurentalprices.com/api/latest.json"),("health","https://gpurentalprices.com/api/health.json")):
                response=client.get(url);response.raise_for_status()
                if len(response.content)>5000000:raise ValueError("Source exceeds capture budget")
                body=response.content;identity=hashlib.sha256(body).hexdigest()
                destination=root/"raw"/(identity+".json");destination.parent.mkdir(parents=True,exist_ok=True)
                if destination.exists():assert hashlib.sha256(destination.read_bytes()).hexdigest()==identity
                else:destination.write_bytes(body)
                raw[name]={"value":response.json(),"sha256":identity,"url":url,"http_version":response.http_version}
        at=datetime.now(timezone.utc);stamp=at.isoformat()
        snapshot=normalize_latest(raw["latest"]["value"],raw["health"]["value"],stamp,raw["latest"]["sha256"],raw["health"]["sha256"])
        rows=snapshot["rows"];day=snapshot["date"]
        # Identical bodies retain their original first-observed timestamp.
        key=digest({"source":snapshot["source_sha256"],"health":snapshot["health_sha256"]})
        target=root/"vintages"/day/(key+".json")
        if target.exists():snapshot=json.loads(target.read_bytes());new=False
        else:write(target,snapshot);new=True
        valid_window=protocol["capture_window_utc_hours"][0]<=at.hour<protocol["capture_window_utc_hours"][1]
        result.update(status="captured",observed_day=day,retrieved_at=stamp,first_observed_at=snapshot["captured_at"],new_vintage=new,rows=len(rows),providers=sorted({r["metadata"]["provider"] for r in rows}),gpu_families=sorted({r["metadata"]["family"] for r in rows}),source_sha256=snapshot["source_sha256"],health_sha256=snapshot["health_sha256"],vintage_sha256=digest(snapshot),observation_is_today=day==at.date().isoformat(),within_registered_window=valid_window,eligible_for_origin=valid_window and day==at.date().isoformat(),exclusions=snapshot["excluded"],permission_url=snapshot["permission_url"],license=snapshot["license"],quote_update_timestamp_verified=False)
        # Public permitted prices are separate from private source bodies.
        result["observations"]=rows
    except Exception as error:result.update(error_type=type(error).__name__,error=str(error)[:300])
    result["runtime_seconds"]=time.monotonic()-started
    write(root/"attempts"/(attempt_id+".json"),result);volume.commit();return result
@app.local_entrypoint()
def main():
    result=capture.remote();root=pathlib.Path("artifacts/market-state-v19-capture");write(root/"capture.json",result)
    print(json.dumps({k:v for k,v in result.items() if k!="observations"}),flush=True)
    if result["status"]!="captured":raise RuntimeError("Source collection failed; retained failure receipt")
