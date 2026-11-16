"""Confirm corrected stochastic sampling before any paired optimization."""
import asyncio,json,pathlib
from compute_forecast.direct_forecast_v12 import digest,parse,price_quantiles
from compute_forecast.evidence_v14 import messages
async def main():
    import tinker
    from tinker_cookbook.renderers import get_renderer,get_text_content
    p=json.loads(pathlib.Path("configs/direct-evidence-v14-final.json").read_text());dataset=json.loads(pathlib.Path("inputs/evidence-v14/dataset.json").read_text())
    assert dataset["protocol_sha256"]==digest(p)
    rest=tinker.RestClient();checkpoints=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);checkpoints.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    assert len(checkpoints)+p["limits"]["max_persistent_checkpoints"]<100,"Insufficient free checkpoint headroom; do not delete or change billing automatically"
    service=tinker.ServiceClient(display_name="Compute Forecast v14 matched sampling preflight");sampler=await service.create_sampling_client(base_model=p["model"]["base"]);renderer=get_renderer(p["model"]["renderer"],sampler.get_tokenizer())
    tasks=sorted(dataset["groups"]["development"],key=lambda t:(t["series_id"],t["origin"]))[::10];rows=[]
    for arm in p["arms"]:
        for task in tasks:
            prompt=renderer.build_generation_prompt(messages(task,arm))
            value=await sampler.sample(prompt=prompt,num_samples=8,sampling_params=tinker.SamplingParams(max_tokens=128,temperature=.8,stop=renderer.get_stop_sequences()))
            vectors=[]
            for sequence in value.sequences:
                try:
                    msg,_=renderer.parse_response(sequence.tokens);vectors.append(parse(get_text_content(msg)))
                except (ValueError,TypeError):pass
            assert len(vectors)>=6,"Unadapted model failed parsing preflight"
            quantiles=price_quantiles(vectors,task["anchor"])
            assert all(0<q[0]<=q[1]<=q[2] for q in quantiles)
            rows.append({"arm":arm,"task_id":task["task_id"],"requested":8,"valid":len(vectors),"distinct":len({tuple(v) for v in vectors}),"sample_returns":vectors,"quantiles":quantiles,"prompt_tokens":prompt.length,"sampling_seed":None})
    for arm in p["arms"]:assert any(r["distinct"]>=2 for r in rows if r["arm"]==arm),"No diversity in this arm's preflight"
    out=pathlib.Path("inputs/evidence-v14/sampling-preflight.json");out.write_text(json.dumps({"status":"passed","checkpoint_count":len(checkpoints),"headroom_required":p["limits"]["max_persistent_checkpoints"],"rows":rows,"selection_use":"Parsing/diversity only; no forecast-score tuning","new_optimizer_updates":0},indent=2)+"\n")
    print(json.dumps({"status":"passed","checkpoint_count":len(checkpoints),"rows":[{k:v for k,v in r.items() if k not in ("sample_returns","quantiles")} for r in rows]}),flush=True)
if __name__=="__main__":asyncio.run(main())
