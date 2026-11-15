"""Independently retrieve CC BY4 Hubbard history; candidate values remain private."""
from __future__ import annotations
import concurrent.futures,hashlib,io,json,math,os,re,shutil,time,uuid
from datetime import date,datetime,timezone
from pathlib import Path
from urllib.parse import urlencode,quote
from urllib.request import urlopen,Request
import xml.etree.ElementTree as ET
import modal
from .starter_probe import image,volume,PACK_SHA256
from .campaign_v2 import unpack,build_history
app=modal.App("compute-forecast-upstream-history-v3")
BASE="https://hubbard-gpu-price-data.s3.amazonaws.com/"
LICENSE_URL="https://raw.githubusercontent.com/alex-hubbard/gpu_price_tracker/ac287bacc95f3b2ceaa97af10a50031ee0abcacf/DATA_LICENSE"
CUTOFF="2026-11-06"
SIDS={"A100_40GB":"afhubbard.hyperscaler_spot.A100_40GB.spot.median","A100_SXM_80GB":"afhubbard.hyperscaler_spot.A100_SXM_80GB.spot.median","T4":"afhubbard.hyperscaler_spot.T4.spot.median","V100":"afhubbard.hyperscaler_spot.V100.spot.median"}
def request(url):
    with urlopen(Request(url,headers={"User-Agent":"ComputeForecastResearch/1.0"}),timeout=90) as response:return response.read(),dict(response.headers)
def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+".pending")
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n");tmp.replace(path)
def list_keys():
    rows=[];token=None;ns={"s":"http://s3.amazonaws.com/doc/2006-03-01/"}
    for _ in range(10):
        params={"list-type":"2","prefix":"prices/","max-keys":"1000"}
        if token:params["continuation-token"]=token
        raw,_=request(BASE+"?"+urlencode(params));root=ET.fromstring(raw)
        for item in root.findall("s:Contents",ns):
            key=item.findtext("s:Key",namespaces=ns)
            match=re.search(r"/dt=(\d{4}-\d{2}-\d{2})/",key or "")
            if key and key.endswith(".parquet") and match and "2026-01-01"<=match.group(1)<=CUTOFF:
                rows.append({"key":key,"partition_date":match.group(1),"etag":item.findtext("s:ETag",namespaces=ns),"last_modified":item.findtext("s:LastModified",namespaces=ns),"bytes":int(item.findtext("s:Size",namespaces=ns))})
        token=root.findtext("s:NextContinuationToken",namespaces=ns)
        if not token:break
    else:raise ValueError("Metadata listing exceeds bounded page budget")
    if not rows or len(rows)>750 or sum(r["bytes"] for r in rows)>300_000_000:raise ValueError("Unexpected/oversized pre-cutoff archive")
    return sorted(rows,key=lambda r:r["key"])
