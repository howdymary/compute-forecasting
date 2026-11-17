"""Read-only probability API, tokenizer, gradient and storage audit before optimization."""
import asyncio,hashlib,importlib.metadata,json,pathlib,sys
from compute_forecast.probability_v18 import digest,decision,datum,custom_loss,probabilities
async def main():
    import tinker,torch
    from tinker_cookbook.renderers import get_renderer
    from tinker_cookbook.recipes.decisions import DecisionRenderer,sample_decision
    p=json.loads(pathlib.Path("configs/direct-probability-v18.json").read_text());data=json.loads(pathlib.Path("inputs/probability-v18/dataset.json").read_text())
    audit=json.loads(pathlib.Path("inputs/probability-v18/audit.json").read_text());assert digest(data)==audit["dataset_sha256"]
    result={"study_id":p["study_id"],"dataset_sha256":digest(data),"data_ready":audit["training_ready"],"new_optimizer_updates":0,"training_ready":False,"gate_reasons":list(audit["gate_reasons"]),"packages":{x:importlib.metadata.version(x) for x in ("tinker","tinker-cookbook","torch","transformers","numpy")},"provider_cost_usd":None}
    rest=tinker.RestClient();items=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);items.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    result["existing_checkpoint_count"]=len(items);result["required_new_headroom"]=p["limits"]["max_new_persistent_states"]+2
    if len(items)+result["required_new_headroom"]>=100:result["gate_reasons"].append("insufficient_checkpoint_headroom_existing_resources_not_deleted")
    out=pathlib.Path("artifacts/probability-v18-audit");out.mkdir(parents=True,exist_ok=True)
    (out/"preflight-start.json").write_text(json.dumps(result,indent=2)+"\n")
    service=tinker.ServiceClient(display_name="Compute Forecast probability v18 read-only preflight",user_metadata={"study_id":p["study_id"],"phase":"read_only_preflight"})
    sampler=await service.create_sampling_client(base_model=p["model"]["base"]);tok=sampler.get_tokenizer();base=get_renderer(p["model"]["renderer"],tok);renderer=DecisionRenderer(base)
    result["tokenizer"]={"class":type(tok).__name__,"backend_sha256":hashlib.sha256(tok.backend_tokenizer.to_str().encode()).hexdigest(),"revision":tok.init_kwargs.get("_commit_hash"),"base_weight_revision":None,"revision_limit":"Provider weight revision unavailable; same registered base model used across the campaign"}
    task=sorted(data["groups"]["training"],key=lambda t:(t["series_id"],t["origin"]))[0];rendering=renderer.render(decision(task,7,data["log_levels"]))
    result["choice_count"]=len(rendering.labels);result["choice_token_ids"]=[rendering.label_tokens[x] for x in rendering.labels]
    assert result["choice_count"]==p["distribution"]["n_levels"] and len(set(result["choice_token_ids"]))==p["distribution"]["n_levels"]
    result["prompt_tokens"]=len(rendering.tokens);assert len(rendering.tokens)<=p["model"]["max_context_tokens"]
    repeats=[await sample_decision(sampler,rendering) for _ in range(3)]
    result["repeated_probabilities"]=repeats;result["max_repeat_probability_difference"]=max(abs(repeats[0][k]-r[k]) for r in repeats for k in repeats[0])
    assert result["max_repeat_probability_difference"]<1e-4,"Target-logprob readout unstable"
    result["gradient_checks"]=[]
    for objective in ("ce","crps"):
        d=datum(task,7,data["log_levels"],renderer);n=d.model_input.length
        lp=torch.linspace(-4.,-1.,p["distribution"]["n_levels"]).repeat(n,1).requires_grad_();fn=custom_loss(objective,data["crps_scale"])
        loss,metrics=fn([d],[lp]);loss.backward();grad=lp.grad[-1].clone();assert torch.isfinite(grad).all() and grad.abs().sum()>0
        direction=torch.linspace(-1.,1.,p["distribution"]["n_levels"]);eps=.001
        plus=lp.detach().clone();minus=lp.detach().clone();plus[-1]+=eps*direction;minus[-1]-=eps*direction
        numerical=float((fn([d],[plus])[0]-fn([d],[minus])[0])/(2*eps));analytic=float((grad*direction).sum())
        assert abs(numerical-analytic)<.002+abs(analytic)*.02,"Finite-difference gradient mismatch"
        result["gradient_checks"].append({"objective":objective,"loss":float(loss.detach()),"gradient_l1":float(grad.abs().sum()),"directional_analytic":analytic,"directional_numeric":numerical})
    result["training_ready"]=not result["gate_reasons"]
    out=pathlib.Path("artifacts/probability-v18-audit");out.mkdir(parents=True,exist_ok=True)
    (out/"preflight.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    pathlib.Path("inputs/probability-v18/preflight.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:result[k] for k in ("study_id","training_ready","gate_reasons","existing_checkpoint_count","choice_count","max_repeat_probability_difference","gradient_checks")}),flush=True)
    if not result["training_ready"]:sys.exit(2)
if __name__=="__main__":asyncio.run(main())
