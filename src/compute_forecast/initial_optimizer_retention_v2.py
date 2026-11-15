"""Remove only redundant v2 zero-update optimizer copies, preserving all reported models."""
from __future__ import annotations
import hashlib,json,os,re,uuid
from pathlib import Path
import modal
from .starter_probe import volume
app=modal.App("compute-forecast-v2-initial-optimizer-cleanup")
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
@app.function(image=image,cpu=.25,memory=512,timeout=90,volumes={"/data":volume})
def records():
    volume.reload();return [json.loads(p.read_text()) for p in Path("/data/campaign-v2/policies").glob("*.json")]
@app.function(image=image,cpu=.25,memory=512,timeout=90,volumes={"/data":volume})
def save(audit,changed):
    volume.reload()
    for p in changed:
        if p["mode"]!="sft" or not re.fullmatch("[a-f0-9]{32}",p["run_id"]):raise ValueError("Unexpected record")
        root=Path("/data/campaign-v2/policies");(root/(p["run_id"]+".json")).write_text(json.dumps(p,sort_keys=True,indent=2))
    root=Path("/data/campaign-v2/storage-audit");root.mkdir(exist_ok=True)
    (root/(audit["audit_id"]+".json")).write_text(json.dumps(audit,sort_keys=True,indent=2));volume.commit()
@app.local_entrypoint()
def main():
    import tinker
    all_records=records.remote();protected=set()
    for p in all_records:
        protected.update(c["sampler_path"] for c in p.get("checkpoints",[]))
        selected=p.get("selected") or {}
        protected.update(selected[k] for k in ("state_path","sampler_path") if selected.get(k))
        protected.update(c["state_path"] for c in p.get("recovery_states",[]))
        if p["mode"]=="rl":protected.update(c["state_path"] for c in p.get("checkpoints",[]))
    candidates=[]
    for p in all_records:
        if p["mode"]!="sft" or p.get("selected",{}).get("update",0)==0:continue
        c=next((c for c in p["checkpoints"] if c["update"]==0),None)
        if c is None or c.get("optimizer_state_status")=="redundant_zero_state_removed":continue
        path=c["state_path"]
        if path in protected or not re.fullmatch(r"tinker://[^/]+/weights/v2_sft_0",path):raise ValueError("Refused noninitial or protected deletion")
        candidates.append((p,c))
    if len(candidates)>6:raise ValueError("Unexpected campaign cleanup scope")
    rest=tinker.RestClient()
    # Verify every reported model counterpart before any deletion.
    for p,c in candidates:rest.get_weights_info_by_tinker_path(c["sampler_path"]).result()
    audit={"audit_id":uuid.uuid4().hex,"source_sha":os.environ["GITHUB_SHA"],"scope":"New v2 zero-update optimizer copies only; all reported sampler IDs and selected/RL recovery states preserved","removed":[]}
    changed=[]
    for p,c in candidates:
        rest.delete_checkpoint_from_tinker_path(c["state_path"]).result()
        rest.get_weights_info_by_tinker_path(c["sampler_path"]).result()
        c["optimizer_state_status"]="redundant_zero_state_removed"
        audit["removed"].append({"seed":p["seed"],"objective":p["objective"],"removed_optimizer_copy_id":hashlib.sha256(c["state_path"].encode()).hexdigest()[:20],"preserved_reported_checkpoint_id":c["checkpoint_id"],"selected_update":p["selected"]["update"]})
        changed.append(p)
    save.remote(audit,changed)
    out=Path("artifacts/v2-retention");out.mkdir(parents=True,exist_ok=True);(out/"retention.json").write_text(json.dumps(audit,indent=2))
    print("V2_INITIAL_STATE_RETENTION:"+json.dumps(audit),flush=True)
