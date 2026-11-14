"""Choose a fixed competition baseline using exact, matured development scores."""
from __future__ import annotations
import argparse
import json
import math
import os
from datetime import datetime,timezone
from pathlib import Path
from .policy_warmup import read_run_csv

METHODS=("last_value","last_value_empirical","drift","seasonal_naive")
ORIGINS=("2026-08-08","2026-08-15","2026-08-22","2026-08-29","2026-09-05","2026-09-12")
PACK_SHA="f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c"

def select(reports,volume,expected_sha):
    if {r["cutoff"] for r in reports}!=set(ORIGINS) or len(reports)!=6:
        raise ValueError("REFUSED: all six registered development origins are required")
    rows=[]
    for report in reports:
        if report["is_synthetic"] or report["status"]!="completed" or report["archive_sha256"]!=PACK_SHA or report["code_sha"]!=expected_sha or not report["refusal_check_passed"] or report["pack_modified"] or report["label_cutoff"]>"2026-09-19":
            raise ValueError("REFUSED: invalid development provenance or information cutoff")
        for method in METHODS:
            columns,cells=read_run_csv(volume,report,"cells_"+method+".csv")
            if not {"loss","baseline_loss","horizon_days"}<=set(columns):
                raise ValueError("REFUSED: official per-cell schema changed")
            values=[]
            for cell in cells:
                try:value=float(cell["loss"])
                except (ValueError,TypeError):continue
                if math.isfinite(value):values.append(value)
            scored=report["reports"]["report_"+method+".json"]
            if len(values)!=scored["overall"]["n_cells"] or not values:
                raise ValueError("REFUSED: official score count mismatch")
            exact=sum(values)/len(values)
            if abs(exact-scored["overall"]["pinball"])>0.00000051:
                raise ValueError("REFUSED: official cell losses disagree with report")
            rows.append({"origin":report["cutoff"],"label_end":report["label_cutoff"],"method":method,"pinball":exact,"n_cells":len(values),"run_id":report["run_id"],"source_code_sha":report["code_sha"]})
    summaries=[]
    for method in METHODS:
        selected=[r for r in rows if r["method"]==method];cells=sum(r["n_cells"] for r in selected)
        summaries.append({"method":method,"pooled_pinball":sum(r["pinball"]*r["n_cells"] for r in selected)/cells,"mean_origin_pinball":sum(r["pinball"] for r in selected)/len(selected),"n_cells":cells,"temporal_origins":len(selected)})
    chosen=min(summaries,key=lambda r:(r["pooled_pinball"],METHODS.index(r["method"])))
    return {"schema_version":"1","scope":"official_full_headline_catalog","selection_phase":"development","dataset_sha256":PACK_SHA,"code_sha":expected_sha,"selected_method":chosen["method"],"selection_rule":"Minimum pooled exact official per-cell development pinball; declared method order on exact ties","methods":summaries,"origin_results":rows,"source_runs":[{"run_id":r["run_id"],"origin":r["cutoff"],"modal_call_id":r["modal_call_id"],"runtime_seconds":r["runtime_seconds"]} for r in reports],"last_development_label":"2026-09-19","final_period_opened":False,"cost_status":"unavailable","cost_value":None,"created_at":datetime.now(timezone.utc).isoformat(),"limitations":"Six weekly origins are dependent; the headline catalog varies with origin; this is development selection, not a test claim."}

if __name__=="__main__":
    import modal
    parser=argparse.ArgumentParser();parser.add_argument("--input-dir",default="inputs/baselines");parser.add_argument("--output",default="artifacts/development-baseline-selection.json")
    args=parser.parse_args();reports=[json.loads(p.read_text()) for p in Path(args.input_dir).rglob("baseline-2026-*.json")]
    volume=modal.Volume.from_name("compute-forecast-data",create_if_missing=False)
    result=select(reports,volume,os.environ["GITHUB_SHA"])
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2)+"\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
        f.write("# Actual full-headline baseline selection\n\n~~~json\n"+json.dumps({k:v for k,v in result.items() if k not in ("origin_results","source_runs")},indent=2)+"\n~~~\n")
