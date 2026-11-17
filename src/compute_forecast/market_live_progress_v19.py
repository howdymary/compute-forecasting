"""Publish only retained, measured progress; never rerun an experiment."""
import json,pathlib,hashlib
import modal
from .probability_v18 import digest
app=modal.App("compute-forecast-market-v19-live-progress")
volume=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
@app.function(image=image,cpu=.5,memory=1024,timeout=120,max_containers=1,volumes={"/data":volume})
def read_progress(key,protocol,base,controls):
    volume.reload();root=pathlib.Path("/data/market-state-v19")
    data=json.loads((root/"inputs"/key/"dataset.json").read_bytes());audit=json.loads((root/"inputs"/key/"audit.json").read_bytes())
    assert digest(data)==audit["dataset_sha256"] and data["protocol_sha256"]==digest(protocol)
    cases={}
    for t in sorted(data["groups"]["development"],key=lambda t:(t["origin"],t["series_id"])):
        cases[t["task_id"]]={"task_id":t["task_id"],"origin":t["origin"],"metadata":t["metadata"],"history":t["context"],"market_state":t["market_state"],"market_input_identity":t["market_input_identity"],"target_dates":t["target_dates"],"outcomes":t["outcomes"],"checkpoints":[]}
    runs=[]
    for arm in ("price","market"):
        for seed in (17,29,43):
            file=root/digest(protocol)/(arm+"-"+str(seed))/"recovery.json";recovery=json.loads(file.read_bytes()) if file.exists() else {}
            state=recovery.get("state",recovery.get("public_files",{}).get("result.json",{}));files=recovery.get("public_files",{})
            checkpoints=state.get("checkpoints",[{"update":0,"checkpoint_id":None,"development":base[arm]["development"]["summary"]}])
            completed=recovery.get("completed",False);selected=state.get("selected") if completed else None
            runs.append({"arm":arm,"seed":seed,"status":"completed" if completed else ("in_progress" if recovery else "queued"),"optimizer_updates":recovery.get("optimizer_updates",0),"checkpoints":checkpoints,"selected":selected,"retrospective":files.get("evaluation-selected.json") if completed else None,"untuned":base[arm]["retrospective"],"shared_untuned_reference":True})
            for cp in checkpoints:
                dev=base[arm]["development"] if cp["update"]==0 else files["development-"+str(cp["update"])+".json"]
                for task_id,c in cases.items():
                    rows=[r for r in dev["cells"] if r["task_id"]==task_id];assert len(rows)==3
                    c["checkpoints"].append({"arm":arm,"seed":seed,"update":cp["update"],"selected":bool(selected and cp["update"]==selected["update"]),"rows":rows})
    return {"snapshot_at":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),"study_id":"market-state-v19-progress","status":"training_in_progress","log_levels":data["log_levels"],"protocol":protocol,"protocol_sha256":digest(protocol),"audit":audit,"runs":runs,"controls":controls,"cases":list(cases.values()),"new_optimizer_updates":sum(r["optimizer_updates"] for r in runs),"optimizer_count_scope":"Lower bound from durable recovery records; in-flight steps may be newer","completed_runs":sum(r["status"]=="completed" for r in runs),"shared_untuned_reference":"One measured untuned reference per input condition, shared across the registered seeds; queued runs have no trained checkpoint","prospective_accuracy":"not established","model_calls":0,"new_updates_in_progress_export":0}
@app.local_entrypoint()
def main():
    inputs=pathlib.Path("inputs/market-state-v19");key=json.loads((inputs/"input-key.json").read_bytes())["private_key"]
    p=json.loads(pathlib.Path("configs/market-state-v19.json").read_bytes());base=json.loads((inputs/"base.json").read_bytes());controls=json.loads(pathlib.Path("artifacts/market-state-v19-controls/controls.json").read_bytes())
    result=read_progress.remote(key,p,base,controls);out=pathlib.Path("artifacts/market-state-v19-progress");out.mkdir(parents=True,exist_ok=True)
    (out/"report.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"durable_updates":result["new_optimizer_updates"],"completed_runs":result["completed_runs"],"new_model_calls":0,"new_optimizer_updates":0}))
