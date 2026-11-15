"""Current-only source audit; no historical price archive or protected truth download."""
import csv,hashlib,io,json,urllib.request
from datetime import datetime,timezone
from pathlib import Path
def main():
    report={"checked_at":datetime.now(timezone.utc).isoformat(),"sources":[],"protected_outcomes_loaded":False}
    urls=["https://gpurentalprices.com/api/latest.json","https://gpurentalprices.com/api/health.json","https://gpurentalprices.com/gpu-prices.csv","https://api.bls.gov/publicAPI/v2/timeseries/data/PCU221122221122"]
    for url in urls:
        item={"url":url}
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"ComputeForecastResearch/1.0"}),timeout=45) as r:raw=r.read(3_000_000);item.update(status=r.status,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
            if url.endswith(".csv"):
                rows=list(csv.DictReader(io.StringIO(raw.decode())));selected=[r for r in rows if any(x in r.get("gpu","").lower() for x in ("a100","h100"))]
                item.update(columns=list(rows[0]) if rows else [],rows=len(rows),examples=selected[:12])
            else:
                value=json.loads(raw);item["top_keys"]=list(value) if isinstance(value,dict) else "list";item["preview"]=str(value)[:1800]
                if "latest.json" in url:
                    for key,v in value.items():
                        if isinstance(v,list):item.setdefault("arrays",{})[key]={"rows":len(v),"first":v[:2]}
                if "bls.gov" in url:item["value"]=value
        except Exception as e:item.update(status="failed",error_type=type(e).__name__,detail=str(e)[:300])
        report["sources"].append(item)
    out=Path("artifacts/signals-source-audit-v6");out.mkdir(parents=True,exist_ok=True);(out/"audit.json").write_text(json.dumps(report,indent=2)+"\n")
    print("SIGNALS_V6_SOURCE_AUDIT:"+json.dumps(report),flush=True)
if __name__=="__main__":main()
