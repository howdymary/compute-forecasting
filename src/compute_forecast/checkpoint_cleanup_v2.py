"""Clean only consumed v2 RL rollout samplers; preserve evaluated and recovery states."""
from __future__ import annotations
import hashlib,json,os,re,uuid
from pathlib import Path
import modal
from .starter_probe import volume
app=modal.App("compute-forecast-v2-storage-cleanup")
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
@app.function(image=image,cpu=.25,memory=512,timeout=90,volumes={"/data":volume})
def private_records():
    volume.reload();return [json.loads(p.read_text()) for p in Path("/data/campaign-v2/policies").glob("*.json")]
@app.function(image=image,cpu=.25,memory=512,timeout=90,volumes={"/data":volume})
def retain(audit):
    volume.reload();root=Path("/data/campaign-v2/storage-audit");root.mkdir(parents=True,exist_ok=True)
    (root/(audit["audit_id"]+".json")).write_text(json.dumps(audit,sort_keys=True,indent=2));volume.commit()
@app.local_entrypoint()
def main(inputs:str="inputs/failed-rl"):
    import tinker
    records=private_records.remote();protected=set()
    for p in records:
        for c in p.get("checkpoints",[]):
            protected.update(c[k] for k in ("state_path","sampler_path") if k in c)
        for c in p.get("recovery_states",[]):protected.add(c["state_path"])
    rest=tinker.RestClient();audit={"audit_id":uuid.uuid4().hex,"source_sha":os.environ["GITHUB_SHA"],"deleted":[],"preserved_paths_count":len(protected),"runs":[]}
    for p in records:
        if p["mode"]!="rl" or p["created_at"]<"2026-11-15T04:13:00":continue
        if not p.get("checkpoints"):continue
        training_id=p["checkpoints"][0]["state_path"].split("/")[2]
        before=rest.list_checkpoints(training_id).result().checkpoints
        for c in before:
            path=c.tinker_path
            if path in protected:continue
            if not re.fullmatch(r"tinker://"+re.escape(training_id)+r"/sampler_weights/v2_rl_rollout_\d+",path):continue
            rest.delete_checkpoint_from_tinker_path(path).result()
            audit["deleted"].append({"checkpoint_id":hashlib.sha256(path.encode()).hexdigest()[:20],"kind":"temporary_rollout_sampler"})
        after=rest.list_checkpoints(training_id).result().checkpoints
        updates_files=[]
        for f in Path(inputs).rglob("updates.json"):
            if f"rl-{p['seed']}" in str(f):updates_files.append(f)
        updates=json.loads(updates_files[0].read_text()) if updates_files else []
        trajectories_files=[f for f in Path(inputs).rglob("rl-trajectories.json") if f"rl-{p['seed']}" in str(f)]
        trajectories=json.loads(trajectories_files[0].read_text()) if trajectories_files else []
        audit["runs"].append({"run_id":p["run_id"],"seed":p["seed"],"objective":p["objective"],"checkpoints_before":len(before),"checkpoints_after":len(after),
          "executed_optimizer_updates":len(updates),"last_sampled_iteration":max((r["step"] for r in trajectories),default=0),
          "saved_optimizer_updates":p.get("completed_optimizer_updates",0),
          "recovery_states":[{k:v for k,v in c.items() if k!="state_path"} for c in p.get("recovery_states",[])]})
    retain.remote(audit)
    out=Path("artifacts/v2-storage");out.mkdir(parents=True,exist_ok=True)
    (out/"cleanup.json").write_text(json.dumps(audit,indent=2))
    print("V2_STORAGE_CLEANUP:"+json.dumps(audit),flush=True)
