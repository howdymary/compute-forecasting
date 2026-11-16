"""Bounded sampler-diversity diagnostic; does not optimize or revise frozen results."""
import asyncio,hashlib,json,os,pathlib,time
from datetime import datetime,timezone
from compute_forecast.direct_forecast_v12 import digest,messages,parse
async def main():
    import tinker
    from tinker_cookbook.renderers import get_renderer,get_text_content
    p=json.loads(pathlib.Path("configs/direct-forecast-v12.json").read_text())
    data=json.loads(pathlib.Path("inputs/direct-v12/dataset.json").read_text())
    assert data["protocol_sha256"]==digest(p)
    client=tinker.ServiceClient(display_name="Compute Forecast v12 sample independence audit",user_metadata={"study_id":"direct-v12-sampling-diagnostic","optimizer_updates":"0"})
    base=await client.create_sampling_client(base_model=p["model"]["base"])
    renderer=get_renderer(p["model"]["renderer"],base.get_tokenizer())
    tasks=sorted(data["groups"]["development"],key=lambda t:(t["series_id"],t["origin"]))
    chosen=[tasks[0],next(t for t in tasks if t["series_id"].startswith("fastgpu_daily."))]
    observations=[];start=time.monotonic()
    async def sample(sampler,prompt,seed,n):
        kwargs={"max_tokens":128,"temperature":.8,"stop":renderer.get_stop_sequences()}
        if seed is not None:kwargs["seed"]=seed
        result=await sampler.sample(prompt=prompt,num_samples=n,sampling_params=tinker.SamplingParams(**kwargs))
        rows=[]
        for sequence in result.sequences:
            message,_=renderer.parse_response(sequence.tokens);text=get_text_content(message)
            try:vector=parse(text)
            except (ValueError,TypeError):vector=None
            rows.append({"token_sha256":digest(sequence.tokens),"text_sha256":hashlib.sha256(text.encode()).hexdigest(),"return_vector":vector,"token_count":len(sequence.tokens)})
        return rows
    for task in chosen:
        prompt=renderer.build_generation_prompt(messages(task));fixed=120000+17+int(task["task_id"][:7],16)
        for mode in ("batch_fixed_seed","batch_unset_seed","individual_distinct_seeds"):
            if mode=="batch_fixed_seed":rows=await sample(base,prompt,fixed%(2**31-1),8)
            elif mode=="batch_unset_seed":rows=await sample(base,prompt,None,8)
            else:
                batches=await asyncio.gather(*(sample(base,prompt,(fixed+i)%(2**31-1),1) for i in range(8)))
                rows=[r for batch in batches for r in batch]
            valid=[r["return_vector"] for r in rows if r["return_vector"] is not None]
            record={"task_id":task["task_id"],"series_id":task["series_id"],"origin":task["origin"],"mode":mode,"prompt_sha256":digest(messages(task)),"samples":len(rows),"valid_samples":len(valid),"distinct_token_sequences":len({r["token_sha256"] for r in rows}),"distinct_vectors":len({tuple(v) for v in valid}),"rows":rows}
            observations.append(record);print(json.dumps({k:v for k,v in record.items() if k!="rows"}),flush=True)
    control=renderer.build_generation_prompt([{"role":"user","content":"Name one animal. Choose freely; return only its common name."}])
    for mode,seed in (("batch_fixed_seed",731),("batch_unset_seed",None)):
        rows=await sample(base,control,seed,8)
        observations.append({"task_id":"nonmarket_diversity_control","mode":mode,"samples":8,"distinct_token_sequences":len({r["token_sha256"] for r in rows}),"rows":rows})
    out=pathlib.Path("artifacts/direct-v12-diagnostics");out.mkdir(parents=True,exist_ok=True)
    report={"study_id":"direct-v12-sampling-diagnostic","created_at":datetime.now(timezone.utc).isoformat(),"source_sha":os.environ["GITHUB_SHA"],"workflow_run_id":os.environ["GITHUB_RUN_ID"],"model":p["model"]["base"],"protocol_sha256":digest(p),"classification":"Post-hoc implementation diagnostic on development prompts; not a new accuracy result","new_optimizer_updates":0,"persistent_checkpoints_created":0,"inference_sequences":sum(r["samples"] for r in observations),"runtime_seconds":time.monotonic()-start,"provider_cost_usd":None,"observations":observations,"original_results_preserved":True}
    (out/"sampling.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
if __name__=="__main__":asyncio.run(main())
