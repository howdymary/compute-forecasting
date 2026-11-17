"""Verify documented optimizer restoration and the frozen categorical model before optimization."""
import asyncio,hashlib,json,os,pathlib
from compute_forecast.probability_v18 import digest
from compute_forecast.continuation_v21 import batches,batch_identity,validate_training
from compute_forecast.continuation_eval_v21 import evaluate,compatibility
from compute_forecast.train_market_v19 import write
def read(p):return json.loads(pathlib.Path(p).read_bytes())
async def main():
    import tinker
    from tinker_cookbook.renderers import get_renderer
    from tinker_cookbook.recipes.decisions import DecisionRenderer
    from compute_forecast.market_state_v19 import decision
    p=read("configs/ce-continuation-v21.json");data=read("inputs/ce-continuation-v21/dataset.json");audit=read("inputs/ce-continuation-v21/audit.json")
    assert digest(data)==audit["dataset_sha256"] and data["protocol_sha256"]==digest(p)
    parent_raw=pathlib.Path(p["parent"]["report_path"]).read_bytes();assert hashlib.sha256(parent_raw).hexdigest()==p["parent"]["report_sha256"]
    report=json.loads(parent_raw);old=next(r for r in report["runs"] if r["arm"]=="price" and r["seed"]==17)
    assert old["selected"]["checkpoint_id"]==p["parent"]["checkpoint_id"] and old["selected"]["update"]==30
    assert old["model"]["learning_rate"]/5==p["model"]["learning_rate"] and old["model"]["batch_size"]==p["model"]["batch_size"]
    rest=tinker.RestClient();items=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);items.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    matches=[c for c in items if hashlib.sha256(c.tinker_path.encode()).hexdigest()[:24]==p["parent"]["checkpoint_id"] and (c.user_metadata or {}).get("study_id")=="market-state-v19"]
    assert len(matches)==1,"Frozen parent unavailable"
    arms=["same"]+(["expanded"] if data["expanded_ready"] else []);capacity=len(items)+3*len(arms)<=100
    result={"study_id":p["study_id"],"protocol_sha256":digest(p),"dataset_sha256":digest(data),"parent_report_sha256":p["parent"]["report_sha256"],"arms":arms,"training_ready":False,"storage":{"current_states":len(items),"pilot_reserved_states":3*len(arms),"max_campaign_new_states":18,"deletion_performed":False},"optimizer_restore":{"method":"create_training_client_from_state_with_optimizer","status":"pending","silent_reset_allowed":False},"reasons":[],"new_optimizer_updates":0,"new_model_calls":0,"provider_cost_usd":None}
    root=pathlib.Path("artifacts/ce-continuation-v21-preflight")
    if not capacity:result["reasons"].append("insufficient_checkpoint_preservation_capacity")
    else:
        service=tinker.ServiceClient(display_name="Compute Forecast v21 optimizer restoration preflight",user_metadata={"study_id":p["study_id"],"phase":"restore_preflight","optimizer_updates":"0"})
        try:
            trainer=await service.create_training_client_from_state_with_optimizer(matches[0].tinker_path,user_metadata={"study_id":p["study_id"],"phase":"restore_preflight","optimizer_updates":"0"})
            result["optimizer_restore"]["status"]="documented_restore_succeeded"
        except Exception as exc:
            result["optimizer_restore"]["status"]="failed";result["optimizer_restore"]["error_type"]=type(exc).__name__;result["reasons"].append("optimizer_restoration_unavailable")
        if result["optimizer_restore"]["status"]=="documented_restore_succeeded":
            tok=trainer.get_tokenizer();assert hashlib.sha256(tok.backend_tokenizer.to_str().encode()).hexdigest()==p["parent"]["tokenizer_sha256"]
            renderer=DecisionRenderer(get_renderer(p["model"]["renderer"],tok));sampler=await trainer.save_weights_and_get_sampling_client(kind="snapshot")
            maximum={}
            for arm in arms:
                validate_training(data["training"][arm],p)
                maximum[arm]=max(len(renderer.render(decision({**t,"arm":"price"},h,data["log_levels"])).tokens) for t in data["training"][arm] for h in p["data"]["horizons"])
            result["max_prompt_tokens"]=maximum
            if any(v>p["model"]["max_context_tokens"] for v in maximum.values()):result["reasons"].append("registered_context_limit_exceeded")
            incumbent={}
            for phase in ("development","retrospective"):
                incumbent[phase]=await evaluate(data["groups"][phase],sampler,renderer,data["log_levels"],p,"incumbent")
            result["new_model_calls"]=sum(len(v["cells"]) for v in incumbent.values())
            retained_dev={"cells":[r for c in report["cases"] for cp in c["checkpoints"] if cp["arm"]=="price" and cp["seed"]==17 and cp["update"]==30 for r in cp["rows"]],"summary":old["selected"]["development"]}
            result["compatibility"]={"development":compatibility(incumbent["development"],retained_dev),"retrospective":compatibility(incumbent["retrospective"],old["retrospective"])}
            if any(not v["quantiles_match"] or v["failures"] for v in result["compatibility"].values()):result["reasons"].append("restored_incumbent_differs_from_retained_forecasts")
            write(root/"incumbent.json",incumbent)
            result["ordering_hashes"]={arm:batch_identity(batches(data["training"][arm],17,100,16,480)) for arm in arms}
    result["training_ready"]=not result["reasons"];write(root/"readiness.json",result)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a") as f:f.write("ready="+str(result["training_ready"]).lower()+"\narms="+json.dumps(arms,separators=(",",":"))+"\n")
    print(json.dumps(result),flush=True)
if __name__=="__main__":asyncio.run(main())
