"""Publish only allowlisted aggregate results; the web app cannot access raw data or keys."""
from __future__ import annotations
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
import modal
from .dashboard_ui import HTML
from .starter_probe import PACK_SHA256

app = modal.App("compute-forecast-observatory")
public = modal.Volume.from_name("compute-forecast-public", create_if_missing=True, version=2)
image = modal.Image.debian_slim(python_version="3.11").pip_install("fastapi[standard]>=0.115,<1").add_local_python_source("compute_forecast")
WARMUP_FIELDS = ("study_kind", "model", "lora_rank", "epochs", "learning_rate", "actual_training_updates", "training_examples", "training_examples_seen", "training_temporal_origins", "development_examples", "development_temporal_origins", "budget_per_case", "inference_decisions", "training_data_last_label", "development_origin", "reference_diagnostic_losses", "seeded_random_diagnostic_loss", "training_cost_status", "training_cost_value", "final_period_opened", "main_six_trial_search_study_complete", "metric_note", "limitation")
METRICS = ("n_cells", "pinball", "baseline_pinball", "skill_pooled", "skill_mean_of_series", "skill_median_of_series", "skill_geomean")

def build_snapshot(warmup, training, development, code_sha):
    if warmup["dataset_sha256"] != PACK_SHA256 or warmup["final_period_opened"] is not False:
        raise ValueError("REFUSED: wrong dataset or final results opened")
    if warmup["study_kind"] != "baseline_choice_warmup_not_main_search_study":
        raise ValueError("REFUSED: unsupported study contract")
    if warmup["training_data_last_label"] > "2026-07-31" or warmup["development_origin"] != "2026-08-08":
        raise ValueError("REFUSED: unexpected temporal boundary")
    result = {"schema_version": "1", "created_at": datetime.now(timezone.utc).isoformat(),
              "code_sha": code_sha, "dataset_sha256": PACK_SHA256,
              "warmup": {key: warmup[key] for key in WARMUP_FIELDS}, "baselines": [],
              "links": {"audit": "https://github.com/howdymary/compute-forecasting/actions/runs/43634354788",
                        "baselines": "https://github.com/howdymary/compute-forecasting/actions/runs/43637893251",
                        "training": "https://github.com/howdymary/compute-forecasting/actions/runs/43639917509"}}
    result["warmup"]["comparisons"] = [{key: row[key] for key in ("policy", "cases", "temporal_origins", "diagnostic_mean_pinball", "chosen_config_counts")} for row in warmup["comparisons"]]
    for report, origin in ((training, "2026-07-24"), (development, "2026-08-08")):
        if report["is_synthetic"] or report["status"] != "completed" or report["archive_sha256"] != PACK_SHA256 or report["cutoff"] != origin or not report["refusal_check_passed"] or report["pack_modified"]:
            raise ValueError("REFUSED: source run failed provenance or leakage checks")
        for method in ("last_value", "last_value_empirical", "drift", "seasonal_naive"):
            scored = report["reports"]["report_" + method + ".json"]
            if scored["forecast_validation"]["n_problems"] or scored["cells"]["missing_forecast"]:
                raise ValueError("REFUSED: invalid or missing submitted forecast cells")
            result["baselines"].append({"origin": origin, "method": method, "run_id": report["run_id"],
                "source_code_sha": report["code_sha"], "runtime_seconds": report["runtime_seconds"],
                "overall": {key: scored["overall"].get(key) for key in METRICS},
                "horizons": {str(h): {key: scored["by_horizon"][str(h)].get(key) for key in METRICS} for h in (1,3,7)}})
    validate_snapshot(result)
    return result

