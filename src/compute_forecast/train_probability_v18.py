"""Matched Tinker CE/CRPS future-price probabilities; no decoded-number gradients."""
from __future__ import annotations
import argparse,asyncio,hashlib,importlib.metadata,json,math,os,pathlib,random,statistics,subprocess,time
from datetime import datetime,timezone
from .probability_v18 import digest,decision,datum,custom_loss,support,quantiles,crps,summarize
from .direct_forecast_v12 import cell_loss
def now():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(pathlib.Path(p).read_text())
def write(p,v):
    p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_suffix(p.suffix+".pending")
    temp.write_text(json.dumps(v,indent=2,allow_nan=False)+"\n");temp.replace(p)
async def evaluate(tasks,sampler,renderer,data,p,label):
    from tinker_cookbook.recipes.decisions import sample_decision
    sem=asyncio.Semaphore(4)
    async def one(t,h):
        z=support(t["anchor"],data["log_levels"]);error=None
        try:
            d=renderer.render(decision(t,h,data["log_levels"]))
            if len(d.tokens)>p["model"]["max_context_tokens"]:raise ValueError("Context limit")
            async with sem:probs=await sample_decision(sampler,d)
            mass=[float(probs[str(i)]) for i in range(len(z))];q=quantiles(mass,z)
        except Exception as exc:
            error=type(exc).__name__;mass=[float(r==0) for r in data["log_levels"]];q=[t["anchor"]]*3
        y=t["outcomes"][(1,3,7).index(h)]
        return {"task_id":t["task_id"],"series_id":t["series_id"],"source_id":t["metadata"]["source_id"],"gpu_model":t["metadata"]["gpu_model"],"instrument_class":t["metadata"]["instrument_class"],"origin":t["origin"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"outcome":y,"anchor":t["anchor"],"q10":q[0],"q50":q[1],"q90":q[2],"loss":cell_loss(y,q),"crps":crps(mass,z,y),"probabilities":mass,"probability_sha256":digest(mass),"support_prices":z,"fallback":error is not None,"failure_type":error,"changed_price":y!=t["anchor"],"out_of_support":y<z[0] or y>z[-1],"prompt_sha256":digest(decision(t,h,data["log_levels"]).text),"method":label}
    cells=await asyncio.gather(*(one(t,h) for t in tasks for h in p["data"]["horizons"]))
    return {"label":label,"created_at":now(),"cells":cells,"summary":summarize(cells)}
def backup(path,value,remote):
    write(path,value)
    result=subprocess.run(["modal","volume","put","compute-forecast-data",str(path),remote,"--force"],capture_output=True,text=True)
    if result.returncode:raise RuntimeError("Private recovery upload failed; refusing to continue without recovery metadata")
async def base_mode(inputs,output):
    import tinker
    from tinker_cookbook.renderers import get_renderer
    from tinker_cookbook.recipes.decisions import DecisionRenderer
    data=read(pathlib.Path(inputs)/"dataset.json");p=read("configs/direct-probability-v18.json");audit=read(pathlib.Path(inputs)/"audit.json");pre=read(pathlib.Path(inputs)/"preflight.json")
    assert digest(data)==audit["dataset_sha256"] and pre["training_ready"]
    service=tinker.ServiceClient(display_name="Compute Forecast probability v18 shared untuned reference",user_metadata={"study_id":p["study_id"],"phase":"shared_base"})
    sampler=await service.create_sampling_client(base_model=p["model"]["base"]);renderer=DecisionRenderer(get_renderer(p["model"]["renderer"],sampler.get_tokenizer()))
    result={phase:await evaluate(data["groups"][phase],sampler,renderer,data,p,"untuned_probability") for phase in ("development","retrospective")}
    result["dataset_sha256"]=digest(data);result["model"]=p["model"];result["new_optimizer_updates"]=0
    write(pathlib.Path(output)/"base.json",result)
async def api_preflight(inputs,output):
    import tinker,torch
    from tinker_cookbook.renderers import get_renderer
    from tinker_cookbook.recipes.decisions import DecisionRenderer,sample_decision
    p=read("configs/direct-probability-v18.json");data=read(pathlib.Path(inputs)/"dataset.json");pre=read(pathlib.Path(inputs)/"preflight.json")
    assert pre["training_ready"]
    rest=tinker.RestClient();items=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);items.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    if len(items)+p["limits"]["max_new_persistent_states"]+2>=100:raise ValueError("Checkpoint preservation gate: insufficient room for all registered new states")
    results=[]
    for objective in p["training"]["objectives"]:
        service=tinker.ServiceClient(display_name="Probability v18 actual-gradient preflight "+objective,user_metadata={"study_id":p["study_id"],"phase":"two_update_api_preflight","objective":objective})
        train=await service.create_lora_training_client(base_model=p["model"]["base"],rank=p["model"]["rank"],seed=0,user_metadata={"study_id":p["study_id"],"phase":"preflight","objective":objective})
        renderer=DecisionRenderer(get_renderer(p["model"]["renderer"],train.get_tokenizer()))
        tasks=sorted(data["groups"]["training"],key=lambda t:(t["series_id"],t["origin"]))[:8]
        sam=await train.save_weights_and_get_sampling_client();rendered=renderer.render(decision(tasks[0],7,data["log_levels"]));before=await sample_decision(sam,rendered)
        datums=[datum(t,7,data["log_levels"],renderer) for t in tasks]
        losses=[]
        for update in range(2):
            f=train.forward_backward_custom(datums,custom_loss(objective,data["crps_scale"]));o=train.optim_step(tinker.AdamParams(learning_rate=.0001))
            result=await f;await o;losses.append({k:float(v) for k,v in result.metrics.items() if isinstance(v,(int,float))})
        after=await sample_decision(await train.save_weights_and_get_sampling_client(),rendered)
        shift=sum(abs(after[k]-before[k]) for k in before)
        if not math.isfinite(shift) or shift<=max(1e-6,20*pre["max_repeat_probability_difference"]):raise ValueError("Actual optimizer updates did not measurably change the forecast probabilities")
        results.append({"objective":objective,"optimizer_updates":2,"probability_l1_shift":shift,"before":before,"after":after,"metrics":losses})
    write(pathlib.Path(output)/"api-preflight.json",{"study_id":p["study_id"],"status":"passed","new_optimizer_updates":4,"results":results,"scope":"Mechanism check on training examples; not a forecasting evaluation","provider_cost_usd":None})
