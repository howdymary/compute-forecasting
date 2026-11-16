"""Bounded primary-source probe after an ALFRED bulk collection timed out."""
import csv,hashlib,io,json,pathlib,urllib.request
from datetime import datetime,timezone
results=[]
for origin in ("2026-02-01","2026-07-01","2026-09-12"):
    url="https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=PCU221122221122&vintage_date="+origin+"&cosd=2025-01-01"
    row={"origin":origin,"url":url,"retrieved_at":datetime.now(timezone.utc).isoformat()}
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"ComputeForecastResearch/1.0"})
        with urllib.request.urlopen(req,timeout=12) as response:
            raw=response.read(1000001)
            if len(raw)>1000000:raise ValueError("Response byte budget exceeded")
            row.update(status=response.status,content_type=response.headers.get("Content-Type"),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
        table=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        row["columns"]=list(table[0]) if table else []
        row["vintage_verified"]="PCU221122221122_"+origin.replace("-","") in row["columns"]
    except Exception as e:row.update(error_type=type(e).__name__,error_message=str(e)[:160],vintage_verified=False)
    results.append(row);print(json.dumps(row),flush=True)
out=pathlib.Path("artifacts/direct-v12-supplementary-probe");out.mkdir(parents=True,exist_ok=True)
(out/"probe.json").write_text(json.dumps({"study_id":"direct-v12-supplementary-audit","results":results,"bulk_capture_status":"Timed out; no qualifying feature table retained","evidence_training_ready":False,"no_market_outcomes_requested":True},indent=2)+"\n")