def validate_snapshot(snapshot):
    if set(snapshot) != {"schema_version", "created_at", "code_sha", "dataset_sha256", "warmup", "baselines", "links"}:
        raise ValueError("REFUSED: unexpected public snapshot fields")
    if snapshot["dataset_sha256"] != PACK_SHA256 or len(snapshot["code_sha"]) != 40:
        raise ValueError("REFUSED: missing content provenance")
    if set(snapshot["warmup"]) != set(WARMUP_FIELDS) | {"comparisons"}:
        raise ValueError("REFUSED: unexpected policy payload")
    if snapshot["warmup"]["final_period_opened"] is not False:
        raise ValueError("REFUSED: final evaluation must remain sealed in this snapshot")
    if set(snapshot["links"]) != {"audit", "baselines", "training"} or any(not url.startswith("https://github.com/howdymary/compute-forecasting/actions/runs/") for url in snapshot["links"].values()):
        raise ValueError("REFUSED: untrusted provenance link")
    for row in snapshot["baselines"]:
        if set(row) != {"origin", "method", "run_id", "source_code_sha", "runtime_seconds", "overall", "horizons"} or row["origin"] not in ("2026-07-24", "2026-08-08"):
            raise ValueError("REFUSED: unexpected baseline payload")
        if set(row["overall"]) != set(METRICS) or set(row["horizons"]) != {"1", "3", "7"}:
            raise ValueError("REFUSED: unexpected metric payload")
        for metrics in [row["overall"], *row["horizons"].values()]:
            if set(metrics) != set(METRICS) or any(v is not None and (not isinstance(v, (int,float)) or not math.isfinite(v)) for v in metrics.values()):
                raise ValueError("REFUSED: nonnumeric public metrics")
    encoded = json.dumps(snapshot, allow_nan=False)
    if len(encoded) > 200_000:
        raise ValueError("REFUSED: unexpectedly large public snapshot")
    for forbidden in ("api_key", "token_secret", "sampler_path", "state_path", "rental_observations", "Authorization"):
        if forbidden in encoded:
            raise ValueError("REFUSED: private information in public snapshot")

@app.function(image=image, cpu=0.25, memory=256, timeout=60, volumes={"/public": public})
def publish_snapshot(snapshot: dict):
    validate_snapshot(snapshot)
    encoded = json.dumps(snapshot, indent=2, allow_nan=False).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    root = Path("/public")
    (root / (digest + ".json")).write_bytes(encoded)
    temporary = root / "current.pending"
    temporary.write_bytes(encoded)
    temporary.replace(root / "current.json")
    public.commit()
    return {"sha256": digest, "bytes": len(encoded), "published_at": datetime.now(timezone.utc).isoformat()}

@app.function(image=image, cpu=0.25, memory=256, timeout=60, scaledown_window=60, volumes={"/public": public})
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web():
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    web_app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    file = Path("/public/current.json")
    snapshot = json.loads(file.read_text()) if file.exists() else None
    if snapshot is not None:
        validate_snapshot(snapshot)
    headers = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "strict-origin-when-cross-origin", "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"}
    @web_app.get("/")
    def index():
        return HTMLResponse(HTML, headers=headers)
    @web_app.get("/api/snapshot")
    def read_snapshot():
        if snapshot is None:
            return JSONResponse({"error": "No measured snapshot has been published"}, status_code=503, headers=headers)
        return JSONResponse(snapshot, headers={**headers, "Cache-Control": "public, max-age=60"})
    @web_app.get("/health")
    def health():
        return JSONResponse({"status": "ok" if snapshot else "awaiting_results", "snapshot_sha": hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest() if snapshot else None}, headers=headers)
    return web_app

@app.local_entrypoint()
def main(warmup_report: str = "inputs/policy-warmup/warmup-report.json", training_report: str = "inputs/starter-training.json", development_report: str = "inputs/starter-development.json"):
    snapshot = build_snapshot(json.loads(Path(warmup_report).read_text()), json.loads(Path(training_report).read_text()), json.loads(Path(development_report).read_text()), os.environ["GITHUB_SHA"])
    result = publish_snapshot.remote(snapshot)
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/dashboard-snapshot.json").write_text(json.dumps(snapshot,indent=2)+"\n")
    Path("artifacts/publication.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
        f.write("# Published measured observatory snapshot\n\n~~~json\n" + json.dumps(result,indent=2) + "\n~~~\n\nOnly aggregate metrics are published; raw data and credentials are not mounted in the web service.\n")
