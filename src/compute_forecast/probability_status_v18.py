"""Read public-safe progress from private recovery receipts; no model calls."""
import json,pathlib,datetime
import modal
from .probability_v18 import digest
app=modal.App("compute-forecast-probability-v18-status")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_file("configs/direct-probability-v18.json","/root/configs/direct-probability-v18.json",copy=True).add_local_python_source("compute_forecast")
@app.function(image=image,cpu=.25,memory=512,timeout=120,volumes={"/data":data})
def snapshot():
    data.reload();p=json.loads(pathlib.Path("/root/configs/direct-probability-v18.json").read_text());root=pathlib.Path("/data/probability-v18")/digest(p);runs=[]
    for file in sorted(root.glob("*/recovery.json")):
        r=json.loads(file.read_text());s=r["public_files"].get("result.json") or r.get("state",{})
        runs.append({k:s.get(k) for k in ("objective","seed","learning_rate","optimizer_updates","planned_updates","example_presentations","status","elapsed_seconds","checkpoints")})
    return {"study_id":p["study_id"],"checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"protocol_sha256":digest(p),"runs":runs,"scope":"Last retained private recovery receipt; a running process may have later updates not yet checkpointed","new_optimizer_updates":0,"private_paths_published":False}
@app.local_entrypoint()
def main():
    value=snapshot.remote();out=pathlib.Path("artifacts/probability-v18-status");out.mkdir(parents=True,exist_ok=True);(out/"progress.json").write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps(value),flush=True)
