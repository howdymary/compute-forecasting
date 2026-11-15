"""Publish only saved checkpoint progress; no model calls or private resource paths."""
from __future__ import annotations
import json,os
from datetime import datetime,timezone
from pathlib import Path
import modal
from .starter_probe import volume
app=modal.App("compute-forecast-v2-progress")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
@app.function(image=image,cpu=.25,memory=256,timeout=60,volumes={"/data":volume,"/public":public})
def snapshot(source_sha,github_run_id):
    volume.reload();rows=[]
    for path in Path("/data/campaign-v2/policies").glob("*.json"):
        p=json.loads(path.read_text())
        rows.append({"run_id":p["run_id"],"mode":p["mode"],"seed":p["seed"],"objective":p["objective"],
          "saved_optimizer_updates":p.get("completed_optimizer_updates",0),
          "saved_rollout_sampler_count":len(p.get("rollout_snapshots",[])),
          "development_evaluated_checkpoints":len(p.get("checkpoints",[])),
          "checkpoint_selection_recorded":bool(p.get("selected")),
          "manifest_updated_at":datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat()})
    result={"schema_version":2,"observed_at":datetime.now(timezone.utc).isoformat(),"source_sha":source_sha,"github_run_id":github_run_id,
      "scope":"Saved private manifests only; optimizer counts can lag in-memory updates. Sampler counts are started rollout snapshots, not completed optimizer steps.",
      "runs":sorted(rows,key=lambda r:(r["mode"],r["seed"],r["objective"],r["run_id"]))}
    assert "tinker://" not in json.dumps(result)
    public.reload();root=Path("/public/experimental-v2");root.mkdir(parents=True,exist_ok=True)
    (root/"training-progress.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n");public.commit()
    return result
@app.local_entrypoint()
def main():
    result=snapshot.remote(os.environ["GITHUB_SHA"],os.environ["GITHUB_RUN_ID"])
    print("V2_TRAINING_PROGRESS:"+json.dumps(result),flush=True)
