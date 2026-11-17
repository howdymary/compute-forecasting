"""Read-only study progress; private checkpoint resource paths are never returned."""
import json,pathlib
import modal
from .probability_v18 import digest
app=modal.App("compute-forecast-market-v19-progress")
volume=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
@app.function(image=image,cpu=.5,memory=512,timeout=90,max_containers=1,volumes={"/data":volume})
def inspect(protocol_sha):
    rows=[]
    for arm in ("price","market"):
        for seed in (17,29,43):
            path=pathlib.Path("/data/market-state-v19")/protocol_sha/(arm+"-"+str(seed))/"recovery.json"
            if not path.exists():rows.append({"arm":arm,"seed":seed,"status":"not_yet_backed_up","optimizer_updates":0});continue
            x=json.loads(path.read_bytes());s=x.get("state",x.get("public_files",{}).get("result.json",{}))
            rows.append({"arm":arm,"seed":seed,"status":"completed" if x.get("completed") else "in_progress","optimizer_updates":x["optimizer_updates"],"planned_updates":s.get("planned_updates"),"checkpoints":[{"update":c["update"],"development_pinball":c["development"]["primary_pinball"]} for c in s.get("checkpoints",[])]})
    return {"study_id":"market-state-v19","runs":rows,"model_calls":0,"new_optimizer_updates":0,"note":"Updates are the latest durable recovery checkpoint; in-flight steps may be newer"}
@app.local_entrypoint()
def main():
    p=json.loads(pathlib.Path("configs/market-state-v19.json").read_bytes());v=inspect.remote(digest(p))
    out=pathlib.Path("artifacts/market-state-v19-status");out.mkdir(parents=True,exist_ok=True);(out/"progress.json").write_text(json.dumps(v,indent=2)+"\n");print(json.dumps(v))
