"""Tinker SFT on observed GPU-price return vectors; resources remain in Tinker."""
from __future__ import annotations
import argparse,asyncio,hashlib,importlib.metadata,json,math,os,random,re,statistics,time
from pathlib import Path
from datetime import datetime,timezone
from .direct_forecast_v12 import digest,messages,conversation,parse,price_quantiles,cell_loss,summarize,matched
def now():return datetime.now(timezone.utc).isoformat()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);raw=json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n"
    temp=path.with_suffix(path.suffix+".pending");temp.write_text(raw);temp.replace(path)
def cfg():return json.loads(Path("configs/direct-forecast-v12.json").read_text())
def reference_cells(tasks,baselines,method):
    lookup={(r["series_id"],r["origin_date"],int(r["horizon_days"])):r for r in baselines if r["method"]==method}
    cells=[]
    for t in tasks:
        for i,h in enumerate((1,3,7)):
            r=lookup.get((t["series_id"],t["origin"],h))
            if r is None:raise ValueError("Native reference missing an eligible cell")
            qs=[float(r[k]) for k in ("q10","q50","q90")]
            cells.append({"task_id":t["task_id"],"series_id":t["series_id"],"origin":t["origin"],"horizon_days":h,"target_date":t["target_dates"][i],"outcome":t["outcomes"][i],"q10":qs[0],"q50":qs[1],"q90":qs[2],"loss":cell_loss(t["outcomes"][i],qs),"method":method,"fallback":False})
    return cells
async def evaluate(tasks,sampler,renderer,protocol,seed,arm,label,output):
    import tinker
    from tinker_cookbook.renderers import get_text_content
    sem=asyncio.Semaphore(protocol["sampling"]["concurrency"])
    async def one(t):
        prompt=renderer.build_generation_prompt(messages(t,arm))
        sample_seed=(protocol["sampling"]["seed_base"]+seed+int(t["task_id"][:7],16))%(2**31-1)
        params=tinker.SamplingParams(max_tokens=protocol["sampling"]["max_tokens"],temperature=protocol["sampling"]["temperature"],stop=renderer.get_stop_sequences(),seed=sample_seed)
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
        return {"task_id":t["task_id"],"series_id":t["series_id"],"origin":t["origin"],"prompt_sha256":digest(messages(t,arm)),"history_sha256":digest(t["context"]),"sampling_seed":sample_seed,"requested_samples":protocol["sampling"]["samples"],"returned_samples":len(result.sequences),"valid_samples":len(good),"invalid_samples":len(bad),"distinct_vectors":len({tuple(v) for v in good}),"sample_collapse":len(good)>0 and len({tuple(v) for v in good})==1,"output_tokens":token_count,"sample_returns":good,"sample_sha256":digest(good),"fallback":failed,"cells":cells}
    tasks_out=await asyncio.gather(*(one(t) for t in tasks));cells=[c for t in tasks_out for c in t["cells"]]
    result={"label":label,"scope":"retrospective_development" if label.startswith("dev") else "additional_retrospective_evaluation","summary":summarize(cells),"cells":cells,"tasks":tasks_out,"samples_requested":sum(t["requested_samples"] for t in tasks_out),"output_tokens":sum(t["output_tokens"] for t in tasks_out),"created_at":now()}
    write(output,result);return result
