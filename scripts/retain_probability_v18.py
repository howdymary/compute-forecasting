"""Retain the two frozen operational probability states, without copies or optimization."""
import asyncio,hashlib,json,math,os,pathlib
from datetime import datetime,timezone
from compute_forecast.probability_v18 import digest
async def main():
    pointer=json.loads(pathlib.Path("results/probability-v18/latest.json").read_bytes())
    raw=pathlib.Path(pointer["report_path"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"]
    report=json.loads(raw);p=report["config"];assert digest(p)==report["protocol_sha256"]
    root=pathlib.Path("artifacts/probability-v18-future-lock");root.mkdir(parents=True,exist_ok=True)
    ready=report["status"]=="completed" and len(report["runs"])==6
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a") as f:f.write("ready="+str(ready).lower()+"\n")
    if not ready:
        value={"study_id":"direct-probability-v18-prospective","status":"gated_pending_complete_training","completed_final_runs":len(report["runs"]),"source_report_sha256":pointer["report_sha256"],"new_optimizer_updates":0,"new_checkpoints":0}
        (root/"readiness.json").write_text(json.dumps(value,indent=2)+"\n");print(json.dumps(value));return
    import tinker
    preflight=json.loads(pathlib.Path(report["preflight_path"]).read_bytes())
    rest=tinker.RestClient();available=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);available.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    expiry=datetime(2027,3,15,tzinfo=timezone.utc);ttl=math.ceil((expiry-datetime.now(timezone.utc)).total_seconds())
    assert 3600<=ttl<=150*86400;rows=[]
    for obj in ("ce","crps"):
        run=next(r for r in report["runs"] if r["objective"]==obj and r["seed"]==17);cp=run["selected"]
        row={"objective":obj,"seed":17,"selected_update":cp["update"],"checkpoint_id":cp.get("checkpoint_id"),"learning_rate":run["learning_rate"]}
        if cp["update"]==0:row["status"]="public_base_requires_no_storage"
        else:
            matches=[c for c in available if hashlib.sha256(c.tinker_path.encode()).hexdigest()[:24]==cp["checkpoint_id"]]
            assert len(matches)==1,"Selected state missing or ambiguous";c=matches[0];meta=c.user_metadata or {}
            assert meta.get("study_id")==p["study_id"] and meta.get("objective")==obj and str(meta.get("seed"))=="17"
            assert c.checkpoint_type=="training"
            await rest.set_checkpoint_ttl_from_tinker_path(c.tinker_path,ttl_seconds=ttl)
            row.update(status="ttl_update_accepted",requested_expiration_utc=expiry.isoformat())
        rows.append(row)
    lock={"study_id":"direct-probability-v18-model-lock","protocol_sha256":report["protocol_sha256"],"dataset_sha256":report["dataset_sha256"],"source_report_path":pointer["report_path"],"source_report_sha256":pointer["report_sha256"],"selected_by":"Original development seven-day pinball; seed17 fixed by the separately registered transfer panel","tokenizer_sha256":preflight["tokenizer"]["backend_sha256"],"base_weight_revision":None,"log_levels":report["log_levels"],"records":rows,"new_optimizer_updates":0,"new_checkpoints":0,"private_paths_published":False,"billing_changed":False}
    (root/"model-lock.json").write_text(json.dumps(lock,indent=2,sort_keys=True)+"\n")
    target=pathlib.Path("inputs/probability-v18-future");target.mkdir(parents=True,exist_ok=True)
    (target/"model-lock.json").write_text(json.dumps(lock,indent=2,sort_keys=True)+"\n")
    print(json.dumps(lock),flush=True)
if __name__=="__main__":asyncio.run(main())
