"""Issue a timestamped prospective log from the verified, explicitly stale snapshot."""
from __future__ import annotations
import hashlib,json,os,shutil,time,uuid
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import modal
from .campaign_v2 import unpack,build_history,scope_catalog,metadata,now,write,digest,image
from .starter_probe import volume,PACK_SHA256
app=modal.App("compute-forecast-v2-prospective")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
@app.function(image=image,cpu=4,memory=8192,timeout=900,volumes={"/data":volume,"/public":public})
def issue(code_sha):
    import numpy as np
    started=time.perf_counter();temp,root=unpack();work=temp/"prospective";work.mkdir()
    issued=now();origin=datetime.now(ZoneInfo("America/Los_Angeles")).date();cutoff=date(2026,11,6)
    if origin<=cutoff:raise ValueError("Prospective issuance must follow archived cutoff")
    history,catalog=build_history(root,work,cutoff.isoformat());primary=scope_catalog(catalog);rows=[]
    for item in primary.to_dict("records"):
        source=history[history["series_id"]==item["series_id"]]
        values={d:float(v) for d,v in zip(source["day"],source["value"]) if d<=cutoff and np.isfinite(v) and v>0}
        if not values:continue
        latest=max(values)
        for h in (1,3,7):
            target=origin+timedelta(days=h);lead=(target-latest).days
            residuals=[values[d+timedelta(days=lead)]-v for d,v in values.items() if d+timedelta(days=lead) in values and d>=cutoff-timedelta(days=180)]
            qs=np.maximum(values[latest]+np.quantile(residuals,[.1,.5,.9]),1e-6).tolist() if residuals else [values[latest]]*3
            rows.append({"series_id":item["series_id"],"origin_date":origin.isoformat(),"target_date":target.isoformat(),"horizon_days":h,"latest_observed_date":latest.isoformat(),"effective_lead_from_last_observation_days":lead,"q10":qs[0],"q50":qs[1],"q90":qs[2],"matured_residual_pairs":len(residuals),"fallback":None if residuals else "degenerate_last_observation_no_calibration_pairs","statistic":item["statistic"]})
    run_id=uuid.uuid4().hex;private={"schema_version":2,"run_id":run_id,"issued_at":issued,"forecast_origin_timezone":"America/Los_Angeles","code_sha":code_sha,"dataset_sha256":PACK_SHA256,"data_cutoff":cutoff.isoformat(),"method":"last observed level plus empirical matured differences at the effective calendar lead; last 180 calendar days","forecast_origin":origin.isoformat(),"rows":rows,"outcome_status":"pending; future outcomes never loaded","market_freshness":"stale archived snapshot, no current quote access","calibration_claim":"empirical quantiles, no guaranteed nominal future coverage","licensing":"Numerical forecasts retained privately pending separate publication review"}
    encoded=json.dumps(private,sort_keys=True,allow_nan=False).encode();path=Path("/data/campaign-v2/prospective")/(run_id+".json");write(path,private);volume.commit()
    manifest={k:v for k,v in private.items() if k!="rows"}
    manifest.update(forecast_count=len(rows),series_count=len({r["series_id"] for r in rows}),forecast_sha256=hashlib.sha256(encoded).hexdigest(),target_dates=sorted({r["target_date"] for r in rows}),horizons=[1,3,7],history_age_days=(origin-cutoff).days,contains_h100=any("H100" in r["series_id"] for r in rows),runtime_seconds=time.perf_counter()-started,modal_call_id=modal.current_function_call_id(),private_forecasts_retained=True)
    public.reload();write(Path("/public/experimental-v2/prospective-manifest.json"),manifest);public.commit();shutil.rmtree(temp);return manifest
@app.local_entrypoint()
def main():
    result=issue.remote(os.environ["GITHUB_SHA"]);write(Path("artifacts/v2-prospective/manifest.json"),result);print("V2_PROSPECTIVE:"+json.dumps(result),flush=True)
