"""Separate, bounded prospective aggregate panel. No historical-study gate is changed."""
from __future__ import annotations
import hashlib,io,json,os,statistics,tempfile
from pathlib import Path
from datetime import datetime,date,timedelta,timezone
from urllib.parse import urlencode,quote
from urllib.request import Request,urlopen
import xml.etree.ElementTree as ET
import modal
from .price_dynamics_v8 import digest,pooled,replay,calibrate,loss,validate_commitment
from .price_dynamics_remote_v8 import data,public,put,encoded
from .starter_probe import PACK_NAME
from .pacific_value_v5 import invoke,write_csv,rows
app=modal.App("compute-forecast-price-dynamics-future-v8")
image=(modal.Image.debian_slim(python_version="3.11").pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","pyarrow>=16,<24").env({"GITHUB_SHA":os.environ.get("GITHUB_SHA","unknown")}).add_local_file("configs/price-dynamics-v8-future.json","/root/configs/price-dynamics-v8-future.json",copy=True).add_local_python_source("compute_forecast"))
BASE="https://hubbard-gpu-price-data.s3.amazonaws.com/"
LICENSE="https://raw.githubusercontent.com/alex-hubbard/gpu_price_tracker/ac287bacc95f3b2ceaa97af10a50031ee0abcacf/DATA_LICENSE"
ROOT=Path("/data/price-dynamics-v8/future")
def now():return datetime.now(timezone.utc)
def request(url):
    with urlopen(Request(url,headers={"User-Agent":"ComputeForecastResearch/1.0"}),timeout=35) as r:
        raw=r.read(30_000_001)
        if len(raw)>30_000_000:raise ValueError("Object byte cap")
        return raw
def capture(at):
    import pandas as pd,pyarrow.parquet as pq
    licence=request(LICENSE)
    if b"CC BY 4.0" not in licence or b"s3://hubbard-gpu-price-data/prices/" not in licence:raise ValueError("Source permission not verified")
    ns={"s":"http://s3.amazonaws.com/doc/2006-03-01/"};token=None;objects=[];latest=None;pages=0;truncated=False
    import re
    for _ in range(10):
        params={"list-type":"2","prefix":"prices/","max-keys":"1000"}
        if token:params["continuation-token"]=token
        xml=ET.fromstring(request(BASE+"?"+urlencode(params)));pages+=1
        for item in xml.findall("s:Contents",ns):
            key=item.findtext("s:Key",namespaces=ns);m=re.search(r"/dt=(\d{4}-\d{2}-\d{2})/",key or "")
            if not m or not key.endswith(".parquet"):continue
            d=m.group(1);latest=max(latest or d,d)
            if "2026-11-16"<=d<at.date().isoformat():
                objects.append({"key":key,"day":d,"etag":item.findtext("s:ETag",namespaces=ns),"size":int(item.findtext("s:Size",namespaces=ns))})
        token=xml.findtext("s:NextContinuationToken",namespaces=ns)
        if not token:break
    else:truncated=True
    # Strictly no protected Nov7–13 object is downloaded.
    downloaded=[];snapshots=[];byte_count=0
    for obj in sorted(objects,key=lambda o:o["key"])[-50:]:
        if byte_count+obj["size"]>60_000_000:break
        raw=request(BASE+quote(obj["key"],safe="/="));byte_count+=len(raw);sha=hashlib.sha256(raw).hexdigest()
        rawpath=ROOT/"objects"/(sha+".parquet");rawpath.parent.mkdir(parents=True,exist_ok=True)
        if not rawpath.exists():
            if sum(p.stat().st_size for p in ROOT.rglob("*") if p.is_file())+len(raw)>150_000_000:raise ValueError("Registered private storage budget reached")
            rawpath.write_bytes(raw)
        frame=pq.read_table(io.BytesIO(raw)).to_pandas()
        required={"timestamp","provider","gpu_type","gpu_count","gpu_memory_gb","price_per_hour","is_spot"}
        if not required<=set(frame):raise ValueError("Upstream target schema changed")
        timestamps=pd.to_datetime(frame["timestamp"],utc=True)
        if any(t.date().isoformat()!=obj["day"] or t>at for t in timestamps):raise ValueError("Object date/availability mismatch")
        mask=frame["provider"].astype(str).str.lower().isin(["aws","azure","gcp"])&frame["is_spot"].fillna(False).astype(bool)
        if "quality" in frame:mask&=frame["quality"].astype(str).eq("ok")
        frame=frame[mask].copy()
        frame["rate"]=pd.to_numeric(frame["price_per_hour"],errors="coerce")/pd.to_numeric(frame["gpu_count"],errors="coerce")
        frame=frame[frame["rate"].gt(0)&frame["rate"].lt(10000)]
        groups={}
        for _,r in frame.iterrows():
            gpu=str(r["gpu_type"]).upper();memory=float(r["gpu_memory_gb"])
            model="A100_40GB" if "A100" in gpu and memory==40 else "A100_80GB_unspecified_form" if "A100" in gpu and memory==80 else "H100_80GB_unspecified_form" if "H100" in gpu and memory==80 else None
            if not model:continue
            groups.setdefault("v8.hubbard.hyperscaler_spot."+model+".spot.median",[]).append(float(r["rate"]))
        for sid,values in groups.items():
            snapshots.append({"series_id":sid,"observation_date":obj["day"],"value":round(statistics.median(values),4),"n_rows":len(values),"object_sha256":sha,"first_observed_at":at.isoformat(),"source_url":BASE+quote(obj["key"],safe="/="),"unit":"USD per GPU-hour","contract":"Observed AWS/Azure/GCP spot offers; all observed regions; specified memory, form factor unspecified; not a competition series"})
        downloaded.append({"key":obj["key"],"sha256":sha,"bytes":len(raw)})
    # Multiple source objects in one day cannot be averaged into an invented median.
    # Group manifests are retained; ambiguous split collections gate that day.
    by={}
    for s in snapshots:by.setdefault((s["series_id"],s["observation_date"]),[]).append(s)
    accepted=[];ambiguous=[]
    for key,ss in by.items():
        if len(ss)!=1:ambiguous.append({"series_id":key[0],"date":key[1],"objects":len(ss),"reason":"multiple source objects need an audited union adapter"});continue
        s=ss[0];vintage=ROOT/"vintages"/s["series_id"]/s["observation_date"]
        put(vintage/(digest(s)+".json"),s)
        first=vintage/"first.json"
        if not first.exists():put(first,s)
        accepted.append(s)
    result={"captured_at":at.isoformat(),"source_last_partition":latest,"new_source_start":"2026-11-16","listing_pages":pages,"listing_truncated":truncated,"objects_downloaded":downloaded,"retained_observations":len(accepted),"ambiguous_days":ambiguous,"license_url":LICENSE,"license_sha256":hashlib.sha256(licence).hexdigest(),"fresh_compatible_prices":bool(accepted),"protected_outcomes_downloaded":False}
    put(ROOT/"captures"/(digest(result)+".json"),result);return result
def observations():
    values={}
    for f in sorted((ROOT/"vintages").glob("*/*/first.json")):
        r=json.loads(f.read_bytes());values.setdefault(r["series_id"],{})[r["observation_date"]]=r["value"]
    return values
def native(panels,origin):
    out=Path(tempfile.mkdtemp(prefix="v8-future-native-"));root=Path("/data/pacific")/PACK_NAME
    history=[{"series_id":sid,"date":d,"value":v} for sid,vs in panels.items() for d,v in vs.items() if d<=origin]
    write_csv(out/"history.csv",history,["series_id","date","value"]);result={}
    invoke(root,out,"native",["baselines.py","--history",out/"history.csv","--origin",origin,"--method","drift","--series-ids",",".join(panels),"--horizons","1,3,7","--frozen","--out",out/"drift.csv"])
    for r in rows(out/"drift.csv"):result[(r["series_id"],int(r["horizon_days"]))]=[float(r[k]) for k in ("q10","q50","q90")]
    return result
def issue(at):
    # Daily shadow commitments supply genuinely issued calibration histories.
    # Sunday origins alone comprise the registered primary evaluation panel.
    origin=(at.date()-timedelta(days=1)).isoformat();cutoff=datetime.fromisoformat(origin+"T23:59:59+00:00");deadline=cutoff+timedelta(minutes=30,seconds=1)
    if not cutoff<=at<=deadline:return {"status":"outside_issuance_window"}
    if not "2026-11-22"<=origin<="2027-03-28":return {"status":"outside_registered_origins"}
    vs=observations()
    if len(vs)<3 or any(origin not in x or len(x)<56 for x in vs.values()):return {"status":"pending_56_fresh_retained_days","origins_issued":0,"retained_days":{s:len(x) for s,x in vs.items()}}
    existing=ROOT/"commitments"/(origin+".json")
    if existing.exists():return {"status":"already_committed","commitment_sha256":digest(json.loads(existing.read_bytes()))}
    panels={sid:{"meta":{"series_id":sid,"source_id":"hubbard_v8_independent","instrument_class":"hyperscaler_spot","pricing_tier":"spot","family":"H100" if "H100" in sid else "A100","unit":"USD per GPU-hour"},"values":{d:v for d,v in x.items() if d<=origin}} for sid,x in vs.items()}
    refs=native({s:x["values"] for s,x in panels.items()},origin);prior=[]
    for path in sorted((ROOT/"commitments").glob("*.json")):
        c=json.loads(path.read_bytes())
        for r in c["forecasts"]:
            if r["target"]<=origin and r["target"] in vs.get(r["series_id"],{}):
                prior.append({**r,"truth":vs[r["series_id"]][r["target"]]})
    forecasts=[]
    for sid,x in panels.items():
        for h in (1,3,7):
            a=refs[(sid,h)];c,cd=pooled(x["values"],x["meta"],panels,origin,h,a)
            base={"A":(a,{}),"C":(c,cd),"E":(a,{"fallback":"aggregate_offer_union_and_identity_not_verified"})}
            allarms=dict(base)
            for raw,cal in (("A","B"),("C","D"),("E","F")):
                past=[r for r in prior if r["method"]==raw and r["series_id"]==sid and r["horizon"]==h]
                allarms[cal]=calibrate(base[raw][0],past,origin,h)
            target=(date.fromisoformat(origin)+timedelta(days=h)).isoformat()
            for m,(q,diag) in allarms.items():forecasts.append({"method":m,"series_id":sid,"origin":origin,"target":target,"horizon":h,"resolution_at":(date.fromisoformat(target)+timedelta(days=1)).isoformat()+"T00:00:00+00:00","quantiles":q,"diagnostic":diag})
    commit={"study_id":"price-dynamics-v8-future","kind":"primary_weekly" if date.fromisoformat(origin).weekday()==6 else "calibration_shadow","origin":origin,"cutoff":cutoff.isoformat(),"issued_at":at.isoformat(),"deadline":deadline.isoformat(),"snapshot_sha256":digest(panels),"configuration_sha256":digest({"protocol":hashlib.sha256(Path("configs/price-dynamics-v8-future.json").read_bytes()).hexdigest(),"engine":hashlib.sha256(Path(__file__).with_name("price_dynamics_v8.py").read_bytes()).hexdigest()}),"source_sha":os.environ.get("GITHUB_SHA"),"forecasts":forecasts}
    validate_commitment(commit,at);put(existing,commit)
    return {"status":"issued","commitment_sha256":digest(commit),"rows":len(forecasts),"resolution_dates":sorted({r["target"] for r in forecasts})}
def evaluate(at):
    vs=observations();scored=[];pending=0
    for f in sorted((ROOT/"commitments").glob("*.json")):
        c=json.loads(f.read_bytes());validate_commitment(c,at)
        if c["kind"]!="primary_weekly":continue
        for r in c["forecasts"]:
            if datetime.fromisoformat(r["resolution_at"])>at or r["target"] not in vs.get(r["series_id"],{}):pending+=1;continue
            truth=vs[r["series_id"]][r["target"]]
            scored.append({**r,"truth":truth,"loss":loss(r["quantiles"],truth),"commitment_sha256":digest(c)})
    return {"scored":scored,"pending_cells":pending,"analysis_at":"2027-04-06T00:00:00+00:00","accuracy_established":False,"interpretation":"No promotion before fixed analysis; compatible matured observations required"}
@app.function(image=image,cpu=2,memory=4096,timeout=900,max_containers=1,volumes={"/data":data,"/public":public},schedule=modal.Cron("5 0 * * *"))
def tick():
    at=now()
    if at>=datetime(2027,4,7,tzinfo=timezone.utc):return {"status":"scheduled_capture_ended","external_requests":0}
    ROOT.mkdir(parents=True,exist_ok=True)
    try:cap=capture(at) if at<datetime(2027,4,6,tzinfo=timezone.utc) else {"status":"capture_window_closed","fresh_compatible_prices":False}
    except Exception as e:cap={"captured_at":at.isoformat(),"status":"capture_failed","error":type(e).__name__,"detail":str(e)[:300],"fresh_compatible_prices":False}
    issuance=issue(now());evaluation=evaluate(now())
    result={"schema_version":8,"study_id":"price-dynamics-v8-future","created_at":at.isoformat(),"status":issuance["status"] if cap.get("fresh_compatible_prices") else "pending_fresh_compatible_aggregate_capture","capture":cap,"issuance":issuance,"evaluation":evaluation,"forecast_commitments":len(list((ROOT/"commitments").glob("*.json"))),"accuracy_established":False}
    data.commit();dest=Path("/public/price-dynamics-v8");dest.mkdir(parents=True,exist_ok=True)
    put(dest/"future-artifacts"/(digest(result)+".json"),result)
    tmp=dest/"future.pending";tmp.write_bytes(encoded(result));tmp.replace(dest/"future.json");public.commit()
    return result
def main():
    with app.run():r=tick.remote()
    out=Path("artifacts/price-dynamics-v8-operations");out.mkdir(parents=True,exist_ok=True)
    put(out/"future.json",r);print("V8_FUTURE:"+json.dumps(r),flush=True)
if __name__=="__main__":main()
