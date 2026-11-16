"""Frozen-weight sampling control; original optimizer states and selections unchanged."""
import argparse,asyncio,hashlib,json,os,time,urllib.request
from pathlib import Path
from .direct_forecast_v12 import digest,messages,parse,price_quantiles,cell_loss,summarize,matched
from .train_direct_v12 import write,now,cfg
async def evaluate(tasks,sampler,renderer,protocol,seed,arm,label,output):
    import tinker
    from tinker_cookbook.renderers import get_text_content
    sem=asyncio.Semaphore(protocol["sampling"]["concurrency"])
    async def one(t):
        prompt=renderer.build_generation_prompt(messages(t,arm))
        sample_seed=(protocol["sampling"]["seed_base"]+seed+int(t["task_id"][:7],16))%(2**31-1)
        params=tinker.SamplingParams(max_tokens=protocol["sampling"]["max_tokens"],temperature=protocol["sampling"]["temperature"],stop=renderer.get_stop_sequences())
        async with sem:
            result=await sampler.sample(prompt=prompt,num_samples=protocol["sampling"]["samples"],sampling_params=params)
        good=[];bad=[];token_count=0
        for sequence in result.sequences:
            token_count+=len(sequence.tokens)
            try:
                message,termination=renderer.parse_response(sequence.tokens)
                if hasattr(termination,"is_clean") and not termination.is_clean:raise ValueError("Unclean model termination")
                text=get_text_content(message)
                good.append(parse(text,protocol["sampling"]["min_log_return"],protocol["sampling"]["max_log_return"]))
            except (ValueError,TypeError,KeyError,OverflowError) as e:bad.append(type(e).__name__)
        failed=len(good)<protocol["sampling"]["min_valid"]
        qs=price_quantiles(good,t["anchor"]) if not failed else [[t["anchor"]]*3 for _ in (1,3,7)]
        cells=[]
        for i,h in enumerate((1,3,7)):
            y=t["outcomes"][i];v=qs[i]
            cells.append({"task_id":t["task_id"],"series_id":t["series_id"],"origin":t["origin"],"horizon_days":h,"target_date":t["target_dates"][i],"outcome":y,"q10":v[0],"q50":v[1],"q90":v[2],"loss":cell_loss(y,v),"method":label,"fallback":failed,"changed_price":y!=t["anchor"]})
        return {"task_id":t["task_id"],"series_id":t["series_id"],"origin":t["origin"],"prompt_sha256":digest(messages(t,arm)),"history_sha256":digest(t["context"]),"sampling_seed":None,"requested_samples":protocol["sampling"]["samples"],"returned_samples":len(result.sequences),"valid_samples":len(good),"invalid_samples":len(bad),"distinct_vectors":len({tuple(v) for v in good}),"sample_collapse":len(good)>0 and len({tuple(v) for v in good})==1,"output_tokens":token_count,"sample_returns":good,"sample_sha256":digest(good),"fallback":failed,"cells":cells}
    tasks_out=await asyncio.gather(*(one(t) for t in tasks));cells=[c for t in tasks_out for c in t["cells"]]
    result={"label":label,"scope":"retrospective_development" if label.startswith("dev") else "additional_retrospective_evaluation","summary":summarize(cells),"cells":cells,"tasks":tasks_out,"samples_requested":sum(t["requested_samples"] for t in tasks_out),"output_tokens":sum(t["output_tokens"] for t in tasks_out),"created_at":now()}
    write(output,result);return result

