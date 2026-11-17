"""Matched categorical CE continuation from the same saved weights and Adam state."""
from __future__ import annotations
import argparse,asyncio,hashlib,importlib.metadata,json,math,os,pathlib,subprocess,time
from datetime import datetime,timezone
from .continuation_v21 import batches,batch_identity,selection
from .continuation_eval_v21 import evaluate
from .probability_v18 import digest,custom_loss
from .market_state_v19 import decision,datum
from .train_market_v19 import write
def read(path):return json.loads(pathlib.Path(path).read_bytes())
def now():return datetime.now(timezone.utc).isoformat()
def backup(path,value,remote,limit):
    raw=json.dumps(value,allow_nan=False).encode();assert len(raw)<=limit,"Private recovery byte budget"
    write(path,value)
    r=subprocess.run(["modal","volume","put","compute-forecast-data",str(path),remote,"--force"],capture_output=True,text=True)
    if r.returncode:raise RuntimeError("Private recovery upload failed; optimization stopped")
async def run(arm,seed):
    import tinker
    from tinker_cookbook.renderers import get_renderer
    from tinker_cookbook.recipes.decisions import DecisionRenderer
    p=read("configs/ce-continuation-v21.json");data=read("inputs/ce-continuation-v21/dataset.json");audit=read("inputs/ce-continuation-v21/audit.json")
    pre=read("artifacts/ce-continuation-v21-preflight/readiness.json");inc=read("artifacts/ce-continuation-v21-preflight/incumbent.json")
    assert digest(p)==pre["protocol_sha256"]==data["protocol_sha256"] and digest(data)==pre["dataset_sha256"]==audit["dataset_sha256"]
    assert pre["training_ready"] and arm in pre["arms"] and seed in (17,29,43)
    assert arm!="expanded" or data["expanded_ready"]
    if seed!=17:
        gate=read("artifacts/ce-continuation-v21-expansion/gate.json")
        assert gate["passed"] and gate["protocol_sha256"]==digest(p),"Registered development/capacity gate did not pass"
    records=data["training"][arm];plan=batches(records,seed,p["model"]["max_updates"],p["model"]["batch_size"],p["parent"]["examples_seen_at_parent"])
    order_hash=batch_identity(plan);out=pathlib.Path("artifacts/ce-continuation-v21-models")/arm/str(seed);out.mkdir(parents=True,exist_ok=True)
    private=pathlib.Path("private/ce-continuation-v21")/(arm+"-"+str(seed)+".json");private.parent.mkdir(parents=True,exist_ok=True)
    remote="/ce-continuation-v21/"+digest(p)+"/"+arm+"-"+str(seed)+"/recovery.json"
    got=subprocess.run(["modal","volume","get","compute-forecast-data",remote,str(private),"--force"],capture_output=True,text=True)
    old=read(private) if got.returncode==0 else None
    if old is not None:
        assert old["protocol_sha256"]==digest(p) and old["dataset_sha256"]==digest(data) and old["state"]["batch_order_sha256"]==order_hash
        if old.get("completed"):
            for name,value in old["public_files"].items():write(out/name,value)
            print(json.dumps({"status":"recovered_completed_outputs","arm":arm,"seed":seed,"new_optimizer_updates":0}),flush=True);return
        if old.get("inflight_update") is not None:raise RuntimeError("Unacknowledged optimizer operation exists; duplicate optimization refused")
        if old["state"]["optimizer_updates"]!=old["last_saved_update"]:raise RuntimeError("Acknowledged unsaved optimizer tail exists; no automatic replay of completed updates")
    rest=tinker.RestClient();items=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);items.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    parent=[c for c in items if hashlib.sha256(c.tinker_path.encode()).hexdigest()[:24]==p["parent"]["checkpoint_id"] and (c.user_metadata or {}).get("study_id")=="market-state-v19"]
    assert len(parent)==1,"Frozen parent checkpoint unavailable"
    start_step=old["state"]["optimizer_updates"] if old else 0
    remaining_states=sum(v>start_step for v in p["model"]["checkpoints"])
    assert len(items)+remaining_states<=p["limits"]["checkpoint_preservation_limit"],"Insufficient preservation capacity; no deletion"
    meta={"study_id":p["study_id"],"protocol_sha256":digest(p),"dataset_sha256":digest(data),"arm":arm,"seed":str(seed),"parent_id":p["parent"]["checkpoint_id"],"phase":"continuation","github_run_id":os.environ["GITHUB_RUN_ID"],"source_sha":os.environ.get("PUBLICATION_SOURCE_SHA",os.environ["GITHUB_SHA"]),"resume_from_update":str(start_step)}
    if old is None:
        for offset in range(0,2000,100):
            page=await rest.list_training_runs(limit=100,offset=offset)
            if any(all((r.user_metadata or {}).get(k)==meta[k] for k in ("study_id","protocol_sha256","arm","seed","phase")) for r in page.training_runs):raise RuntimeError("Matching training run exists without recovery receipt; duplicate optimization refused")
            if len(page.training_runs)<100:break
    paths=old["private_paths"] if old else {};files=old["public_files"] if old else {"development-0.json":inc["development"]}
    state=old["state"] if old else {"study_id":p["study_id"],"arm":arm,"seed":seed,"status":"running","protocol_sha256":digest(p),"dataset_sha256":digest(data),"training_corpus_sha256":audit["training_corpus_sha256"][arm],"parent_id":p["parent"]["checkpoint_id"],"parent_selected_update":30,"optimizer_restore":"weights_and_optimizer","optimizer_updates":0,"example_presentations":0,"input_token_presentations":0,"supervised_answer_positions":0,"batch_order_sha256":order_hash,"training_windows":len(records),"training_horizon_examples":3*len(records),"started_at":now(),"source_sha":meta["source_sha"],"model":p["model"],"tokenizer_sha256":p["parent"]["tokenizer_sha256"],"updates":[],"checkpoints":[{"update":0,"checkpoint_id":p["parent"]["checkpoint_id"],"identity":"Frozen operational parent weights and Adam state; no redundant checkpoint storage","development":inc["development"]["summary"]}],"provider_cost_usd":None,"prospective_accuracy":"not established","packages":{k:importlib.metadata.version(k) for k in ("tinker","tinker-cookbook","torch","transformers")}}
    state.setdefault("attempts",[]).append({"github_run_id":os.environ["GITHUB_RUN_ID"],"attempt":os.environ.get("GITHUB_RUN_ATTEMPT","1"),"resumed_update":start_step,"source_sha":meta["source_sha"],"started_at":now()})
    last_saved=start_step;inflight=None
    def recovery(done=False):
        return {"protocol_sha256":digest(p),"dataset_sha256":digest(data),"completed":done,"state":state,"private_paths":paths,"public_files":files,"last_saved_update":last_saved,"inflight_update":inflight}
    backup(private,recovery(),remote,p["limits"]["max_private_recovery_bytes"])
    service=tinker.ServiceClient(display_name="Compute Forecast CE continuation "+arm+"/"+str(seed),user_metadata=meta)
    restore=paths[str(start_step)] if start_step else parent[0].tinker_path
    try:trainer=await service.create_training_client_from_state_with_optimizer(restore,user_metadata=meta)
    except Exception as exc:raise RuntimeError("Documented optimizer restore failed: "+type(exc).__name__) from None
    tok=trainer.get_tokenizer();assert hashlib.sha256(tok.backend_tokenizer.to_str().encode()).hexdigest()==p["parent"]["tokenizer_sha256"]
    renderer=DecisionRenderer(get_renderer(p["model"]["renderer"],tok));started=time.monotonic();prior_elapsed=state.get("elapsed_seconds",0)
    for step in range(start_step+1,p["model"]["max_updates"]+1):
        if time.monotonic()-started>p["limits"]["max_hours_per_run"]*3600:raise TimeoutError("Registered per-run execution limit")
        rows=plan[step-1];datums=[];tokens=0
        for t,h in rows:
            task={**t,"arm":"price"};rendered=renderer.render(decision(task,h,data["log_levels"]))
            assert len(rendered.tokens)<=p["model"]["max_context_tokens"]
            tokens+=len(rendered.tokens);datums.append(datum(task,h,data["log_levels"],renderer))
        inflight=step;backup(private,recovery(),remote,p["limits"]["max_private_recovery_bytes"])
        tick=time.monotonic()
        f=trainer.forward_backward_custom(datums,custom_loss("ce",1.));o=trainer.optim_step(tinker.AdamParams(learning_rate=p["model"]["learning_rate"]));value=await f;await o
        metrics={k:float(v) for k,v in value.metrics.items() if isinstance(v,(int,float))}
        assert all(math.isfinite(v) for v in metrics.values()),"Nonfinite training metric"
        inflight=None;state["optimizer_updates"]=step;state["example_presentations"]+=len(datums);state["supervised_answer_positions"]+=len(datums);state["input_token_presentations"]+=tokens
        state["updates"].append({"update":step,"examples":len(datums),"logical_input_tokens":tokens,"candidate_answer_logprobs":len(datums)*19,"loss_metrics":metrics,"runtime_seconds":time.monotonic()-tick})
        write(out/"progress.json",state);backup(private,recovery(),remote,p["limits"]["max_private_recovery_bytes"])
        if step==1 or step%10==0:print("CE_CONTINUATION_UPDATE "+json.dumps({"arm":arm,"seed":seed,"update":step,"metrics":metrics}),flush=True)
        if step in p["model"]["checkpoints"]:
            sampler=await trainer.save_weights_and_get_sampling_client(kind="snapshot")
            saved=await trainer.save_state("v21-"+arm+"-"+str(seed)+"-"+str(step),ttl_seconds=p["limits"]["checkpoint_ttl_days"]*86400,user_metadata={**meta,"update":str(step)})
            paths[str(step)]=saved.path;last_saved=step
            backup(private,recovery(),remote,p["limits"]["max_private_recovery_bytes"])
            measured=await evaluate(data["groups"]["development"],sampler,renderer,data["log_levels"],p,arm+"_update_"+str(step))
            files["development-"+str(step)+".json"]=measured;write(out/("development-"+str(step)+".json"),measured)
            state["checkpoints"].append({"update":step,"checkpoint_id":hashlib.sha256(saved.path.encode()).hexdigest()[:24],"identity_kind":"Private resource-ID hash, not weight-byte checksum","development":measured["summary"]})
            state["elapsed_seconds"]=prior_elapsed+time.monotonic()-started;write(out/"progress.json",state);backup(private,recovery(),remote,p["limits"]["max_private_recovery_bytes"])
            print("CE_CONTINUATION_CHECKPOINT "+json.dumps({"arm":arm,"seed":seed,"update":step,"development_pinball":measured["summary"]["primary_pinball"]}),flush=True)
    # Recover a saved checkpoint whose development measurement was interrupted, without an optimizer replay.
    measured_updates={c["update"] for c in state["checkpoints"]}
    for update,path in sorted(paths.items(),key=lambda x:int(x[0])):
        if int(update) in measured_updates:continue
        client=await service.create_training_client_from_state(path);sampler=await client.save_weights_and_get_sampling_client(kind="snapshot")
        measured=await evaluate(data["groups"]["development"],sampler,renderer,data["log_levels"],p,arm+"_update_"+update)
        files["development-"+update+".json"]=measured
        state["checkpoints"].append({"update":int(update),"checkpoint_id":hashlib.sha256(path.encode()).hexdigest()[:24],"identity_kind":"Private resource-ID hash, not weight-byte checksum","development":measured["summary"]})
    state["checkpoints"].sort(key=lambda c:c["update"]);state["selected"]=selection(state["checkpoints"])
    files["selection.json"]={"selected":state["selected"],"selected_at":now(),"rule":p["training"]["selection"],"locked_before_exploratory_evaluation":True}
    write(out/"selection.json",files["selection.json"]);backup(private,recovery(),remote,p["limits"]["max_private_recovery_bytes"])
    if "evaluation-selected.json" in files:measured=files["evaluation-selected.json"]
    elif state["selected"]["update"]==0:measured=inc["retrospective"]
    else:
        selected=await service.create_training_client_from_state(paths[str(state["selected"]["update"])])
        sampler=await selected.save_weights_and_get_sampling_client(kind="snapshot")
        measured=await evaluate(data["groups"]["retrospective"],sampler,renderer,data["log_levels"],p,arm+"_selected")
    files["evaluation-selected.json"]=measured
    used=[(t["task_id"],h) for group in plan for t,h in group]
    state.update(status="completed",completed_at=now(),retrospective=measured["summary"],incumbent=inc["retrospective"]["summary"],elapsed_seconds=prior_elapsed+time.monotonic()-started,unique_horizon_examples_presented=len(set(used)),repeated_horizon_presentations=len(used)-len(set(used)),effective_corpus_passes=len(used)/(3*len(records)),new_optimizer_updates_this_attempt=p["model"]["max_updates"]-start_step,inference_method="Exact categorical conditional answer-token probabilities, frozen v19 support and quantile convention",interpretation="Opened historical periods only; no prospective accuracy claim")
    files["result.json"]=state;files["progress.json"]=state
    for name,value in files.items():write(out/name,value)
    backup(private,recovery(True),remote,p["limits"]["max_private_recovery_bytes"])
    print("CE_CONTINUATION_COMPLETED "+json.dumps({"arm":arm,"seed":seed,"optimizer_updates":state["optimizer_updates"],"selected_update":state["selected"]["update"],"development_pinball":state["selected"]["development"]["primary_pinball"],"retrospective_pinball":measured["summary"]["primary_pinball"]}),flush=True)
def main():
    a=argparse.ArgumentParser();a.add_argument("--arm",choices=["same","expanded"],required=True);a.add_argument("--seed",type=int,default=17);args=a.parse_args();asyncio.run(run(args.arm,args.seed))
if __name__=="__main__":main()
