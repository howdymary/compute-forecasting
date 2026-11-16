"""Private-pack schema and target audit; no protected outcomes or raw offers exported."""
import json,tempfile
from pathlib import Path
from datetime import datetime,timezone
import modal
from .starter_probe import PACK_NAME,verify_manifest
from .pacific_value_v5 import build_history
app=modal.App("compute-forecast-price-dynamics-audit-v8")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","pyarrow>=16,<24").add_local_python_source("compute_forecast")
@app.function(image=image,cpu=4,memory=8192,timeout=900,volumes={"/data":data})
def audit():
    import duckdb
    root=Path("/data/pacific")/PACK_NAME
    count=verify_manifest(root)
    work=Path(tempfile.mkdtemp())
    hist,cat,_,_=build_history(root,work,"2026-11-06")
    c=duckdb.connect()
    pattern=str(root/"rental_observations"/"*"/"*"/"*.parquet")
    c.execute("CREATE VIEW offers AS SELECT * FROM read_parquet(?,hive_partitioning=false)",[pattern])
    schema=c.execute("DESCRIBE offers").fetchall()
    selected=[r for r in cat if r.get("table")=="daily_statistics" and r.get("statistic")=="median" and r.get("gpu_model","").upper().startswith(("H100","A100"))]
    groups=c.execute("SELECT source_id,instrument_class,gpu_model,pricing_tier,count(*),min(dt),max(dt) FROM offers WHERE CAST(dt AS DATE)<=DATE '2026-11-06' AND usd_per_gpu_hour>0 GROUP BY ALL ORDER BY 1,2,3,4").fetchall()
    snippets={}
    for f in ("DATA.md","starter/build_series.py","starter/baselines.py"):
        lines=(root/f).read_text().splitlines()
        matches=[i for i,line in enumerate(lines) if any(k in line.lower() for k in ("offer_id","dedup","snapshot","daily_statistics","def drift","log_changes","instrument_class"))]
        snippets[f]=[{"line":i+1,"text":"\n".join(lines[max(0,i-2):i+6])} for i in matches[:16]]
    return {"checked_at":datetime.now(timezone.utc).isoformat(),"manifest_members":count,"schema":[list(r) for r in schema],"catalog":selected,"groups":[list(r) for r in groups],"snippets":snippets,"protected_outcomes_loaded":False}
def main():
    with app.run(): result=audit.remote()
    out=Path("artifacts/price-dynamics-v8");out.mkdir(parents=True,exist_ok=True)
    (out/"schema-audit.json").write_text(json.dumps(result,default=str,indent=2))
    print("V8_AUDIT:"+json.dumps(result,default=str),flush=True)
if __name__=="__main__":main()