async def run(inputs,output,seed,arm,storage_mode="paired"):
    import tinker
    import numpy as np
    from tinker_cookbook.renderers import get_renderer,TrainOnWhat
    from tinker_cookbook.supervised.data import conversation_to_datum
    p=cfg();root=Path(inputs);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    dataset=json.loads((root/"dataset.json").read_text());audit=json.loads((root/"audit.json").read_text())
    if dataset["protocol_sha256"]!=digest(p) or audit["protocol_sha256"]!=digest(p):raise ValueError("Prepared protocol mismatch")
    if digest(dataset)!=audit["dataset_sha256"]:raise ValueError("Prepared dataset hash mismatch")
    if not audit["price_only_ready"]:raise ValueError("Direct-forecast readiness gate failed")
    if arm=="price_evidence" and not audit["evidence_ready"]:raise ValueError("Origin-safe evidence gate failed")
    if seed not in p["model"]["seeds"]:raise ValueError("Unregistered training seed")
    train=dataset["groups"]["training"];dev=dataset["groups"]["development"];test=dataset["groups"]["retrospective"]
    for t in train:
        if max(t["target_dates"])>p["data"]["train_labels_through"]:raise ValueError("Immature training label")
    started=time.monotonic();rng=random.Random(seed);tag=p["study_id"]+"-"+arm+"-"+str(seed)+"-"+digest(p)[:12]
    meta={"study_id":p["study_id"],"protocol_sha256":digest(p),"seed":str(seed),"arm":arm,"github_sha":os.environ["GITHUB_SHA"],"github_run_id":os.environ["GITHUB_RUN_ID"]}
    client=tinker.ServiceClient(display_name=tag,user_metadata=meta)
    # Paths are saved privately by Tinker. Authenticated RestClient metadata lookup
    # can discover these states without publishing their private resource paths.
    rest=tinker.RestClient();prior=[]
    for offset in range(0,500,100):
        page=await rest.list_training_runs(limit=100,offset=offset)
        prior.extend(r for r in page.training_runs if (r.user_metadata or {}).get("study_id")==p["study_id"] and (r.user_metadata or {}).get("protocol_sha256")==digest(p) and (r.user_metadata or {}).get("seed")==str(seed) and (r.user_metadata or {}).get("arm")==arm)
        if len(page.training_runs)<100:break
    if prior:
        empty_failed_seed43=storage_mode=="state_only" and seed==43
        if empty_failed_seed43:
            for r in prior:
                if (await rest.list_checkpoints(r.training_run_id)).checkpoints:empty_failed_seed43=False
        if not empty_failed_seed43:raise ValueError("Existing matching Tinker run found; inspect and resume it rather than duplicating optimization")
    trainer=await client.create_lora_training_client(base_model=p["model"]["base"],rank=p["model"]["rank"],seed=seed,user_metadata=meta)
    tokenizer=trainer.get_tokenizer();renderer=get_renderer(p["model"]["renderer"],tokenizer)
    datums=[]
    for t in train:
        datum=conversation_to_datum(conversation(t,arm),renderer,max_length=p["model"]["max_context_tokens"],train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE)
        if datum is None:raise ValueError("Training example exceeds registered token budget")
        datums.append(datum)
    state={"study_id":p["study_id"],"status":"training","arm":arm,"seed":seed,"protocol_sha256":digest(p),"dataset_sha256":digest(dataset),"source_sha":os.environ["GITHUB_SHA"],"github_run_id":os.environ["GITHUB_RUN_ID"],"model":p["model"]["base"],"renderer":p["model"]["renderer"],"method":"LoRA supervised likelihood of realized future log-price vectors","training_tasks":len(train),"training_origins":audit["distinct_training_origins"],"optimizer_updates":0,"checkpoints":[],"updates":[],"started_at":now(),"provider_cost_usd":None,"prospective_accuracy":"pending","evidence_effect":"not_established","packages":{n:importlib.metadata.version(n) for n in ("tinker","tinker-cookbook","torch","transformers","numpy")},"resource_storage":"Private Tinker checkpoints with study/configuration/seed metadata; no resource paths in public output","protected_outcomes_loaded":False}
    state["checkpoint_storage_mode"]=storage_mode
    write(out/"progress.json",state);print("DIRECT_TRAINING_STARTED "+json.dumps({k:state[k] for k in ("study_id","seed","arm","training_tasks","model")}),flush=True)
    base=await client.create_sampling_client(base_model=p["model"]["base"])
    dev_base=await evaluate(dev,base,renderer,p,seed,arm,"dev_base",out/"development-0.json")
    state["checkpoints"].append({"update":0,"checkpoint_id":"base-"+digest(p["model"]["base"])[:20],"development":dev_base["summary"],"is_base":True})
    # Checkpoint zero is the actual unadapted model, not a favorable warmup.
    if storage_mode=="paired":
        await trainer.save_state(tag+"-0",user_metadata={**meta,"update":"0"},ttl_seconds=30*86400)
        await trainer.save_weights_for_sampler(tag+"-0",user_metadata={**meta,"update":"0"},ttl_seconds=30*86400)
    paths={}
    write(out/"progress.json",state)
    for step in range(1,p["model"]["max_updates"]+1):
        if time.monotonic()-started>p["limits"]["total_hours"]*3600:raise TimeoutError("Registered execution budget exhausted")
        batch=[datums[rng.randrange(len(datums))] for _ in range(p["model"]["batch_size"])]
        tick=time.monotonic();forward=trainer.forward_backward(batch,"cross_entropy");optim=trainer.optim_step(tinker.AdamParams(learning_rate=p["model"]["learning_rate"]))
        result=await forward;await optim
        weights=np.concatenate([d.loss_fn_inputs["weights"].tolist() for d in batch]);logprobs=np.concatenate([r["logprobs"].tolist() for r in result.loss_fn_outputs])
        loss=float(-np.dot(logprobs,weights)/weights.sum())
        state["updates"].append({"update":step,"completion_cross_entropy":loss,"examples":len(batch),"completion_tokens":float(weights.sum()),"runtime_seconds":time.monotonic()-tick})
        state["optimizer_updates"]=step;state["elapsed_seconds"]=time.monotonic()-started
        write(out/"progress.json",state)
        if step==1 or step%10==0:print("DIRECT_OPTIMIZER_UPDATE "+json.dumps({"seed":seed,"update":step,"completion_cross_entropy":loss}),flush=True)
        if step in p["model"]["checkpoints"]:
            name=tag+"-"+str(step)
            if storage_mode=="state_only":
                # Snapshot before the final persistent save; storage may close the
                # TrainingClient at its limit. Existing fixed samplers remain separate.
                sampler=await trainer.save_weights_and_get_sampling_client()
                saved=await trainer.save_state(name,user_metadata={**meta,"update":str(step)},ttl_seconds=30*86400)
                identity=saved.path;paths[step]=sampler
            else:
                saved=await trainer.save_state(name,user_metadata={**meta,"update":str(step)},ttl_seconds=30*86400)
                weights=await trainer.save_weights_for_sampler(name,user_metadata={**meta,"update":str(step)},ttl_seconds=30*86400)
                identity=weights.path;paths[step]=weights.path
                sampler=await client.create_sampling_client(model_path=weights.path)
            scored=await evaluate(dev,sampler,renderer,p,seed,arm,"dev_update_"+str(step),out/("development-"+str(step)+".json"))
            row={"update":step,"checkpoint_id":hashlib.sha256(identity.encode()).hexdigest()[:24],"development":scored["summary"],"is_base":False}
            state["checkpoints"].append(row);write(out/"progress.json",state)
            print("DIRECT_CHECKPOINT "+json.dumps({"seed":seed,"update":step,"primary_pinball":scored["summary"]["primary_pinball"]}),flush=True)
    selected=min(state["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))
    write(out/"selection.json",{"selected":selected,"rule":p["evaluation"]["selection"],"locked_before_retrospective_evaluation":True,"selected_at":now(),"eligible_updates":[r["update"] for r in state["checkpoints"]]})
    sampler=base if selected["update"]==0 else paths[selected["update"]] if storage_mode=="state_only" else await client.create_sampling_client(model_path=paths[selected["update"]])
    measured=await evaluate(test,sampler,renderer,p,seed,arm,"selected_direct",out/"evaluation-selected.json")
    initial=await evaluate(test,base,renderer,p,seed,arm,"base_direct",out/"evaluation-base.json")
    reference_rows=dataset["baselines"]
    repair_path=root/"reference-repair.json"
    if repair_path.exists():
        repair=json.loads(repair_path.read_text())
        if repair["original_rows_sha256"]!=digest(reference_rows) or not repair["existing_rows_unchanged"]:raise ValueError("Invalid reference correction")
        reference_rows=repair["rows"];state["reference_coverage_repair"]=repair
    references={}
    for method in p["evaluation"]["references"]:
        cells=reference_cells(test,reference_rows,method)
        references[method]={"summary":summarize(cells),"cells":cells,"comparison":matched(measured["cells"],cells)}
    state.update(status="completed",completed_at=now(),selected=selected,retrospective=measured["summary"],base=initial["summary"],comparison_to_base=matched(measured["cells"],initial["cells"]),references=references,elapsed_seconds=time.monotonic()-started,sample_tasks=sum(len(json.loads(f.read_text()).get("tasks",[])) for f in out.glob("development-*.json"))+len(test)*2,source_attribution="Pacific Machines (2026), gpu-price-pack v0.1.1-handover, CC BY 4.0 compilation. Approved component metadata and source-specific target identities retained.")
    # The illustrated task is selected by identity, not by its improvement.
    case=sorted(test,key=lambda t:(t["series_id"],t["origin"]))[0]
    state["illustrative_case"]={"selection":"Lexicographically first eligible retrospective task, fixed independently of model performance","task_id":case["task_id"],"metadata":case["metadata"],"origin":case["origin"],"history":case["context"],"target_dates":case["target_dates"],"outcomes":case["outcomes"]}
    write(out/"result.json",state);write(out/"progress.json",state)
    print("DIRECT_STUDY_COMPLETED "+json.dumps({"seed":seed,"updates":state["optimizer_updates"],"selected_update":selected["update"],"evaluation":measured["summary"]}),flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--inputs",required=True);parser.add_argument("--output",required=True);parser.add_argument("--seed",type=int,required=True);parser.add_argument("--arm",default="price_only",choices=["price_only","price_evidence"]);parser.add_argument("--storage-mode",choices=["paired","state_only"],default="paired");args=parser.parse_args()
    asyncio.run(run(args.inputs,args.output,args.seed,args.arm,args.storage_mode))
if __name__=="__main__":main()