async def train_mode(inputs,output,objective,seed,lr):
    import tinker
    from tinker_cookbook.renderers import get_renderer
    from tinker_cookbook.recipes.decisions import DecisionRenderer
    p=read("configs/direct-probability-v18.json");data=read(pathlib.Path(inputs)/"dataset.json");audit=read(pathlib.Path(inputs)/"audit.json");pre=read(pathlib.Path(inputs)/"preflight.json");base=read(pathlib.Path(inputs)/"base.json")
    assert digest(data)==audit["dataset_sha256"]==base["dataset_sha256"] and pre["training_ready"]
    assert data["protocol_sha256"]==digest(p),"Training configuration differs from audited prepared data"
    assert objective in p["training"]["objectives"] and seed in p["model"]["seeds"] and lr in p["model"]["learning_rates"]
    out=pathlib.Path(output);out.mkdir(parents=True,exist_ok=True)
    tag=objective+"-"+str(seed)+"-"+format(lr,".0e");remote="/probability-v18/"+digest(p)+"/"+tag+"/recovery.json"
    private=pathlib.Path("private/probability-v18")/(tag+".json");private.parent.mkdir(parents=True,exist_ok=True)
    got=subprocess.run(["modal","volume","get","compute-forecast-data",remote,str(private),"--force"],capture_output=True,text=True)
    if got.returncode==0:
        old=read(private);assert old["protocol_sha256"]==digest(p) and old["dataset_sha256"]==digest(data)
        if old.get("completed"):
            for name,value in old["public_files"].items():write(out/name,value)
            print(json.dumps({"status":"recovered_completed_artifacts","objective":objective,"seed":seed,"new_optimizer_updates":0}),flush=True);return
        raise RuntimeError("An incomplete matching run exists. Recover its exact optimizer/update state before any retry; duplicate optimization refused")
    meta={"study_id":p["study_id"],"protocol_sha256":digest(p),"dataset_sha256":digest(data),"objective":objective,"seed":str(seed),"learning_rate":str(lr),"github_sha":os.environ["GITHUB_SHA"],"github_run_id":os.environ["GITHUB_RUN_ID"]}
    rest=tinker.RestClient()
    for offset in range(0,2000,100):
        page=await rest.list_training_runs(limit=100,offset=offset)
        for prior in page.training_runs:
            m=prior.user_metadata or {}
            if all(m.get(k)==meta[k] for k in ("study_id","protocol_sha256","objective","seed","learning_rate")):raise RuntimeError("Existing matching training run found without completed recovery receipt; refusing duplicate optimization")
        if len(page.training_runs)<100:break
    service=tinker.ServiceClient(display_name="Compute Forecast probability "+tag,user_metadata=meta)
    trainer=await service.create_lora_training_client(base_model=p["model"]["base"],rank=p["model"]["rank"],seed=seed,train_mlp=True,train_attn=True,train_unembed=True,user_metadata=meta)
    tok=trainer.get_tokenizer();renderer=DecisionRenderer(get_renderer(p["model"]["renderer"],tok))
    tokenizer_hash=hashlib.sha256(tok.backend_tokenizer.to_str().encode()).hexdigest();assert tokenizer_hash==pre["tokenizer"]["backend_sha256"],"Tokenizer changed after audit"
    records=[(t,h) for t in data["groups"]["training"] for h in p["data"]["horizons"]]
    order=list(range(len(records)));random.Random(seed).shuffle(order);batch_size=p["model"]["batch_size"]
    steps=min(p["model"]["max_updates"],math.ceil(len(order)/batch_size));checkpoints=sorted({round(f*steps) for f in p["model"]["checkpoint_fractions"]})
    max_length=max(len(renderer.render(decision(t,h,data["log_levels"])).tokens) for t,h in records)
    assert max_length<=p["model"]["max_context_tokens"],"A training prompt exceeds the registered context budget"
    start=time.monotonic();state={"study_id":p["study_id"],"status":"training","objective":objective,"seed":seed,"learning_rate":lr,"protocol_sha256":digest(p),"dataset_sha256":digest(data),"source_sha":os.environ["GITHUB_SHA"],"started_at":now(),"model":p["model"],"tokenizer":pre["tokenizer"],"optimizer_updates":0,"example_presentations":0,"planned_updates":steps,"training_horizon_examples":len(records),"training_windows":len(data["groups"]["training"]),"batch_order_sha256":digest([(records[i][0]["task_id"],records[i][1]) for i in order]),"max_prompt_tokens":max_length,"updates":[],"checkpoints":[{"update":0,"checkpoint_id":None,"identity":"Registered public untuned model; no redundant untrained storage copy","development":base["development"]["summary"]}],"provider_cost_usd":None,"prospective_accuracy":"not established","packages":{x:importlib.metadata.version(x) for x in ("tinker","tinker-cookbook","torch","numpy","transformers")}}
    public_files={"development-0.json":base["development"]};paths={};snapshots={0:None}
    write(out/"development-0.json",base["development"]);write(out/"progress.json",state)
    backup(private,{"protocol_sha256":digest(p),"dataset_sha256":digest(data),"completed":False,"optimizer_updates":0,"state":state,"private_paths":{},"public_files":public_files},remote)
    for step in range(1,steps+1):
        if time.monotonic()-start>p["limits"]["max_hours_per_run"]*3600:raise TimeoutError("Registered run timeout")
        batch_indices=order[(step-1)*batch_size:step*batch_size];batch=[datum(*records[i],data["log_levels"],renderer) for i in batch_indices]
        tick=time.monotonic();f=trainer.forward_backward_custom(batch,custom_loss(objective,data["crps_scale"]));o=trainer.optim_step(tinker.AdamParams(learning_rate=lr));result=await f;await o
        state["optimizer_updates"]=step;state["example_presentations"]+=len(batch)
        state["updates"].append({"update":step,"examples":len(batch),"answer_positions":len(batch),"candidate_logprobs":len(batch)*p["distribution"]["n_levels"],"loss_metrics":{k:float(v) for k,v in result.metrics.items() if isinstance(v,(int,float))},"runtime_seconds":time.monotonic()-tick})
        write(out/"progress.json",state)
        if step==1 or step%10==0:print("PROBABILITY_UPDATE "+json.dumps({"objective":objective,"seed":seed,"lr":lr,"update":step,"loss_metrics":state["updates"][-1]["loss_metrics"]}),flush=True)
        if step in checkpoints:
            sampler=await trainer.save_weights_and_get_sampling_client()
            saved=await trainer.save_state("v18-"+tag+"-"+str(step),ttl_seconds=p["limits"]["selected_state_ttl_seconds"],user_metadata={**meta,"update":str(step)})
            paths[str(step)]=saved.path;snapshots[step]=sampler
            measured=await evaluate(data["groups"]["development"],sampler,renderer,data,p,"dev_update_"+str(step))
            public_files["development-"+str(step)+".json"]=measured;write(out/("development-"+str(step)+".json"),measured)
            state["checkpoints"].append({"update":step,"checkpoint_id":hashlib.sha256(saved.path.encode()).hexdigest()[:24],"checkpoint_identity_kind":"Hash of private resource identity, not weight-byte checksum","development":measured["summary"]})
            state["elapsed_seconds"]=time.monotonic()-start;write(out/"progress.json",state)
            backup(private,{"protocol_sha256":digest(p),"dataset_sha256":digest(data),"completed":False,"optimizer_updates":step,"state":state,"private_paths":paths,"public_files":public_files},remote)
            print("PROBABILITY_CHECKPOINT "+json.dumps({"objective":objective,"seed":seed,"lr":lr,"update":step,"development_pinball":measured["summary"]["primary_pinball"]}),flush=True)
    selected=min(state["checkpoints"],key=lambda x:(x["development"]["primary_pinball"],x["update"]))
    selection={"selected":selected,"selected_at":now(),"rule":p["training"]["selection"],"locked_before_retrospective_evaluation":True}
    public_files["selection.json"]=selection;write(out/"selection.json",selection)
    if selected["update"]==0:measured=base["retrospective"]
    else:measured=await evaluate(data["groups"]["retrospective"],snapshots[selected["update"]],renderer,data,p,"selected_"+objective)
    public_files["evaluation-selected.json"]=measured;public_files["evaluation-base.json"]=base["retrospective"]
    state.update(status="completed",completed_at=now(),selected=selected,retrospective=measured["summary"],base=base["retrospective"]["summary"],elapsed_seconds=time.monotonic()-start,dataset_equivalent_passes=state["example_presentations"]/len(records),inference_method="Single registered conditional answer-token probability vector per horizon, no Monte Carlo sample quantiles",source_attribution=audit["source_attribution"])
    public_files["result.json"]=state;public_files["progress.json"]=state
    for name,value in public_files.items():write(out/name,value)
    backup(private,{"protocol_sha256":digest(p),"dataset_sha256":digest(data),"completed":True,"optimizer_updates":steps,"private_paths":paths,"public_files":public_files},remote)
    print("PROBABILITY_COMPLETED "+json.dumps({"objective":objective,"seed":seed,"lr":lr,"optimizer_updates":steps,"selected_update":selected["update"],"primary_pinball":state["retrospective"]["primary_pinball"]}),flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument("--mode",choices=["base","preflight","train"],required=True);p.add_argument("--inputs",required=True);p.add_argument("--output",required=True);p.add_argument("--objective",choices=["ce","crps"]);p.add_argument("--seed",type=int,default=17);p.add_argument("--lr",type=float,default=.00002);a=p.parse_args()
    operation=base_mode(a.inputs,a.output) if a.mode=="base" else api_preflight(a.inputs,a.output) if a.mode=="preflight" else train_mode(a.inputs,a.output,a.objective,a.seed,a.lr)
    asyncio.run(operation)
if __name__=="__main__":main()
