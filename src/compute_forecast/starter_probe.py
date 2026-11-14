"""Run the unmodified Pacific starter remotely; never writes into the pack."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import modal

PACK_ID = "1_TeAyT2SYBg3HcLCaFxeWVhA2K3rtN7j"
PACK_SHA256 = "f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c"
PACK_NAME = "gpu-price-pack-v0.1.1-handover"

# Committed before executing any measured forecasting experiment.
EVALUATION_PROTOCOL = {
    "version": "1",
    "measurement": "advertised_rental_offer_rate",
    "train_last_label_date": "2026-07-31",
    "training_probe_origins": ["2026-07-24"],
    "development_origins": ["2026-08-08", "2026-08-15", "2026-08-22", "2026-08-29", "2026-09-05", "2026-09-12"],
    "final_origins": ["2026-09-27", "2026-10-04", "2026-10-11", "2026-10-18", "2026-10-25"],
    "scored_horizons_days": [1, 3, 7],
    "quantiles": [0.1, 0.5, 0.9],
    "official_origin_date": "2026-11-06",
    "official_cutoff_utc": "2026-11-06T23:59:59+00:00",
    "final_results_sealed_until_freeze": True,
    "note": "Five weekly final origins are temporally dependent; offer counts are not independent trials.",
}

app = modal.App("compute-forecast-starter-probe")
volume = modal.Volume.from_name("compute-forecast-data", create_if_missing=True, version=2)
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("gdown>=6,<7", "duckdb==1.2.2", "pandas==2.3.1", "numpy==2.2.6", "pyarrow>=16,<24")
    .add_local_python_source("compute_forecast")
)


def verify_manifest(root: Path) -> int:
    import hashlib
    import pathlib

    count = 0
    for line in (root / "MANIFEST.sha256").read_text().splitlines():
        if not line.strip():
            continue
        expected, name = line.split(maxsplit=1)
        name = name.lstrip(" *")
        relative = pathlib.PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("REFUSED: unsafe manifest member")
        file = root / name
        if not file.is_file():
            raise RuntimeError("REFUSED: missing manifest file: " + name)
        with file.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise RuntimeError("REFUSED: manifest mismatch: " + name)
        count += 1
    return count


@app.function(image=image, cpu=4, memory=8192, timeout=900, volumes={"/data": volume})
def run_starter(cutoff: str = "2026-08-08") -> dict:
    import hashlib
    import importlib.metadata
    import pathlib
    import shutil
    import subprocess
    import time
    import uuid
    import zipfile
    from datetime import date, datetime, timedelta, timezone

    import gdown

    started = time.perf_counter()
    if cutoff not in EVALUATION_PROTOCOL["development_origins"] + EVALUATION_PROTOCOL["training_probe_origins"]:
        raise RuntimeError("REFUSED: probe only accepts preregistered training/development origins")
    if date.fromisoformat(cutoff) + timedelta(days=7) >= date(2026, 9, 27):
        raise RuntimeError("REFUSED: development labels must not reach final dates")
    base = Path("/data/pacific")
    base.mkdir(parents=True, exist_ok=True)
    root = base / PACK_NAME
    archive = base / "pack.zip"
    if not root.exists():
        gdown.download(id=PACK_ID, output=str(archive), quiet=False)
        with archive.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != PACK_SHA256:
            raise RuntimeError("REFUSED: published archive SHA-256 mismatch")
        temporary = base / ("extract-" + uuid.uuid4().hex)
        temporary.mkdir()
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                path = pathlib.PurePosixPath(member.filename)
                if path.is_absolute() or ".." in path.parts or (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise RuntimeError("REFUSED: unsafe archive member")
            source.extractall(temporary)
        candidates = list(temporary.rglob("MANIFEST.sha256"))
        if len(candidates) != 1:
            raise RuntimeError("REFUSED: expected exactly one pack manifest")
        extracted = candidates[0].parent
        verify_manifest(extracted)
        extracted.rename(root)
        shutil.rmtree(temporary)
        volume.commit()
    verified_files = verify_manifest(root)
    run_id = uuid.uuid4().hex
    output = Path("/data/runs") / run_id
    output.mkdir(parents=True)
    manifest_digest_before = hashlib.sha256((root / "MANIFEST.sha256").read_bytes()).hexdigest()
    pack_members_before = sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    commands = []

    def invoke(label, arguments, expected_returncode=0):
        command = ["python", "-I", "-B", str(root / "starter" / arguments[0]), *arguments[1:]]
        result = subprocess.run(command, capture_output=True, text=True, env=env)
        (output / (label + ".stdout.txt")).write_text(result.stdout)
        (output / (label + ".stderr.txt")).write_text(result.stderr)
        commands.append({"label": label, "arguments": arguments, "returncode": result.returncode})
        if result.returncode != expected_returncode:
            volume.commit()
            raise RuntimeError("Starter command failed in run " + run_id + ": " + label + ": " + result.stderr[-5000:])
        return result

    history = str(output / "history.csv")
    catalog = str(output / "series_catalog.csv")
    truth = str(output / "truth.csv")
    # Build history FIRST so composite membership cannot be selected from later data.
    invoke("build_history", ["build_series.py", "--pack", str(root), "--cutoff", cutoff,
           "--out", history, "--catalog", catalog, "--report", str(output / "build_history_report.json")])
    label_cutoff = (date.fromisoformat(cutoff) + timedelta(days=7)).isoformat()
    invoke("build_truth", ["build_series.py", "--pack", str(root), "--cutoff", label_cutoff,
           "--members-from", catalog, "--out", truth,
           "--catalog", str(output / "truth_catalog.csv"), "--report", str(output / "build_truth_report.json")])
    for method in ("last_value", "last_value_empirical", "drift", "seasonal_naive"):
        original = output / ("baseline_all_horizons_" + method + ".csv")
        forecast = output / ("baseline_" + method + ".csv")
        invoke("baseline_" + method, ["baselines.py", "--history", history, "--origin", cutoff,
               "--method", method, "--catalog", catalog, "--tier", "headline", "--frozen", "--out", str(original)])
        with original.open() as stream:
            reader = csv.DictReader(stream)
            columns = reader.fieldnames
            rows = [row for row in reader if int(row["horizon_days"]) in (1, 3, 7)]
        with forecast.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        invoke("score_" + method, ["scorer.py", "--forecast", str(forecast), "--truth", truth,
               "--history", history, "--frozen-cutoff", cutoff, "--catalog", catalog, "--tier", "headline",
               "--out", str(output / ("report_" + method + ".json")),
               "--per-cell", str(output / ("cells_" + method + ".csv"))])
    with open(history) as stream:
        reader = csv.DictReader(stream)
        history_columns = reader.fieldnames
        history_rows = list(reader)
    with open(truth) as stream:
        later = next((row for row in csv.DictReader(stream) if row["date"] > cutoff), None)
    if later is None:
        raise RuntimeError("Refusal check unavailable: no matured later observation")
    contaminated = output / "diagnostic_contaminated_history.csv"
    with contaminated.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=history_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(history_rows)
        writer.writerow(later)
    refusal = invoke("refusal_check", ["scorer.py", "--forecast", str(output / "baseline_last_value.csv"),
               "--truth", truth, "--history", str(contaminated), "--frozen-cutoff", cutoff,
               "--catalog", catalog, "--tier", "headline", "--out", str(output / "refusal_report.json")], 2)
    if "REFUSED" not in refusal.stdout + refusal.stderr:
        raise RuntimeError("Refusal command did not report REFUSED")
    after = verify_manifest(root)
    manifest_digest_after = hashlib.sha256((root / "MANIFEST.sha256").read_bytes()).hexdigest()
    pack_members_after = sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())
    if manifest_digest_after != manifest_digest_before or pack_members_after != pack_members_before or after != verified_files:
        raise RuntimeError("REFUSED: starter execution changed the immutable pack")
    reports = {}
    for path in sorted(output.rglob("*.json")):
        if path.stat().st_size < 2_000_000:
            reports[str(path.relative_to(output))] = json.loads(path.read_text())
    artifacts = []
    for path in sorted(output.rglob("*")):
        if path.is_file():
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            artifacts.append({"path": str(path.relative_to(output)), "sha256": digest, "bytes": path.stat().st_size})
    call_id = modal.current_function_call_id() if hasattr(modal, "current_function_call_id") else None
    report = {
        "status": "completed",
        "is_synthetic": False,
        "purpose": "official_starter_development_integration",
        "run_id": run_id,
        "modal_call_id": call_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cutoff": cutoff,
        "label_cutoff": label_cutoff,
        "commands": commands,
        "refusal_check_passed": True,
        "evaluation_protocol": EVALUATION_PROTOCOL,
        "archive_sha256": PACK_SHA256,
        "manifest_files_verified_before": verified_files,
        "manifest_files_verified_after": after,
        "pack_modified": False,
        "runtime_seconds": time.perf_counter() - started,
        "cost_status": "unavailable",
        "cost_value": None,
        "volume_name": "compute-forecast-data",
        "artifact_prefix": str(output),
        "source_attribution": "Pacific Machines (2026). gpu-price-pack v0.1.1-handover. CC BY 4.0 compilation; component attribution retained in ATTRIBUTION.md.",
        "packages": {name: importlib.metadata.version(name) for name in ("gdown", "duckdb", "pandas", "numpy", "pyarrow")},
        "reports": reports,
        "artifacts": artifacts,
    }
    (output / "probe.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    volume.commit()
    return report


@app.local_entrypoint()
def main(output: str = "artifacts/starter-probe.json", cutoff: str = "2026-08-08"):
    # This client entrypoint runs only on the hosted Actions runner.
    report = run_starter.remote(cutoff)
    report["code_sha"] = os.environ.get("GITHUB_SHA")
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ("reports", "artifacts")}, indent=2))
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as summary:
            summary.write("# Genuine Pacific starter run on Modal\n\n")
            summary.write("Historical integration run; no final-period results opened.\n\n")
            summary.write("- Cutoff: " + cutoff + "\n- Run ID: " + report["run_id"] + "\n")
            summary.write("- Manifest files verified: " + str(report["manifest_files_verified_after"]) + "\n")
            summary.write("- Runtime seconds: " + str(round(report["runtime_seconds"], 3)) + "\n")
            summary.write("- Cost: unavailable; no amount invented.\n\n")
            for name, payload in report["reports"].items():
                text = json.dumps(payload, indent=2, allow_nan=False)
                summary.write("## " + name + "\n\n")
                for start in range(0, min(len(text), 16000), 3000):
                    summary.write("~~~json\n" + text[start:start+3000] + "\n~~~\n\n")
                if len(text) > 16000:
                    summary.write("Full report is retained in the run artifact.\n\n")
