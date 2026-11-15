"""Audit pre-cutoff history metadata privately; never export historical price values."""
from __future__ import annotations
import hashlib,json,os,shutil,time
from datetime import datetime,timezone
from pathlib import Path
import modal
from .starter_probe import image,volume,PACK_SHA256
from .campaign_v2 import unpack,build_history
app=modal.App("compute-forecast-history-audit-v3")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
def write_atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+".pending")
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n");tmp.replace(path)
@app.function(image=image,cpu=2,memory=4096,timeout=900,volumes={"/data":volume,"/public":public})
def inspect():
    started=time.perf_counter();temp,root=unpack();work=temp/"audit-work";work.mkdir()
    hist,cat=build_history(root,work,"2026-11-06")
    headlines=cat[cat["tier"]=="headline"].copy()
    if len(headlines)!=37:raise ValueError("Unexpected headline catalog")
    license_files=[];private_texts={}
    for path in root.rglob("*"):
        if not path.is_file() or path.stat().st_size>100000:continue
        if not any(k in path.name.lower() for k in ("licen","readme","provenance","sources")):continue
        if path.suffix.lower() not in (".md",".txt",".json",".csv",""):continue
        raw=path.read_bytes()
        try:text=raw.decode()
        except UnicodeDecodeError:continue
        rel=path.relative_to(root).as_posix();private_texts[rel]=text;low=text.lower()
        license_files.append({"path":rel,"sha256":hashlib.sha256(raw).hexdigest(),"mentions_cc_by":"cc by" in low or "cc-by" in low,"mentions_pending":"pending" in low,"mentions_upstream":"upstream" in low,"mentions_redistribution":"redistribut" in low,"bytes":len(raw)})
    rows=[]
    fields=("series_id","source_id","table","instrument_class","gpu_model","pricing_tier","statistic","instance_type","az_global_id","product_description","source_url","licence_id")
    for item in headlines.to_dict("records"):
        sid=item["series_id"];rr=hist[hist["series_id"]==sid].sort_values("day")
        days=rr["day"].tolist();valid=rr["value"].notna()
        first=min(days).isoformat() if days else None;last=max(days).isoformat() if days else None
        span=(max(days)-min(days)).days+1 if days else 0
        rows.append({**{k:str(item.get(k,"")) for k in fields},"history_rows":len(rr),"nonmissing_values":int(valid.sum()),"first_date":first,"last_date":last,"calendar_span_days":span,"missing_calendar_days":span-len(set(days)),"duplicate_date_rows":len(days)-len(set(days)),"frequency":"daily" if item["table"]=="daily_statistics" else "snapshot/other; inspect source","currency":"USD","unit":"USD per GPU-hour" if item["statistic"]=="median_usd_per_gpu_hour" else "unverified","collection_vintage":"Frozen gpu-price-pack v0.1.1-handover; row dates do not establish live historical availability","revision_status":"No original-versus-revised vintage history verified","region_definition":str(item.get("az_global_id","")) or "not supplied in the headline catalog","provider_population":"Source-level population; provider membership stability is not established","history_publication_permitted":False,"publication_status":"blocked_pending_explicit_compilation_and_upstream_permission"})
    result={"schema_version":1,"audited_at":datetime.now(timezone.utc).isoformat(),"code_sha":os.environ.get("GITHUB_SHA"),"dataset_sha256":PACK_SHA256,"cutoff":"2026-11-06","future_competition_truth_loaded":False,"raw_history_values_included":False,"catalog_sha256":hashlib.sha256((work/"catalog.csv").read_bytes()).hexdigest(),"series":rows,"license_file_metadata":license_files,"upstream_review_status":"Separate linked public-terms review required; metadata license labels are not a publication grant","runtime_seconds":time.perf_counter()-started}
    stamp=os.environ.get("GITHUB_RUN_ID","manual")
    write_atomic(Path("/data/phase3-history")/(stamp+"-license-texts.json"),private_texts)
    write_atomic(Path("/data/phase3-history")/(stamp+"-audit.json"),result);volume.commit()
    public.reload();write_atomic(Path("/public/phase3/history-audit.json"),result);public.commit()
    shutil.rmtree(temp);return result
@app.local_entrypoint()
def main():
    value=inspect.remote();out=Path("artifacts");out.mkdir(exist_ok=True)
    (out/"history-audit-v3.json").write_text(json.dumps(value,indent=2)+"\n")
    print("HISTORY_AUDIT_V3:"+json.dumps(value),flush=True)
