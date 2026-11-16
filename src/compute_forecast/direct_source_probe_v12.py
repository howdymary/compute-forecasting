"""Test archived BLS access through Modal egress; no GPU-market outcomes."""
import csv,hashlib,io,json,pathlib,urllib.request
from datetime import datetime,timezone
import modal
app=modal.App("compute-forecast-direct-v12-source-probe")
@app.function(image=modal.Image.debian_slim(python_version="3.11"),cpu=1,memory=512,timeout=70)
def probe():
    rows=[]
    for origin in ("2026-02-01","2026-07-01","2026-09-12"):
        url="https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=PCU221122221122&vintage_date="+origin+"&cosd=2025-01-01"
        r={"origin":origin,"url":url,"retrieved_at":datetime.now(timezone.utc).isoformat(),"egress":"Modal"}
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"ComputeForecastResearch/1.0"}),timeout=12) as response:
                raw=response.read(1000001)
                if len(raw)>1000000:raise ValueError("Byte budget exceeded")
                r.update(http_status=response.status,sha256=hashlib.sha256(raw).hexdigest(),content_type=response.headers.get("Content-Type"))
            table=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
            r["columns"]=list(table[0]) if table else []
            r["vintage_verified"]="PCU221122221122_"+origin.replace("-","") in r["columns"]
            r["rows"]=len(table)
        except Exception as e:r.update(error_type=type(e).__name__,error_message=str(e)[:160],vintage_verified=False)
        rows.append(r)
    return {"study_id":"direct-v12-supplementary-egress-diagnostic","created_at":datetime.now(timezone.utc).isoformat(),"results":rows,"evidence_training_ready":False,"new_optimizer_updates":0,"protected_market_outcomes_requested":False,"provider_cost_usd":None}
@app.local_entrypoint()
def main():
    result=probe.remote();out=pathlib.Path("artifacts/direct-v12-diagnostics");out.mkdir(parents=True,exist_ok=True);(out/"source-access.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result),flush=True)
