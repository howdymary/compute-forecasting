"""Inspect actual pack metadata remotely without exposing rental-offer rows."""
from __future__ import annotations
import json
import os
from pathlib import Path
import modal
from .starter_probe import image, volume, PACK_NAME, PACK_SHA256, verify_manifest
app = modal.App("compute-forecast-metadata-audit")

@app.function(image=image, cpu=2, memory=4096, timeout=300, volumes={"/data": volume})
def inspect_metadata():
    import csv
    import duckdb
    root = Path("/data/pacific") / PACK_NAME
    verified = sum(bool(line.strip()) for line in (root / "MANIFEST.sha256").read_text().splitlines())
    print("Manifest entries read; prior integrity run verified contents", flush=True)
    cached = Path("/data/runs/3219f79a4dbe4823b293cccfa6368be0")
    def table(path):
        with path.open() as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        return {"columns": reader.fieldnames, "rows": len(rows), "examples": rows[:3]}
    catalog = table(cached / "series_catalog.csv")
    con = duckdb.connect()
    parquet = str(next((root / "rental_observations").rglob("*.parquet")))
    print("Inspecting one physical Parquet schema", flush=True)
    schema = con.execute("DESCRIBE SELECT * FROM read_parquet(?, hive_partitioning=false)", [parquet]).fetchall()
    result = {"archive_sha256": PACK_SHA256, "manifest_entries": verified, "integrity_verification_source": "Actions 43634354788 and 43637893251; this metadata probe does not rehash all files",
              "catalog": catalog, "history_columns": next(csv.reader((cached / "history.csv").open())),
              "offer_schema": [{"column": row[0], "type": row[1]} for row in schema],
              "daily_statistics_columns": next(csv.reader((root / "daily_statistics.csv").open())),
              "licensing": "Compilation CC BY 4.0 is described as owner default pending confirmation in DATA.md; retain per-source terms; no raw redistribution authorized."}
    result["catalog_values"] = {name: sorted({str(row.get(name, "")) for row in csv.DictReader((cached / "series_catalog.csv").open())})[:100] for name in catalog["columns"] if any(term in name.lower() for term in ("gpu", "source", "tier", "instrument", "stat", "metric"))}
    result["starter_build_source"] = (root / "starter" / "build_series.py").read_text()
    return result

@app.local_entrypoint()
def main(output: str = "artifacts/metadata-audit.json"):
    result = inspect_metadata.remote()
    result["code_sha"] = os.environ.get("GITHUB_SHA")
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
        f.write("# Actual Pacific metadata and adapter audit\n\n")
        source = result.pop("starter_build_source")
        f.write("~~~json\n" + json.dumps(result, indent=2) + "\n~~~\n\n")
        f.write("## Official builder (unaltered)\n\n~~~python\n" + source + "\n~~~\n")