async def run(inputs,output,seed):
    import tinker
    from tinker_cookbook.renderers import get_renderer
    root=Path(inputs);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    p=cfg();q=json.loads(Path("configs/direct-sampling-v13.json").read_text());dataset=json.loads((root/"dataset.json").read_text())
    assert digest(p)==q["parent_protocol_sha256"] and digest(dataset)==q["dataset_sha256"]
    started=time.monotonic();base_url="https://raw.githubusercontent.com/howdymary/mochi-demo/compute-observatory/"
    parent=None
    for attempt in range(90):
        with urllib.request.urlopen(base_url+"results/direct-v12/latest.json",timeout=30) as response:index=json.load(response)
        with urllib.request.urlopen(base_url+index["report_path"],timeout=60) as response:raw=response.read()
        assert hashlib.sha256(raw).hexdigest()==index["report_sha256"]
        report=json.loads(raw);parent=next((r for r in report["runs"] if r["seed"]==seed),None)
        if parent:break
        await asyncio.sleep(10)
    else:
        write(out/"pending.json",{"study_id":q["study_id"],"seed":seed,"status":"pending_original_seed_completion","new_optimizer_updates":0});return
    assert parent["protocol_sha256"]==digest(p) and parent["dataset_sha256"]==digest(dataset)
    chosen=parent["selected"];client=tinker.ServiceClient(display_name="Compute Forecast v13 frozen-weight sampler control seed"+str(seed),user_metadata={"study_id":q["study_id"],"seed":str(seed),"optimizer_updates":"0"})
    base=await client.create_sampling_client(base_model=p["model"]["base"]);sampler=base
    if chosen["update"]!=0:
        rest=tinker.RestClient();runs=[]
        for offset in range(0,500,100):
            page=await rest.list_training_runs(limit=100,offset=offset)
            for r in page.training_runs:
                m=r.user_metadata or {}
                if m.get("study_id")==p["study_id"] and m.get("protocol_sha256")==digest(p) and m.get("seed")==str(seed) and m.get("arm")=="price_only" and m.get("github_run_id")==parent["github_run_id"]:runs.append(r)
            if len(page.training_runs)<100:break
        assert len(runs)==1,"Ambiguous original training identity"
        checkpoints=(await rest.list_checkpoints(runs[0].training_run_id)).checkpoints
        saved=[c for c in checkpoints if (c.user_metadata or {}).get("update")==str(chosen["update"]) and hashlib.sha256(c.tinker_path.encode()).hexdigest().startswith(chosen["checkpoint_id"])]
        assert len(saved)==1,"Frozen selected checkpoint hash mismatch"
        if saved[0].checkpoint_type=="sampler":sampler=await client.create_sampling_client(model_path=saved[0].tinker_path)
        else:
            trainer=await client.create_training_client_from_state_with_optimizer(saved[0].tinker_path)
            sampler=await trainer.save_weights_and_get_sampling_client()
    renderer=get_renderer(p["model"]["renderer"],base.get_tokenizer());tasks=dataset["groups"]["retrospective"]
    assert len(tasks)==22
    selected=await evaluate(tasks,sampler,renderer,p,seed,"price_only","selected_direct_corrected",out/"evaluation-selected.json")
    initial=await evaluate(tasks,base,renderer,p,seed,"price_only","base_direct_corrected",out/"evaluation-base.json")
    lookup={t["task_id"]:t for t in tasks}
    for value,file in ((selected,"evaluation-selected.json"),(initial,"evaluation-base.json")):
        for t in value["tasks"]:
            t["anchor"]=lookup[t["task_id"]]["anchor"];t["sampling_mode"]="batch_without_request_seed"
            assert t["requested_samples"]==q["sampling"]["samples"]==64
        write(out/file,value)
    refs={name:{"summary":r["summary"],"cells":r["cells"],"comparison":matched(selected["cells"],r["cells"])} for name,r in parent["references"].items()}
    diversity=lambda value:{"tasks":len(value["tasks"]),"collapsed_tasks":sum(t["sample_collapse"] for t in value["tasks"]),"min_distinct_vectors":min(t["distinct_vectors"] for t in value["tasks"]),"max_distinct_vectors":max(t["distinct_vectors"] for t in value["tasks"])}
    result={"study_id":q["study_id"],"seed":seed,"protocol":q,"protocol_sha256":digest(q),"parent_report_path":index["report_path"],"parent_report_sha256":index["report_sha256"],"parent_protocol_sha256":digest(p),"dataset_sha256":digest(dataset),"frozen_selection":chosen,"training_optimizer_updates":parent["optimizer_updates"],"new_optimizer_updates":0,"new_persistent_checkpoints":0,"source_sha":os.environ["GITHUB_SHA"],"workflow_run_id":os.environ["GITHUB_RUN_ID"],"created_at":now(),"runtime_seconds":time.monotonic()-started,"provider_cost_usd":None,"base":initial["summary"],"selected":selected["summary"],"comparison_to_base":matched(selected["cells"],initial["cells"]),"references":refs,"diversity":{"base":diversity(initial),"selected":diversity(selected)},"original_fixed_seed_results":{"base":parent["base"],"selected":parent["retrospective"]},"classification":q["interpretation"],"status":"completed"}
    write(out/"result.json",result);print("SAMPLING_CONTROL_COMPLETED "+json.dumps({k:result[k] for k in ("seed","base","selected","diversity","new_optimizer_updates")}),flush=True)
def main():
    a=argparse.ArgumentParser();a.add_argument("--inputs",required=True);a.add_argument("--output",required=True);a.add_argument("--seed",type=int,required=True);v=a.parse_args()
    asyncio.run(run(v.inputs,v.output,v.seed))
if __name__=="__main__":main()