@app.function(image=image,cpu=2,memory=8192,timeout=1200,max_containers=1,volumes={"/data":volume})
def inspect(source_sha,workflow_run):
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq
    started=time.perf_counter();license_bytes,_=request(LICENSE_URL);license_text=license_bytes.decode()
    if "s3://hubbard-gpu-price-data/prices/" not in license_text or "CC BY 4.0" not in license_text or "Share" not in license_text or "Adapt" not in license_text:raise ValueError("Explicit upstream permission not verified")
    objects=list_keys();stamp=uuid.uuid4().hex;root=Path("/data/phase3-history/upstream")/stamp;root.mkdir(parents=True)
    schemas=set();gpus=set();providers=set();receipts=[]
    def read_object(item):
        if item["partition_date"]>CUTOFF:raise ValueError("Post-cutoff downloads prohibited")
        raw,headers=request(BASE+quote(item["key"],safe="/="))
        if len(raw)!=item["bytes"]:raise ValueError("Source object changed size")
        sha=hashlib.sha256(raw).hexdigest()
        path=root/(sha+".parquet");path.write_bytes(raw)
        table=pq.read_table(io.BytesIO(raw));frame=table.to_pandas()
        required={"timestamp","provider","gpu_type","gpu_count","gpu_memory_gb","price_per_hour","is_spot"}
        if not required<=set(frame):raise ValueError("Upstream schema changed: "+str(sorted(frame.columns)))
        dates=pd.to_datetime(frame["timestamp"],utc=True)
        if (dates.dt.date>date.fromisoformat(CUTOFF)).any():raise ValueError("A selected pre-cutoff object contains later observations; not used")
        frame["day"]=dates.dt.strftime("%Y-%m-%d")
        mask=frame["provider"].astype(str).str.lower().isin(["aws","azure","gcp"])&frame["is_spot"].fillna(False).astype(bool)&(pd.to_numeric(frame["gpu_count"],errors="coerce")>0)
        if "quality" in frame:mask&=frame["quality"].astype(str).eq("ok")
        frame=frame[mask].copy();family=frame["gpu_type"].astype(str).str.upper();memory=pd.to_numeric(frame["gpu_memory_gb"],errors="coerce")
        frame["model"]=np.select([family.str.contains("A100")&memory.eq(40),family.str.contains("A100")&memory.eq(80),family.str.contains(r"\bT4\b")&memory.eq(16),family.str.contains("V100")],["A100_40GB","A100_SXM_80GB","T4","V100"],default="")
        frame=frame[frame["model"]!=""].copy()
        frame["value"]=pd.to_numeric(frame["price_per_hour"],errors="coerce")/pd.to_numeric(frame["gpu_count"],errors="coerce")
        frame=frame[np.isfinite(frame["value"])&(frame["value"]>0)]
        receipt={**item,"sha256":sha,"response_etag":headers.get("ETag"),"url":BASE+quote(item["key"],safe="/=")}
        return frame[["day","model","value"]],receipt,tuple(sorted(required)),frame["gpu_type"].astype(str).unique().tolist(),frame["provider"].astype(str).unique().tolist()
    frames=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for frame,receipt,schema,gpu,provider in executor.map(read_object,objects):
            frames.append(frame);receipts.append(receipt);schemas.update(schema);gpus.update(gpu);providers.update(provider)
    raw=pd.concat(frames,ignore_index=True)
    if raw.empty:raise ValueError("No compatible upstream observations")
    grouped=raw.groupby(["day","model"],sort=True)["value"].median().reset_index()
    temp,pack=unpack();work=temp/"compare";work.mkdir();official,cat=build_history(pack,work,CUTOFF)
    candidates=[];private_curves={}
    for model,sid in SIDS.items():
        curve=grouped[grouped["model"]==model].sort_values("day")
        points=[{"date":r["day"],"value":float(r["value"])} for r in curve.to_dict("records")]
        benchmark={d.isoformat():float(v) for d,v in zip(official[official["series_id"]==sid]["day"],official[official["series_id"]==sid]["value"])}
        overlap=[(p["date"],p["value"],benchmark[p["date"]]) for p in points if p["date"] in benchmark]
        matches=sum(math.isclose(a,b,rel_tol=0,abs_tol=1e-6) for _,a,b in overlap)
        agrees=len(overlap)>=30 and matches==len(overlap)
        hardware_verified=model in ("A100_40GB","T4")
        first=points[0]["date"] if points else None;last=points[-1]["date"] if points else None
        span=(date.fromisoformat(last)-date.fromisoformat(first)).days+1 if points else 0
        private_curves[sid]=points
        candidates.append({"series_id":sid,"source_id":"afhubbard","gpu_model":model.replace("_"," "),"instrument_class":"hyperscaler_spot","pricing_tier":"spot","statistic":"median_usd_per_gpu_hour","unit":"USD per GPU-hour","first_date":first,"last_date":last,"observations":len(points),"missing_calendar_days":span-len(points),"overlap_days":len(overlap),"matching_days":matches,"max_absolute_difference":max((abs(a-b) for _,a,b in overlap),default=None),"overlap_agreement":agrees,"hardware_mapping_verified":hardware_verified,"eligible_for_separate_licensed_publication":bool(agrees and hardware_verified),"publication_status":"candidate_only_not_yet_published","points_sha256":hashlib.sha256(json.dumps(points,sort_keys=True,allow_nan=False).encode()).hexdigest()})
    source={"dataset":"Alex Hubbard GPU Price Tracker","dataset_url":"https://github.com/alex-hubbard/gpu_price_tracker","license":"CC BY 4.0","license_url":"https://creativecommons.org/licenses/by/4.0/","license_evidence_url":LICENSE_URL,"license_sha256":hashlib.sha256(license_bytes).hexdigest(),"retrieved_at":datetime.now(timezone.utc).isoformat(),"changes":"Independently downloaded pre-cutoff snapshots; quality-ok AWS/Azure/GCP spot GPU listings; price divided by GPU count; daily median. Calendar gaps are not filled.","vintage_caveat":"Current retrieval of recorded pre-cutoff snapshots; not proof of exact historical availability or unchanged provider populations.","benchmark_input_claim":False,"private_pack_values_published":False}
    summary={"schema_version":1,"status":"candidate_audited","run_id":stamp,"source_sha":source_sha,"workflow_run_id":workflow_run,"source":source,"cutoff":CUTOFF,"objects_downloaded":len(objects),"bytes_downloaded":sum(r["bytes"] for r in objects),"post_cutoff_price_objects_downloaded":0,"normalization":{"providers":["aws","azure","gcp"],"market":"spot","quality":"ok","unit":"USD per GPU-hour","aggregation":"median across eligible observations on each UTC date","A100_80GB_caveat":"Raw family/VRAM does not establish SXM interconnect identity; no matched publication without further evidence.","V100_caveat":"VRAM variants are not separated by the headline; no matched publication without further evidence."},"candidates":candidates,"runtime_seconds":time.perf_counter()-started,"public_price_values_included":False}
    atomic(root/"receipts.json",receipts);atomic(root/"candidate-private.json",{"summary":summary,"curves":private_curves});atomic(root/"summary.json",summary);volume.commit();shutil.rmtree(temp);return summary
@app.local_entrypoint()
def main():
    result=inspect.remote(os.environ["GITHUB_SHA"],os.environ["GITHUB_RUN_ID"])
    out=Path("artifacts");out.mkdir(exist_ok=True);(out/"upstream-history-candidate.json").write_text(json.dumps(result,indent=2)+"\n")
    print("UPSTREAM_HISTORY_CANDIDATE:"+json.dumps(result),flush=True)
