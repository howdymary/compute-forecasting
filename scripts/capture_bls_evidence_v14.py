"""Original BLS PDF-vintage extraction through Exa; no current-series backfill."""
import calendar,hashlib,json,os,pathlib,re,urllib.request
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from compute_forecast.direct_forecast_v12 import digest
def period_shift(period,n):
    year,month=map(int,period.split("-"));count=year*12+month-1+n
    return f"{count//12:04d}-{count%12+1:02d}"
def extract(text,period,independent=None):
    flat=re.sub(r"\s+"," ",text.replace("|"," "))
    pattern=r"\b221122\s+12/03\s+((?:(?:\d+\.\d+|[–—-])\s+){4}(?:\d+\.\d+|[–—-]))"
    matches=list(re.finditer(pattern,flat));unique={m.group(1) for m in matches}
    if len(unique)!=1:raise ValueError("Exact221122/12-03 five-column row missing or ambiguous")
    match=matches[0];tokens=match.group(1).split();values=[None if v in ("–","—","-") else float(v) for v in tokens]
    months=[period_shift(period,n) for n in (-4,-3,-2,-1,0)]
    header=flat[max(0,match.start()-16000):match.start()]
    # Exa may omit the repeated "Unadjusted index" label while preserving the
    # five ordered month/year captions. Verify the actual captions and industry.
    captions=[]
    for item in months:
        year,month=map(int,item.split("-"))
        captions.append(calendar.month_abbr[month]+r"[a-z]*\.?\s+"+str(year)+r"(?:\s*p)?")
    verified=re.search(r"\s+".join(captions),header,re.I)
    if not verified:
        if not independent or independent["periods"]!=months or independent["indices"]!=values:
            raise ValueError("Ordered five-month captions not verified")
    if "Electric power distribution" not in flat[max(0,match.start()-400):match.start()]:
        raise ValueError("Exact industry title missing")
    for item in months:
        year,month=map(int,item.split("-"))
        name=calendar.month_abbr[month]
        if name.lower() not in header.lower() or str(year) not in header:raise ValueError("Column month not verified: "+item)
    if values[-1] is None or values[-2] is None:raise ValueError("Latest or previous month missing")
    return {"periods":months,"indices":values,"source_row":match.group(0),"source_row_sha256":hashlib.sha256(match.group(0).encode()).hexdigest(),"header_context_sha256":hashlib.sha256(header.encode()).hexdigest(),"verified_column_caption":verified.group(0) if verified else independent["verified_caption"],"extraction":"Exactindustry221122/base12-03; five monthly index columns; excludes221122-P/products and percent-change table"}
def main():
    cfg=json.loads(pathlib.Path("configs/evidence-v14-bls-sources.json").read_text())
    out=pathlib.Path("artifacts/evidence-v14-audit");out.mkdir(parents=True,exist_ok=True);records=[];usage=[]
    previous={}
    prior_url="https://raw.githubusercontent.com/howdymary/mochi-demo/compute-observatory/results/evidence-v14/audits/43966106373/bls-vintages.json"
    with urllib.request.urlopen(prior_url,timeout=30) as response:
        prior=json.load(response);previous={r["reference_period"]:r for r in prior["records"] if r["status"]=="qualified_pending_spot_check"}
    for spec in cfg["vintages"]:
        if spec["period"] in previous:
            kept=previous[spec["period"]];kept["reused_from_artifact"]=prior_url;records.append(kept);continue

        year,month=map(int,spec["period"].split("-"));url=f"https://www.bls.gov/ppi/detailed-report/ppi-detailed-report-{calendar.month_name[month].lower()}-{year}.pdf"
        at=datetime.now(timezone.utc).isoformat();record={"source_url":url,"publisher":"US Bureau of Labor Statistics","series_id":cfg["series_id"],"reference_period":spec["period"],"retrieved_at":at,"first_observed_at":at,"permission_url":cfg["permission_url"],"acquisition":cfg["acquisition"]}
        release=datetime.fromisoformat(spec["release_date"]+"T"+spec["release_time"]).replace(tzinfo=ZoneInfo(spec["release_timezone"])).astimezone(timezone.utc).isoformat();record["available_at"]=release
        try:
            body=json.dumps({"urls":[url],"text":{"maxCharacters":cfg["limits"]["max_characters_per_pdf"]}}).encode()
            req=urllib.request.Request("https://api.exa.ai/contents",data=body,headers={"Content-Type":"application/json","x-api-key":os.environ["EXA_API_KEY"]})
            with urllib.request.urlopen(req,timeout=cfg["limits"]["http_timeout_seconds"]) as response:reply=json.load(response)
            result=next(r for r in reply.get("results",[]) if r.get("text"));text=result["text"]
            record.update(content_sha256=hashlib.sha256(text.encode()).hexdigest(),characters=len(text),exa_request_id=reply.get("requestId"),cost_dollars=reply.get("costDollars"),values=extract(text,spec["period"],cfg.get("independent_pdf_checks",{}).get(spec["period"])),status="qualified_pending_spot_check")
            # Only the exact public index row, headers hashes and original source identity are published.
            usage.append({"request_id":reply.get("requestId"),"cost_dollars":reply.get("costDollars")})
        except Exception as e:record.update(status="unavailable",error_type=type(e).__name__,error_message=str(e)[:180].replace(os.environ["EXA_API_KEY"],"[redacted]"))
        records.append(record);print(json.dumps({k:v for k,v in record.items() if k not in ("values",)}),flush=True)
        (out/"bls-vintages.json").write_text(json.dumps({"study_id":"direct-evidence-v14","created_at":datetime.now(timezone.utc).isoformat(),"config_sha256":digest(cfg),"records":records,"usage":usage,"source_sha":os.environ["GITHUB_SHA"],"historical_contents_basis":"Original immutable monthly government reports; publication dates are not inferred from retrieval dates","ready":len(records)==len(cfg["vintages"]) and all(r["status"]=="qualified_pending_spot_check" for r in records)},indent=2)+"\n")
if __name__=="__main__":main()
