"""Append-only capture of explicitly licensed independent source vintages."""
from __future__ import annotations
import hashlib,io,json,math,re,statistics,uuid
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import quote,urlencode
from urllib.request import urlopen
import xml.etree.ElementTree as ET
from .review_v4 import digest,encoded
BASE="https://hubbard-gpu-price-data.s3.amazonaws.com/"
LICENSE="https://raw.githubusercontent.com/alex-hubbard/gpu_price_tracker/ac287bacc95f3b2ceaa97af10a50031ee0abcacf/DATA_LICENSE"
LICENSE_SHA="5935a23bebd1f3add38258ebd4167ad55ca9a001bfb88e32396b36b77152f7cb"
IDS={"A100_40GB":"hubbard-independent-a100-40","T4":"hubbard-independent-t4"}
TARGET={"measurement":"advertised_rental_offer_rate","unit":"USD per GPU-hour","statistic":"daily median of quality-ok AWS/Azure/GCP spot observations; SKU hourly rate / GPU count","composition":"mixed regions and changing provider/configuration population","source_license_sha256":LICENSE_SHA}
def permitted(day):return day<="2026-11-06" or day>="2026-11-14"
def utc(value):
    v=datetime.fromisoformat(value.replace("Z","+00:00"))
    if v.tzinfo is None:raise ValueError("Timezone required")
    return v.astimezone(timezone.utc)
def validate_snapshot(v,now=None):
    now=now or datetime.now(timezone.utc)
    if v["schema_version"]!=4 or v["target_definition"]!=TARGET:raise ValueError("Snapshot target identity")
    if utc(v["retrieved_at"])>now:raise ValueError("Snapshot timestamp is in the future")
    if date.fromisoformat(v["cutoff"])>now.date():raise ValueError("Future source cutoff")
    if v["source"]["license_sha256"]!=LICENSE_SHA:raise ValueError("Unverified permission")
    keys=set()
    for s in v["series"]:
        if s["id"] not in IDS.values() or s["id"] in keys:raise ValueError("Unverified hardware identity")
        keys.add(s["id"]);seen=set()
        for p in s["points"]:
            if p["date"] in seen or p["date"]>v["cutoff"] or not permitted(p["date"]):raise ValueError("Duplicate, later or protected observation")
            if not math.isfinite(float(p["value"])) or p["value"]<=0:raise ValueError("Invalid rate")
            seen.add(p["date"])
    return v
def retain(root,v):
    validate_snapshot(v);root=Path(root);root.mkdir(parents=True,exist_ok=True);identifier=digest(v);path=root/(identifier+".json");raw=encoded(v)
    if path.exists() and path.read_bytes()!=raw:raise ValueError("Immutable vintage changed")
    if not path.exists():
        with path.open("xb") as out:out.write(raw)
    previous=[]
    for p in root.glob("*.json"):
        if p==path or p.name.endswith(".receipt.json"):continue
        old=json.loads(p.read_bytes())
        if old.get("schema_version")==4 and "series" in old:previous.append(old)
    revisions=[]
    if previous:
        old=max(previous,key=lambda x:x["retrieved_at"]);known={(s["id"],p["date"]):p["value"] for s in old["series"] for p in s["points"]}
        for s in v["series"]:
            for p in s["points"]:
                key=(s["id"],p["date"])
                if key in known and known[key]!=p["value"]:revisions.append({"series_id":s["id"],"date":p["date"],"previous":known[key],"new":p["value"]})
    receipt={"schema_version":4,"snapshot_id":identifier,"snapshot_bytes_sha256":hashlib.sha256(raw).hexdigest(),"retrieved_at":v["retrieved_at"],"cutoff":v["cutoff"],"target_definition_sha256":digest(TARGET),"revisions":revisions,"first_observed_vintage_preserved":True}
    receipt_path=root/(identifier+".receipt.json")
    if not receipt_path.exists():
        with receipt_path.open("xb") as out:out.write(encoded(receipt))
    return receipt
