"""Read-only diagnosis of public status routes; no models, snapshots or commitments are changed."""
import json,pathlib,time
import modal
app=modal.App("compute-forecast-serving-diagnostic-v18")
volume=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11")
@app.function(image=image,cpu=.5,memory=512,timeout=120,volumes={"/public":volume})
def inspect_indices():
    rows=[]
    for name in ("evidence-v14-future/index.json","probability-v18-future/index.json","forecast-serving/evidence-v14/index.json","forecast-serving/probability-v18/index.json"):
        begin=time.monotonic();path=pathlib.Path("/public")/name
        row={"path":name,"exists":path.exists()}
        if path.exists():
            row["bytes"]=path.stat().st_size
            if row["bytes"]<=20000000:
                value=json.loads(path.read_bytes())
                row.update(study_id=value.get("study_id"),keys=sorted(value),issued_origins=value.get("issued_origins"),commitments=len(value.get("commitments",[])))
        row["elapsed_seconds"]=time.monotonic()-begin;rows.append(row)
    return {"public_indices":rows,"new_optimizer_updates":0,"model_calls":0,"data_modified":False}
@app.local_entrypoint()
def main():
    root=pathlib.Path("artifacts/probability-v18-serving-diagnostic");root.mkdir(parents=True,exist_ok=True)
    value=inspect_indices.remote()
    (root/"volume-metadata.json").write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps(value),flush=True)
