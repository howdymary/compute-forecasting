"""Frozen November 6 official export; never retrieves future competition truth."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import modal
from .representation_study import image,volume
from .freeze_contract import validate_freeze,PACK_SHA

app=modal.App("compute-forecast-official-export")
COLUMNS=("series_id","origin_date","horizon_days","q10","q50","q90")
ORIGIN="2026-11-06"

def scenario_outlook():
    assumptions=[{"scenario":"supply_expansion","rental_annual_change":-.35,"resale_annual_depreciation":.40,"assumption":"Rapid capacity addition and substitution toward newer accelerators."},{"scenario":"moderate_decline","rental_annual_change":-.15,"resale_annual_depreciation":.25,"assumption":"Continued efficiency gains with continued demand for older accelerators."},{"scenario":"persistent_constraints","rental_annual_change":.05,"resale_annual_depreciation":.10,"assumption":"Capacity constraints support nominal rental rates and slow depreciation."}]
    rows=[]
    for case in assumptions:
        for years in (2,3):
            rows.append({"scenario":case["scenario"],"years":years,"rental_index":100*(1+case["rental_annual_change"])**years,"resale_index":100*(1-case["resale_annual_depreciation"])**years})
    return {"kind":"assumption_driven_scenario_not_fitted_forecast","reference_date":ORIGIN,"reference_index":100,"rental_reference":"100 represents the November 6 advertised rate for a specified source/SKU/contract, conditional on that contract still being quoted.","resale_reference":"100 is a hypothetical hardware resale-value anchor. The pack does not provide an open executed resale-price dataset; no observed dollar resale anchor is claimed.","scenario_probabilities":None,"confidence_level":None,"assumptions":assumptions,"results":rows,"limitations":["The scenario envelope is not a confidence interval or quantile forecast.","No scenario probabilities were estimated.","Quote survival, capacity, transaction execution and hardware condition are not modeled.","Rental and hardware resale are separate instruments; rental rates do not directly determine resale prices.","These illustrative annual changes are explicit assumptions, not empirical estimates."]}

def validate_export(rows,headline_ids):
    seen=set()
    for row in rows:
        key=(row["series_id"],int(row["horizon_days"]))
        if row["origin_date"]!=ORIGIN or key in seen or key[0] not in headline_ids or key[1] not in (1,3,7):
            raise ValueError("REFUSED: wrong origin, duplicate, horizon or official target")
        qs=[float(row[k]) for k in ("q10","q50","q90")]
        if any(not __import__('math').isfinite(q) or q<=0 for q in qs) or qs!=sorted(qs):
            raise ValueError("REFUSED: nonpositive, nonfinite or crossing forecast quantiles")
        seen.add(key)
    if seen!={(sid,h) for sid in headline_ids for h in (1,3,7)}:
        raise ValueError("REFUSED: incomplete official headline forecast export")

@app.function(image=image,cpu=4,memory=8192,timeout=900,volumes={"/data":volume})
def export_frozen(freeze):
    import math
    import shutil
    import subprocess
    import tempfile
    import time
    import uuid
    import zipfile
    from datetime import datetime,timezone
    validate_freeze(freeze)
    started=time.perf_counter();run_id=uuid.uuid4().hex
    temporary=Path(tempfile.mkdtemp(prefix="pacific-export-"));archive=temporary/"pack.zip"
    shutil.copyfile("/data/pacific/pack.zip",archive)
    with archive.open("rb") as f:
        if hashlib.file_digest(f,"sha256").hexdigest()!=PACK_SHA:raise ValueError("REFUSED: archive hash mismatch")
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            p=Path(member.filename)
            if p.is_absolute() or ".." in p.parts or (member.external_attr>>16)&0o170000==0o120000:raise ValueError("REFUSED: unsafe archive member")
        z.extractall(temporary/"pack")
    root=next((temporary/"pack").rglob("MANIFEST.sha256")).parent
    work=temporary/"work";work.mkdir()
    commands=[]
    def execute(label,args):
        response=subprocess.run(["python","-I","-B",str(root/"starter"/args[0]),*args[1:]],capture_output=True,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1"))
        commands.append({"label":label,"arguments":args,"returncode":response.returncode})
        (work/(label+".stdout.txt")).write_text(response.stdout);(work/(label+".stderr.txt")).write_text(response.stderr)
        if response.returncode:raise RuntimeError("Official export command failed: "+label+" "+response.stderr[-2000:])
    history=work/"history.csv";catalog=work/"catalog.csv";original=work/"all-horizons.csv"
    execute("history_only",["build_series.py","--pack",str(root),"--cutoff",ORIGIN,"--out",str(history),"--catalog",str(catalog),"--report",str(work/"history-build.json")])
    with history.open() as f:
        if any(row["date"]>ORIGIN for row in csv.DictReader(f)):raise ValueError("REFUSED: history contains a later date")
    with catalog.open() as f:catalog_rows=list(csv.DictReader(f))
    ids={row["series_id"] for row in catalog_rows if row["tier"]=="headline"}
    if not ids:raise ValueError("REFUSED: official headline catalog is empty")
    execute("frozen_baseline",["baselines.py","--history",str(history),"--origin",ORIGIN,"--method",freeze["official_method"],"--catalog",str(catalog),"--tier","headline","--frozen","--out",str(original)])
    with original.open() as f:rows=[{key:r[key] for key in COLUMNS} for r in csv.DictReader(f) if r["series_id"] in ids and int(r["horizon_days"]) in (1,3,7)]
    rows.sort(key=lambda r:(r["series_id"],int(r["horizon_days"])))
    validate_export(rows,ids)
    text=io.StringIO();writer=csv.DictWriter(text,fieldnames=COLUMNS);writer.writeheader();writer.writerows(rows);forecast_csv=text.getvalue()
    (work/"forecasts.csv").write_text(forecast_csv)
    outlook=scenario_outlook();(work/"outlook-scenarios.json").write_text(json.dumps(outlook,indent=2))
    markdown="# Two- and three-year rental and resale outlook\n\nThese are assumption-driven sensitivities, separate from the scored 1/3/7-day forecasts. Rental index 100 is a specified contract's November 6 quote; resale index 100 is a hypothetical starting value, not an observed transaction. No probabilities or confidence levels are estimated.\n\n| Scenario | Years | Rental index | Resale index |\n|---|---:|---:|---:|\n"
    for r in outlook["results"]:markdown+="| "+r["scenario"]+" | "+str(r["years"])+" | "+str(round(r["rental_index"],2))+" | "+str(round(r["resale_index"],2))+" |\n"
    markdown+="\n"+"\n".join("- "+r["scenario"]+": rental annual change "+str(r["rental_annual_change"])+"; resale annual depreciation "+str(r["resale_annual_depreciation"])+". "+r["assumption"] for r in outlook["assumptions"])+"\n\nThe envelope is not a calibrated prediction interval. SKU discontinuation, utilization, energy costs, hardware condition and transaction liquidity can dominate these assumptions. There is no open executed resale-price series in the pack.\n"
    (work/"outlook.md").write_text(markdown)
    output=Path("/data/submissions")/run_id;output.mkdir(parents=True)
    artifacts=[]
    for file in work.iterdir():
        if file.is_file():
            shutil.copyfile(file,output/file.name);artifacts.append({"path":file.name,"sha256":hashlib.sha256(file.read_bytes()).hexdigest(),"bytes":file.stat().st_size})
    report={"schema_version":"1","run_id":run_id,"origin_date":ORIGIN,"origin_cutoff_utc":"2026-11-06T23:59:59+00:00","dataset_sha256":PACK_SHA,"method":freeze["official_method"],"selection_phase":"development","selection_run_id":freeze["official_selection_run_id"],"freeze_created_at":freeze["frozen_at"],"n_headline_series":len(ids),"forecast_rows":len(rows),"horizons_days":[1,3,7],"quantiles":[.1,.5,.9],"columns":COLUMNS,"forecast_csv_sha256":hashlib.sha256(forecast_csv.encode()).hexdigest(),"future_competition_truth_loaded":False,"official_future_score":None,"validation":"Schema, positivity, ordering and complete official headline coverage; no future-outcome score","commands":commands,"artifacts":artifacts,"runtime_seconds":time.perf_counter()-started,"modal_call_id":modal.current_function_call_id(),"cost_status":"unavailable","cost_value":None,"created_at":datetime.now(timezone.utc).isoformat(),"vintage_note":"Retrospective pack frozen November 9; this is not proof of real-time historical accessibility.","source_attribution":"Pacific Machines (2026), gpu-price-pack v0.1.1-handover; upstream attribution retained; raw pack not redistributed."}
    (output/"export-report.json").write_text(json.dumps(report,indent=2));volume.commit();shutil.rmtree(temporary)
    return {"report":report,"forecasts_csv":forecast_csv,"outlook":outlook,"outlook_markdown":markdown}

@app.local_entrypoint()
def main(freeze_file: str="configs/release-freeze.json",output_dir: str="artifacts/submission"):
    freeze=json.loads(Path(freeze_file).read_text());validate_freeze(freeze)
    result=export_frozen.remote(freeze);result["report"]["code_sha"]=os.environ.get("GITHUB_SHA")
    if hashlib.sha256(result["forecasts_csv"].encode()).hexdigest()!=result["report"]["forecast_csv_sha256"]:raise ValueError("Export transfer hash mismatch")
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    (out/"forecasts.csv").write_text(result["forecasts_csv"]);(out/"export-report.json").write_text(json.dumps(result["report"],indent=2));(out/"outlook-scenarios.json").write_text(json.dumps(result["outlook"],indent=2));(out/"outlook.md").write_text(result["outlook_markdown"])
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
        f.write("# Frozen official forecast export\n\n~~~json\n"+json.dumps({k:v for k,v in result["report"].items() if k not in ("commands","artifacts")},indent=2)+"\n~~~\n\n"+result["outlook_markdown"])
