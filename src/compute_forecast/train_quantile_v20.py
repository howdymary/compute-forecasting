"""Bounded direct pinball warm start through Tinker; no numerical predictions delegated."""
from __future__ import annotations
import argparse,asyncio,hashlib,importlib.metadata,json,math,os,pathlib,random,statistics,subprocess,time
from datetime import datetime,timezone
from .quantile_v20 import decision,datum,head_quantiles,custom_loss,expansion_gate,TAUS
from .probability_v18 import digest,support,summarize
from .direct_forecast_v12 import cell_loss
from .train_market_v19 import load_inputs,write
def now():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
async def evaluate(tasks,sampler,renderer,data,p,label):
    from tinker_cookbook.recipes.decisions import sample_decision
    sem=asyncio.Semaphore(p["limits"]["max_inference_concurrency"])
    async def one(t,h):
        z=support(t["anchor"],data["log_levels"]);heads=[];error=None;prompts=[]
        try:
            for tau in TAUS:
                d=decision(t,h,tau,data["log_levels"]);rendered=renderer.render(d)
                if len(rendered.tokens)>p["model"]["max_context_tokens"]:raise ValueError("Context limit")
                prompts.append(digest(d.text))
                async with sem:probs=await asyncio.wait_for(sample_decision(sampler,rendered),timeout=120)
                heads.append([float(probs[str(i)]) for i in range(len(z))])
            q,raw,cross=head_quantiles(heads,z)
        except Exception as exc:error=type(exc).__name__;q=[t["anchor"]]*3;raw=None;cross=None
        y=t["outcomes"][(1,3,7).index(h)]
        return {"task_id":t["task_id"],"series_id":t["series_id"],"source_id":t["metadata"]["source_id"],"gpu_model":t["metadata"]["gpu_model"],"instrument_class":t["metadata"]["instrument_class"],"origin":t["origin"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"anchor":t["anchor"],"outcome":y,"q10":q[0],"q50":q[1],"q90":q[2],"loss":cell_loss(y,q),"crps":None,"head_probabilities":heads,"head_encoding":"Scalar mean coefficients, not predictive probability mass","raw_head_means":raw,"raw_crossing":cross,"support_prices":z,"prompt_sha256":prompts,"fallback":error is not None,"failure_type":error,"out_of_support":y<z[0] or y>z[-1],"changed_price":y!=t["anchor"],"method":label}
    cells=await asyncio.gather(*(one(t,h) for t in tasks for h in p["data"]["horizons"]))
    return {"label":label,"created_at":now(),"cells":cells,"summary":summarize(cells),"raw_crossing_count":sum(r["raw_crossing"] is True for r in cells)}
def backup(path,value,remote):
    write(path,value)
    r=subprocess.run(["modal","volume","put","compute-forecast-data",str(path),remote,"--force"],capture_output=True,text=True)
    if r.returncode:raise RuntimeError("Private recovery upload failed; stopped without repeating optimization")
async def run(seed):
    import tinker
    from tinker_cookbook.renderers import get_renderer
    from tinker_cookbook.recipes.decisions import DecisionRenderer
    p=read("configs/quantile-training-v20.json");pre=read("artifacts/quantile-training-v20/preflight/readiness.json")
    data,old,audit=load_inputs("inputs/market-state-v19")
    assert pre["training_ready"] and digest(p)==pre["protocol_sha256"] and digest(data)==p["parent"]["dataset_sha256"]
    assert seed in (17,29,43)
    if seed!=17:
        pilot=read("artifacts/quantile-training-v20/models/17/result.json")
        assert pilot["expansion_gate"]["passed"],"No new optimization: registered development expansion gate failed"
    tag=str(seed);out=pathlib.Path("artifacts/quantile-training-v20/models")/tag
    remote="/quantile-training-v20/"+digest(p)+"/"+tag+"/recovery.json"
    private=pathlib.Path("private/quantile-training-v20")/(tag+".json");private.parent.mkdir(parents=True,exist_ok=True)
    got=subprocess.run(["modal","volume","get","compute-forecast-data",remote,str(private),"--force"],capture_output=True,text=True)
    if got.returncode==0:
        saved=read(private);assert saved["protocol_sha256"]==digest(p) and saved["dataset_sha256"]==digest(data)
        if saved.get("completed"):
            for name,value in saved["public_files"].items():write(out/name,value)
            print(json.dumps({"status":"recovered_completed","seed":seed,"new_optimizer_updates":0}),flush=True);return
        raise RuntimeError("Incomplete matching run exists; exact checkpoint/optimizer recovery required. Duplicate optimization refused")
    rest=tinker.RestClient();items=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);items.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    assert len(items)+3<=100,"Checkpoint capacity changed; no deletion or billing change"
    identifier=p["parent"]["checkpoint_ids"][tag]
    parents=[c for c in items if hashlib.sha256(c.tinker_path.encode()).hexdigest()[:24]==identifier and (c.user_metadata or {}).get("study_id")=="market-state-v19"]
    assert len(parents)==1,"Frozen parent identity not available"
    meta={"study_id":p["study_id"],"protocol_sha256":digest(p),"seed":tag,"objective":"direct_ordered_quantile_pinball","parent_id":identifier,"github_run_id":os.environ["GITHUB_RUN_ID"],"github_sha":os.environ.get("PUBLICATION_SOURCE_SHA",os.environ["GITHUB_SHA"])}
    for offset in range(0,2000,100):
        page=await rest.list_training_runs(limit=100,offset=offset)
        if any(all((r.user_metadata or {}).get(k)==meta[k] for k in ("study_id","protocol_sha256","seed")) for r in page.training_runs):raise RuntimeError("Matching Tinker run already exists; duplicate optimization refused")
        if len(page.training_runs)<100:break
    service=tinker.ServiceClient(display_name="Compute Forecast direct quantile pilot "+tag,user_metadata=meta)
    trainer=await service.create_training_client_from_state(parents[0].tinker_path,user_metadata=meta)
    tok=trainer.get_tokenizer();assert hashlib.sha256(tok.backend_tokenizer.to_str().encode()).hexdigest()==p["parent"]["tokenizer_sha256"]
    renderer=DecisionRenderer(get_renderer(p["model"]["renderer"],tok))
    records=[(t,h) for t in data["groups"]["training"] for h in p["data"]["horizons"]]
    order=list(range(len(records)));random.Random(seed).shuffle(order)
    steps=p["model"]["max_updates"];batch_size=p["model"]["batch_horizon_groups"]
    assert steps*batch_size<=len(order),"Pilot repeats or exceeds registered one-pass horizon budget"
    state={"study_id":p["study_id"],"seed":seed,"status":"running","protocol_sha256":digest(p),"dataset_sha256":digest(data),"parent_id":identifier,"parent_selected_update":30,"model":p["model"],"optimizer_updates":0,"horizon_group_presentations":0,"head_presentations":0,"training_windows":len(data["groups"]["training"]),"training_horizon_examples":len(records),"batch_order_sha256":digest([(records[i][0]["task_id"],records[i][1]) for i in order[:steps*batch_size]]),"started_at":now(),"source_sha":os.environ.get("PUBLICATION_SOURCE_SHA",os.environ["GITHUB_SHA"]),"tokenizer_sha256":p["parent"]["tokenizer_sha256"],"loss_scale":pre["loss_scale"],"updates":[],"checkpoints":[],"provider_cost_usd":None,"prospective_accuracy":"not established","packages":{k:importlib.metadata.version(k) for k in ("tinker","tinker-cookbook","torch","transformers")}}
    files={};paths={};snapshots={};start=time.monotonic()
    recovery=lambda done:{"protocol_sha256":digest(p),"dataset_sha256":digest(data),"completed":done,"state":state,"private_paths":paths,"public_files":files}
    # Persist existence before any update; interruption never silently reruns optimization.
    backup(private,recovery(False),remote)
    sampler=await trainer.save_weights_and_get_sampling_client()
    baseline=await evaluate(data["groups"]["development"],sampler,renderer,data,p,"head_zero")
    state["checkpoints"].append({"update":0,"checkpoint_id":identifier,"identity":"Frozen v19 parent weights with new quantile-head interface; no redundant stored copy","development":baseline["summary"],"raw_crossing_count":baseline["raw_crossing_count"]})
    files["development-0.json"]=baseline;write(out/"development-0.json",baseline);write(out/"progress.json",state);snapshots[0]=sampler
    backup(private,recovery(False),remote)
    max_length=0
    for step in range(1,steps+1):
        if time.monotonic()-start>p["limits"]["max_hours_per_run"]*3600:raise TimeoutError("Registered runtime limit")
        indices=order[(step-1)*batch_size:step*batch_size]
        batch=[datum(*records[i],tau,data["log_levels"],renderer) for i in indices for tau in TAUS]
        for i in indices:
            for tau in TAUS:max_length=max(max_length,len(renderer.render(decision(*records[i],tau,data["log_levels"])).tokens))
        assert max_length<=p["model"]["max_context_tokens"],"Registered prompt limit"
        tick=time.monotonic()
        f=trainer.forward_backward_custom(batch,custom_loss(pre["loss_scale"]));o=trainer.optim_step(tinker.AdamParams(learning_rate=p["model"]["learning_rate"]))
        result=await f;await o
        metrics={k:float(v) for k,v in result.metrics.items() if isinstance(v,(int,float))}
        assert all(math.isfinite(v) for v in metrics.values()),"Nonfinite real Tinker gradient/loss operation"
        state["optimizer_updates"]=step;state["horizon_group_presentations"]+=len(indices);state["head_presentations"]+=len(batch)
        state["updates"].append({"update":step,"horizon_groups":len(indices),"head_datums":len(batch),"metrics":metrics,"runtime_seconds":time.monotonic()-tick})
        write(out/"progress.json",state)
        if step==1 or step%8==0:print("QUANTILE_UPDATE "+json.dumps({"seed":seed,"update":step,"metrics":metrics}),flush=True)
        if step in p["model"]["checkpoints"]:
            sampler=await trainer.save_weights_and_get_sampling_client()
            saved=await trainer.save_state("v20-quantile-"+tag+"-"+str(step),ttl_seconds=180*86400,user_metadata={**meta,"update":str(step)})
            paths[str(step)]=saved.path;snapshots[step]=sampler
            measured=await evaluate(data["groups"]["development"],sampler,renderer,data,p,"head_update_"+str(step))
            files["development-"+str(step)+".json"]=measured;write(out/("development-"+str(step)+".json"),measured)
            state["checkpoints"].append({"update":step,"checkpoint_id":hashlib.sha256(saved.path.encode()).hexdigest()[:24],"identity_kind":"Hash of private resource identifier, not weight-byte checksum","development":measured["summary"],"raw_crossing_count":measured["raw_crossing_count"]})
            state["elapsed_seconds"]=time.monotonic()-start;write(out/"progress.json",state);backup(private,recovery(False),remote)
            print("QUANTILE_CHECKPOINT "+json.dumps({"seed":seed,"update":step,"pinball":measured["summary"]["primary_pinball"]}),flush=True)
    state["selected"]=min(state["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))
    parent=next(r for r in read(p["parent"]["report_path"])["runs"] if r["arm"]=="price" and r["seed"]==seed)
    state["expansion_gate"]=expansion_gate(state,parent["selected"]["development"]["primary_pinball"])
    files["selection.json"]={"selected":state["selected"],"selected_at":now(),"before_new_retrospective_evaluation":True,"rule":p["selection"]["rule"]}
    write(out/"selection.json",files["selection.json"]);backup(private,recovery(False),remote)
    chosen=state["selected"]["update"]
    measured=await evaluate(data["groups"]["retrospective"],snapshots[chosen],renderer,data,p,"selected_head")
    zero=measured if chosen==0 else await evaluate(data["groups"]["retrospective"],snapshots[0],renderer,data,p,"head_zero")
    files["evaluation-selected.json"]=measured;files["evaluation-zero.json"]=zero
    state.update(status="completed",completed_at=now(),elapsed_seconds=time.monotonic()-start,max_prompt_tokens=max_length,retrospective=measured["summary"],head_zero=zero["summary"],frozen_parent=parent["retrospective"]["summary"],inference_calls_per_cell=3,interpretation="Additional exploratory opened-period comparison; no future accuracy claim")
    files["result.json"]=state;files["progress.json"]=state
    for name,value in files.items():write(out/name,value)
    backup(private,recovery(True),remote)
    print("QUANTILE_COMPLETED "+json.dumps({"seed":seed,"updates":state["optimizer_updates"],"selected_update":chosen,"retrospective_pinball":measured["summary"]["primary_pinball"],"expansion_gate":state["expansion_gate"]}),flush=True)
def main():
    a=argparse.ArgumentParser();a.add_argument("--seed",type=int,default=17);args=a.parse_args();asyncio.run(run(args.seed))
if __name__=="__main__":main()
