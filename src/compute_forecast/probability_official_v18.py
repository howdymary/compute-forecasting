"""Independent native starter-scorer verification of retained v18 forecasts; no model calls."""
import csv,hashlib,json,os,pathlib,tempfile,time
from datetime import datetime,timezone
import modal
from .starter_probe import PACK_NAME,verify_manifest
from .pacific_value_v5 import build_history,invoke,rows,write_csv
from .probability_v18 import digest
app=modal.App("compute-forecast-probability-v18-native-score")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=(modal.Image.debian_slim(python_version="3.11").pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","pyarrow>=16,<24").add_local_python_source("compute_forecast"))
@app.function(image=image,cpu=4,memory=8192,timeout=1200,max_containers=1,volumes={"/data":data})
def audit(report,source_report_sha):
    started=time.monotonic();data.reload();pack=pathlib.Path("/data/pacific")/PACK_NAME
    assert verify_manifest(pack)==672
    work=pathlib.Path(tempfile.mkdtemp(prefix="native-probability-v18-"))
    history,catalog,hp,cp=build_history(pack,work,"2026-11-06")
    methods={"untuned":report["base"]["retrospective"]["cells"]}
    methods.update({"native-"+name:value["cells"] for name,value in report["native_references"].items()})
    methods.update({r["objective"]+"-"+str(r["seed"]):r["retrospective_evaluation"]["cells"] for r in report["runs"]})
    expected={(r["series_id"],r["origin"],r["horizon_days"]) for r in methods["untuned"]}
    ids=sorted({k[0] for k in expected});assert len(expected)==75 and len(ids)==11
    outputs=[]
    for name,cells in methods.items():
        assert {(r["series_id"],r["origin"],r["horizon_days"]) for r in cells}==expected
        fc=work/(name+".csv");columns=["series_id","origin_date","horizon_days","q10","q50","q90","target_date"]
        records=[{"series_id":r["series_id"],"origin_date":r["origin"],"horizon_days":r["horizon_days"],"q10":r["q10"],"q50":r["q50"],"q90":r["q90"],"target_date":r["target_date"]} for r in cells];write_csv(fc,records,columns)
        output=work/(name+"-report.json");percell=work/(name+"-cells.csv")
        invoke(pack,work,"score-"+name,["scorer.py","--forecast",fc,"--truth",hp,"--history",hp,"--catalog",cp,"--series-ids",",".join(ids),"--horizons","1,3,7","--no-missing-as-baseline","--out",output,"--per-cell",percell])
        native=rows(percell);actual={(r["series_id"],r["origin_date"],int(r["horizon_days"])) for r in native};assert actual==expected
        by_key={(r["series_id"],r["origin"],r["horizon_days"]):r for r in cells};max_difference=0.
        for row in native:
            target=by_key[(row["series_id"],row["origin_date"],int(row["horizon_days"]))]
            assert row["status"]=="scored" and abs(float(row["y"])-target["outcome"])<1e-12
            max_difference=max(max_difference,abs(float(row["loss"])-target["loss"]))
            assert max_difference<1e-12,"Official per-cell score differs"
        outputs.append({"method":name,"n":len(native),"max_cell_loss_difference":max_difference,"forecast_csv_sha256":hashlib.sha256(fc.read_bytes()).hexdigest(),"official_report":json.loads(output.read_bytes()),"cells":native})
    assert verify_manifest(pack)==672
    return {"study_id":"direct-probability-v18-native-score-audit","status":"verified","source_report_sha256":source_report_sha,"dataset_sha256":report["dataset_sha256"],"source_protocol_sha256":report["protocol_sha256"],"scorer_sha256":hashlib.sha256((pack/"starter/scorer.py").read_bytes()).hexdigest(),"baseline_sha256":hashlib.sha256((pack/"starter/baselines.py").read_bytes()).hexdigest(),"history_sha256":hashlib.sha256(hp.read_bytes()).hexdigest(),"methods":outputs,"scoring_scope":"Historical backtest through November6; no later competition outcomes","protected_outcomes_loaded":False,"new_optimizer_updates":0,"provider_cost_usd":None,"runtime_seconds":time.monotonic()-started,"checked_at":datetime.now(timezone.utc).isoformat()}
@app.local_entrypoint()
def main():
    pointer=json.loads(pathlib.Path("results/probability-v18/latest.json").read_bytes());raw=pathlib.Path(pointer["report_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"]
    report=json.loads(raw);value=audit.remote(report,pointer["report_sha256"])
    out=pathlib.Path("artifacts/probability-v18-native");out.mkdir(parents=True,exist_ok=True)
    (out/"native-score-audit.json").write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:value[k] for k in ("study_id","status","runtime_seconds","source_report_sha256")}),flush=True)
