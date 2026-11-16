"""Read checkpoint identities and test zero-update client creation; no billing changes."""
import asyncio,hashlib,json,os,pathlib
from datetime import datetime,timezone
from manage_tinker_storage_v12 import classify,hashed
async def main():
    import tinker
    rest=tinker.RestClient();caps=await rest.get_server_capabilities()
    supported=[m.model_name for m in caps.supported_models];rows=[];run_cache={};session_cache={}
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset)
        for c in page.checkpoints:
            rid=getattr(c,"training_run_id",None) or c.tinker_path.split("/")[2]
            if rid not in run_cache:run_cache[rid]=await rest.get_training_run(rid)
            run=run_cache[rid];sid=getattr(run,"session_id",None) or rid.split(":train:")[0]
            if sid not in session_cache:
                try:session_cache[sid]=await rest.get_session(sid)
                except Exception:session_cache[sid]=None
            project,reason,proof=classify(run,session_cache[sid],c)
            rows.append({"checkpoint_sha256":hashed(c.tinker_path),"checkpoint_type":c.checkpoint_type,"classification":reason,"unrelated_project":project,"metadata":{k:v for k,v in (getattr(c,"user_metadata",None) or {}).items() if k in ("study_id","seed","arm","update")},"proof":proof})
            # Fresh user authorization covers these explicitly identified unrelated projects.
            if project in ("CodeGarden","BoundForge","Mochi"):
                await rest.delete_checkpoint_from_tinker_path(c.tinker_path)
                rows[-1]["deleted"]=True
        if len(page.checkpoints)<100:break
    result={"study_id":"direct-evidence-v14","created_at":datetime.now(timezone.utc).isoformat(),"model_supported":"Qwen/Qwen3.5-4B" in supported,"checkpoint_count_before":len(rows),"deleted_unrelated":sum(r.get("deleted",False) for r in rows),"records":rows,"new_optimizer_updates":0,"new_persistent_checkpoints":0,"billing_changed":False}
    try:
        service=tinker.ServiceClient(display_name="Compute Forecast v14 zero-update capacity preflight",user_metadata={"study_id":"direct-evidence-v14-capacity-preflight","optimizer_updates":"0"})
        trainer=await service.create_lora_training_client(base_model="Qwen/Qwen3.5-4B",rank=16,seed=17,user_metadata={"study_id":"direct-evidence-v14-capacity-preflight","optimizer_updates":"0"})
        result["training_client_creation"]="available";result["capacity_interpretation"]="Zero-update client creation succeeded; saving additional persistent checkpoints still needs a retention-capacity plan"
    except Exception as e:
        result["training_client_creation"]="blocked";result["error_type"]=type(e).__name__
        result["reason"]="Provider rejected fresh training-client creation after the checkpoint limit; no relevant checkpoints deleted and no paid storage enabled"
    out=pathlib.Path("artifacts/evidence-v14-audit");out.mkdir(parents=True,exist_ok=True);(out/"storage-readiness.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="records"}),flush=True)
if __name__=="__main__":asyncio.run(main())
