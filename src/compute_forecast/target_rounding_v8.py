"""Supplementary target-rounding diagnostic; does not change the frozen v8 arms."""
import csv,json,tempfile
from pathlib import Path
import modal
from .price_dynamics_remote_v8 import image,data,public,put,encoded
from .starter_probe import PACK_NAME
from .price_dynamics_v8 import digest
app=modal.App("compute-forecast-target-rounding-audit-v8")
@app.function(image=image,cpu=2,memory=4096,timeout=180,volumes={"/data":data,"/public":public})
def audit():
    import duckdb,numpy as np
    root=Path("/data/pacific")/PACK_NAME
    targets=list(csv.DictReader((root/"daily_statistics.csv").open()))
    selected=[r for r in targets if r["source_id"]=="afhubbard" and r["gpu_model"]=="A100 40GB" and r["instrument_class"]=="hyperscaler_spot" and r["pricing_tier"]=="spot" and r["date"]<="2026-11-06"]
    official={r["date"]:float(r["median_usd_per_gpu_hour"]) for r in selected}
    sql=duckdb.connect();pattern=str(root/"rental_observations"/"*"/"*"/"*.parquet")
    raw=sql.execute("SELECT CAST(dt AS VARCHAR),median(usd_per_gpu_hour) FROM read_parquet(?,hive_partitioning=false) WHERE source_id='afhubbard' AND gpu_model='A100 40GB' AND instrument_class='hyperscaler_spot' AND pricing_tier='spot' AND CAST(dt AS DATE)<=DATE '2026-11-06' GROUP BY dt ORDER BY dt",[pattern]).fetchall()
    discrepancies=[{"date":d,"python_round":round(float(v),4),"numpy_round":float(np.round(v,4)),"official":official[d]} for d,v in raw if round(float(v),4)!=official[d]]
    report={"schema_version":8,"study_id":"price-dynamics-v8-rounding-diagnostic","series_id":"afhubbard.hyperscaler_spot.A100_40GB.spot.median","days":len(raw),"python_round_matches":sum(round(float(v),4)==official[d] for d,v in raw),"numpy_round_matches":sum(float(np.round(v,4))==official[d] for d,v in raw),"discrepancies":discrepancies,"interpretation":"Python scalar rounding and NumPy vector rounding can differ at binary halfway values. Original diagnostics retained. No forecasts, losses or replay gates are recomputed.","official_submission_changed":False,"protected_outcomes_loaded":False}
    dest=Path("/public/price-dynamics-v8");put(dest/"rounding-artifacts"/(digest(report)+".json"),report)
    tmp=dest/"rounding.pending";tmp.write_bytes(encoded(report));tmp.replace(dest/"rounding.json");public.commit()
    return report
def main():
    with app.run():r=audit.remote()
    out=Path("artifacts/dynamics-ui-v8");out.mkdir(parents=True,exist_ok=True);put(out/"rounding.json",r);print("V8_ROUNDING:"+json.dumps(r),flush=True)
if __name__=="__main__":main()