def select_snapshot(root,origin,deadline_hours=2):
    bound=utc(origin+"T00:00:00+00:00")+timedelta(hours=deadline_hours);cutoff=(date.fromisoformat(origin)-timedelta(days=1)).isoformat();candidates=[]
    for p in Path(root).glob("*.json"):
        if p.name.endswith(".receipt.json"):continue
        v=json.loads(p.read_bytes())
        if "series" in v and utc(v["retrieved_at"])<=bound and v["cutoff"]<=cutoff:candidates.append((v,p))
    if not candidates:return None
    v,p=max(candidates,key=lambda x:(x[0]["cutoff"],x[0]["retrieved_at"]));validate_snapshot(v)
    return {"snapshot_id":digest(v),"path":str(p),"value":v}
def seed_context(payload,root):
    h=payload["history_context"];now=datetime.now(timezone.utc).isoformat()
    v={"schema_version":4,"retrieved_at":now,"cutoff":h["cutoff"],"target_definition":TARGET,"source":h["source"],"kind":"Retained existing licensed context; current retention does not backdate collection","series":[{"id":s["id"],"gpu_model":s["gpu_model"],"points":s["points"],"auxiliary":{},"auxiliary_status":"No source offer identities in the published context"} for s in h["series"]],"source_objects":[],"quote_verification_age":None}
    return retain(root,v)
def fetch(url,limit):
    with urlopen(url,timeout=60) as response:
        raw=response.read(limit+1);headers=dict(response.headers)
    if len(raw)>limit:raise ValueError("Source size limit")
    return raw,headers
def list_objects(cutoff):
    rows=[];token=None;ns={"s":"http://s3.amazonaws.com/doc/2006-03-01/"}
    for _ in range(8):
        params={"list-type":"2","prefix":"prices/","max-keys":"1000"}
        if token:params["continuation-token"]=token
        raw,_=fetch(BASE+"?"+urlencode(params),2_000_000);root=ET.fromstring(raw)
        for item in root.findall("s:Contents",ns):
            key=item.findtext("s:Key",namespaces=ns) or "";match=re.search(r"/dt=(\d{4}-\d{2}-\d{2})/",key)
            if match and key.endswith(".parquet") and "2026-01-01"<=match[1]<=cutoff and permitted(match[1]):
                rows.append({"key":key,"partition_date":match[1],"etag":item.findtext("s:ETag",namespaces=ns),"last_modified":item.findtext("s:LastModified",namespaces=ns),"bytes":int(item.findtext("s:Size",namespaces=ns))})
        token=root.findtext("s:NextContinuationToken",namespaces=ns)
        if not token:break
    else:raise ValueError("Source listing limit")
    if not rows or len(rows)>750 or sum(r["bytes"] for r in rows)>300_000_000:raise ValueError("Source object budget")
    return sorted(rows,key=lambda r:r["key"])
