"""Verify historical ALFRED vintages; current-news retrieval is not backdated."""
from __future__ import annotations
import csv,hashlib,io,json,os,pathlib,time,urllib.request
from datetime import date,datetime,timezone
from compute_forecast.direct_forecast_v12 import digest
def fetch(url):
    request=urllib.request.Request(url,headers={"User-Agent":"ComputeForecastResearch/1.0"})
    with urllib.request.urlopen(request,timeout=45) as response:
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError("Response byte budget")
        return raw,{"url":url,"status":response.status,"retrieved_at":datetime.now(timezone.utc).isoformat(),"content_sha256":hashlib.sha256(raw).hexdigest(),"content_type":response.headers.get("Content-Type")}
def main():
    config=json.loads(pathlib.Path("configs/direct-v12-supplementary.json").read_text())
    parent=json.loads(pathlib.Path("configs/direct-forecast-v12.json").read_text())
    root=pathlib.Path("inputs/direct-v12");dataset=json.loads((root/"dataset.json").read_text())
    origins=sorted({t["origin"] for tasks in dataset["groups"].values() for t in tasks})
    assert len(origins)<=config["limits"]["max_csv_requests"]
    vintages={};failures=[];receipts=[]
    for origin in origins:
        url=config["historical_source"]["url_template"].format(origin=origin)
        try:
            raw,receipt=fetch(url);receipts.append(receipt);rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
            expected="PCU221122221122_"+origin.replace("-","")
            if not rows or expected not in rows[0]:raise ValueError("Requested vintage not confirmed by CSV header")
            obs=[]
            for row in rows:
                day=row.get("observation_date") or row.get("DATE")
                if not day or day>origin:raise ValueError("Future observation or missing date")
                value=row[expected]
                if value in ("","."):continue
                number=float(value)
                if number<=0:raise ValueError("Non-positive index")
                obs.append((day,number))
            obs.sort()
            if len(obs)<2:raise ValueError("Insufficient vintage observations")
            previous,latest=obs[-2],obs[-1]
            vintages[origin]={"source":"US BLS via ALFRED","source_url":url,"series_id":"PCU221122221122","vintage_date":origin,"available_at":origin+"T23:59:59+00:00","availability_semantics":"Verified archived state as of origin; timestamp is a conservative known-by bound, not an asserted release time","first_retrieved_at":receipt["retrieved_at"],"content_sha256":receipt["content_sha256"],"latest_observation_period":latest[0][:7],"latest_available_index":latest[1],"month_over_month_change":latest[1]/previous[1]-1,"age_days_since_observation_period_start":(date.fromisoformat(origin)-date.fromisoformat(latest[0])).days,"unit":"PPI index, December 2003=100; not USD/kWh"}
        except Exception as e:failures.append({"origin":origin,"error_type":type(e).__name__,"message":str(e)[:200],"url":url})
        time.sleep(config["limits"]["request_spacing_seconds"])
    distinct=len({v["latest_observation_period"] for v in vintages.values()})
    coverage=len(vintages)/len(origins)
    # All original tasks remain. Missing signal records are explicit; no outcome-based exclusions.
    evidence_ready=coverage>=config["historical_source"]["minimum_origin_coverage"] and distinct>=config["historical_source"]["minimum_distinct_latest_periods"]
    current=[]
    for source in config["current_only_sources"]:
        try:
            raw,receipt=fetch(source["url"]);payload=json.loads(raw)
            current.append({**source,**receipt,"payload_date":payload.get("date") or payload.get("snapshot_date"),"top_level_keys":sorted(payload),"price_rows_retained":False,"historical_prices_downloaded":False})
        except Exception as e:current.append({**source,"error_type":type(e).__name__})
    report={"study_id":config["study_id"],"parent_protocol_sha256":digest(parent),"capture_config_sha256":digest(config),"created_at":datetime.now(timezone.utc).isoformat(),"origins_requested":len(origins),"origins_verified":len(vintages),"origin_coverage":coverage,"distinct_latest_periods":distinct,"evidence_ready":evidence_ready,"vintages":vintages,"failures":failures,"receipts":receipts,"current_source_audits":current,"protected_outcomes_loaded":False,"news_effect":"not_tested","infrastructure_effect":"not_tested","BLS_effect":"pending_matched_training","permission":"BLS government statistics via ALFRED; source attribution and archived-vintage semantics retained"}
    out=pathlib.Path("artifacts/direct-v12-supplementary");out.mkdir(parents=True,exist_ok=True)
    (out/"source-audit.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("vintages","receipts")},indent=2))
if __name__=="__main__":main()
