"""Publish immutable serving copies after GitHub publication; never calls a model."""
import hashlib,json,os,pathlib,time
from datetime import datetime,timezone
import modal
from .artifact_snapshot_v18 import NAMES
app=modal.App("compute-forecast-probability-v18-serving")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
@app.function(image=image,cpu=.5,memory=512,timeout=180,max_containers=1,volumes={"/public":public})
def publish(payloads):
    started=time.monotonic();public.reload();receipts=[]
    for item in payloads:
        raw=item["raw"];pointer=item["pointer"];study=item["study_id"];value=json.loads(raw);identity=hashlib.sha256(raw).hexdigest()
        assert value["study_id"]==study and study in NAMES and identity==pointer["report_sha256"]
        assert "tinker://" not in raw.decode() and len(raw)<=20000000
        directory=pathlib.Path("/public/forecast-serving")/NAMES[study];directory.mkdir(parents=True,exist_ok=True)
        target=directory/(identity+".json")
        if target.exists():assert target.read_bytes()==raw,"Immutable serving object conflict"
        else:
            with target.open("xb") as f:f.write(raw)
        entry={**pointer,"study_id":study,"published_at":datetime.now(timezone.utc).isoformat(),"github_commit":item["github_commit"],"source":"Verified mirror of canonical committed GitHub artifacts"}
        temp=directory/"index.pending";temp.write_text(json.dumps(entry,indent=2)+"\n");temp.replace(directory/"index.json")
        receipts.append({"study_id":study,"report_sha256":identity,"bytes":len(raw),"github_commit":item["github_commit"]})
    public.commit()
    return {"status":"published_verified_serving_snapshots","snapshots":receipts,"new_optimizer_updates":0,"model_calls":0,"runtime_seconds":time.monotonic()-started,"provider_cost_usd":None}
@app.local_entrypoint()
def main():
    payloads=[];commit=os.environ.get("EVIDENCE_SOURCE_SHA",os.environ.get("PUBLICATION_SOURCE_SHA",os.environ["GITHUB_SHA"]))
    for study,kind in (("direct-probability-v18","probability-v18"),("direct-evidence-v14","evidence-v14")):
        pointer=json.loads(pathlib.Path("results/"+kind+"/latest.json").read_bytes());raw=pathlib.Path(pointer["report_path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"]
        payloads.append({"study_id":study,"pointer":pointer,"raw":raw,"github_commit":commit})
    value=publish.remote(payloads);out=pathlib.Path("artifacts/forecast-serving");out.mkdir(parents=True,exist_ok=True)
    (out/"serving-receipt.json").write_text(json.dumps(value,indent=2)+"\n");print(json.dumps(value),flush=True)