def capture(root,cutoff):
    if cutoff>datetime.now(timezone.utc).date().isoformat():raise ValueError("Future source request")
    license_raw,_=fetch(LICENSE,100_000)
    if hashlib.sha256(license_raw).hexdigest()!=LICENSE_SHA:raise ValueError("Data license changed")
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq
    frames=[];receipts=[];raw_root=Path(root)/"source-objects";raw_root.mkdir(parents=True,exist_ok=True)
    for item in list_objects(cutoff):
        if not permitted(item["partition_date"]):raise ValueError("Protected source partition")
        url=BASE+quote(item["key"],safe="/=");raw,headers=fetch(url,min(item["bytes"]+1024,30_000_000))
        if len(raw)!=item["bytes"]:raise ValueError("Source revision during listing")
        sha=hashlib.sha256(raw).hexdigest();saved=raw_root/(sha+".parquet")
        if not saved.exists():
            with saved.open("xb") as out:out.write(raw)
        frame=pq.read_table(io.BytesIO(raw)).to_pandas()
        required={"timestamp","provider","gpu_type","gpu_count","gpu_memory_gb","price_per_hour","is_spot","quality"}
        if not required<=set(frame):raise ValueError("Source schema missing "+str(sorted(required-set(frame))))
        times=pd.to_datetime(frame["timestamp"],utc=True);days=times.dt.strftime("%Y-%m-%d")
        if any(d>cutoff or not permitted(d) for d in days):raise ValueError("Unexpected later/protected content; source object not used")
        mask=frame["provider"].astype(str).str.lower().isin(["aws","azure","gcp"])&frame["is_spot"].fillna(False).astype(bool)&frame["quality"].astype(str).eq("ok")
        frame=frame[mask].copy();frame["day"]=days[mask];frame["captured"]=times[mask]
        family=frame["gpu_type"].astype(str).str.upper();memory=pd.to_numeric(frame["gpu_memory_gb"],errors="coerce")
        frame["model"]=np.select([family.str.contains("A100")&memory.eq(40),family.str.contains(r"\bT4\b")&memory.eq(16)],["A100_40GB","T4"],default="")
        frame["value"]=pd.to_numeric(frame["price_per_hour"],errors="coerce")/pd.to_numeric(frame["gpu_count"],errors="coerce")
        frame=frame[(frame["model"]!="")&np.isfinite(frame["value"])&(frame["value"]>0)]
        frames.append(frame);receipts.append({**item,"sha256":sha,"url":url,"response_etag":headers.get("ETag")})
    rows=pd.concat(frames,ignore_index=True);series=[]
    for model,sid in IDS.items():
        group=rows[rows["model"]==model].copy()
        if group.empty:continue
        curve=group.groupby("day")["value"].median()
        points=[{"date":d,"value":float(v)} for d,v in curve.items()]
        aux={};sku=next((c for c in ("instance_type","sku","name") if c in group),None);region=next((c for c in ("region","region_name","location") if c in group),None)
        if sku and region and group[[sku,region]].notna().all().all():
            identity=["provider",sku,region,"gpu_count","gpu_memory_gb"]
            group["key"]=group[identity].astype(str).agg("|".join,axis=1)
            group=group.sort_values("captured").drop_duplicates(["day","key"],keep="last")
            first=min(group["day"]);end=(date.fromisoformat(first)+timedelta(days=6)).isoformat()
            anchor=group[group["day"]<=end].groupby("key")["value"].median()
            raw_panel={};basket={}
            for d,g in group.groupby("day"):
                if d<end:continue
                prices=g.set_index("key")["value"];matched=prices.reindex(anchor.index);coverage=float(matched.notna().mean());shares=g.groupby("provider").size()/len(g)
                common={"coverage":coverage,"log_configs":math.log1p(len(g)),"provider_hhi":float((shares**2).sum())}
                raw_panel[d]={**common,"log_index":math.log(float(prices.median()))}
                basket[d]={**common,"log_index":float(np.log(matched/anchor).mean()) if coverage==1 else None}
            for panel in (raw_panel,basket):
                for d,row in panel.items():
                    for lag in (1,3,7):
                        prev=panel.get((date.fromisoformat(d)-timedelta(days=lag)).isoformat(),{}).get("log_index")
                        row["change_"+str(lag)]=row["log_index"]-prev if row["log_index"] is not None and prev is not None else None
            aux={"raw":raw_panel,"fixed_basket":basket}
        series.append({"id":sid,"gpu_model":model,"points":points,"auxiliary":aux,"auxiliary_status":"verified source identities" if aux else "unsupported source identity; explicit numerical fallbacks will be reported"})
    v={"schema_version":4,"retrieved_at":datetime.now(timezone.utc).isoformat(),"cutoff":cutoff,"target_definition":TARGET,"source":{"dataset_url":"https://github.com/alex-hubbard/gpu_price_tracker","license":"CC BY 4.0","license_url":"https://creativecommons.org/licenses/by/4.0/","license_sha256":LICENSE_SHA,"license_evidence_url":LICENSE,"changes":"Independent retrieval; quality-ok hyperscaler spot filtering, rate/GPU normalization, UTC medians; no gap filling"},"series":series,"source_objects":receipts,"quote_verification_age":None}
    return retain(root,v)
