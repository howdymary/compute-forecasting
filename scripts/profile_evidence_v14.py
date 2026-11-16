"""Reconstruct registered training batches and token counts; not provider billing."""
import asyncio,json,os,pathlib,random
from compute_forecast.direct_forecast_v12 import digest
from compute_forecast.evidence_v14 import messages,conversation
async def main():
    import tinker
    from tinker_cookbook.renderers import get_renderer,TrainOnWhat
    from tinker_cookbook.supervised.data import conversation_to_datum
    p=json.loads(pathlib.Path("configs/direct-evidence-v14-final.json").read_text());data=json.loads(pathlib.Path("inputs/evidence-v14/dataset.json").read_text());assert data["protocol_sha256"]==digest(p)
    service=tinker.ServiceClient(display_name="Compute Forecast v14 deterministic resource accounting",user_metadata={"study_id":"direct-evidence-v14-resource-accounting","optimizer_updates":"0"});sampler=await service.create_sampling_client(base_model=p["model"]["base"]);tokenizer=sampler.get_tokenizer();renderer=get_renderer(p["model"]["renderer"],tokenizer)
    groups={}
    for arm in p["arms"]:
        rows=[]
        for task in data["groups"]["training"]:
            datum=conversation_to_datum(conversation(task,arm),renderer,max_length=p["model"]["max_context_tokens"],train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE)
            assert datum is not None
            rows.append({"task_id":task["task_id"],"generation_prompt_tokens":renderer.build_generation_prompt(messages(task,arm)).length,"training_sequence_tokens":datum.model_input.length,"completion_loss_tokens":int(sum(datum.loss_fn_inputs["weights"].tolist()))})
        groups[arm]=rows
    runs=[]
    for seed in p["model"]["seeds"]:
        rng=random.Random(seed);batches=[[rng.randrange(len(data["groups"]["training"])) for _ in range(p["model"]["batch_size"])] for _ in range(p["model"]["max_updates"])]
        ids=[[data["groups"]["training"][i]["task_id"] for i in batch] for batch in batches]
        for arm in p["arms"]:
            per_update=[{"update":j+1,"training_sequence_tokens":sum(groups[arm][i]["training_sequence_tokens"] for i in batch),"completion_loss_tokens":sum(groups[arm][i]["completion_loss_tokens"] for i in batch)} for j,batch in enumerate(batches)]
            runs.append({"arm":arm,"seed":seed,"optimizer_updates":100,"example_presentations":1600,"batch_task_order_sha256":digest(ids),"training_sequence_tokens":sum(r["training_sequence_tokens"] for r in per_update),"completion_loss_tokens":sum(r["completion_loss_tokens"] for r in per_update),"per_update":per_update})
    for seed in p["model"]["seeds"]:
        paired=[r for r in runs if r["seed"]==seed];assert paired[0]["batch_task_order_sha256"]==paired[1]["batch_task_order_sha256"]
        assert paired[0]["completion_loss_tokens"]==paired[1]["completion_loss_tokens"]
    report={"study_id":"direct-evidence-v14-resource-accounting","source_sha":os.environ["GITHUB_SHA"],"protocol_sha256":digest(p),"dataset_sha256":digest(data),"model":p["model"]["base"],"tokenizer_revision":getattr(tokenizer,"init_kwargs",{}).get("_commit_hash"),"scope":"Deterministic reconstruction of registered batches; actual successful-update reconciliation occurs after run completion. These are not provider-billed token counts or dollar receipts.","catalog":groups,"runs":runs,"new_optimizer_updates":0,"provider_cost_usd":None}
    out=pathlib.Path("artifacts/evidence-v14-audit");out.mkdir(parents=True,exist_ok=True);(out/"resource-profile.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("catalog","runs")}),flush=True)
if __name__=="__main__":asyncio.run(main())
