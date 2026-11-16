"""Read authenticated study checkpoint metadata without publishing resource paths."""
import asyncio,hashlib,json,pathlib
async def main():
    import tinker
    p=json.loads(pathlib.Path("configs/direct-forecast-v12.json").read_text());rest=tinker.RestClient();runs=[]
    for offset in range(0,500,100):
        page=await rest.list_training_runs(limit=100,offset=offset)
        for r in page.training_runs:
            m=r.user_metadata or {}
            if m.get("study_id")!=p["study_id"]:continue
            checkpoints=await rest.list_checkpoints(r.training_run_id)
            runs.append({"seed":m.get("seed"),"arm":m.get("arm"),"protocol_sha256":m.get("protocol_sha256"),"training_identity_sha256":hashlib.sha256(r.training_run_id.encode()).hexdigest(),"checkpoints":[{"type":c.checkpoint_type,"update":(c.user_metadata or {}).get("update"),"resource_sha256":hashlib.sha256(c.tinker_path.encode()).hexdigest()} for c in checkpoints.checkpoints]})
        if len(page.training_runs)<100:break
    root=pathlib.Path("artifacts/direct-v12-status");root.mkdir(parents=True,exist_ok=True)
    (root/"status.json").write_text(json.dumps({"study_id":p["study_id"],"runs":runs,"private_paths_exposed":False},indent=2)+"\n")
    print(json.dumps({"study_id":p["study_id"],"runs":runs},indent=2))
asyncio.run(main())
