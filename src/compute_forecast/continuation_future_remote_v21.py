"""New prospective quantile challenger; shared source capture, separate immutable commitments."""
import asyncio,hashlib,json,os,pathlib,time
from datetime import datetime,timedelta,timezone
import modal
from .probability_v18 import digest,support,quantiles
from .market_state_v19 import decision as parent_decision,utc
from .market_future_v19 import prepare,snapshots as first_source_vintages
from .continuation_future_v21 import effective_protocol,validate,score
from .market_future_remote_v19 import image,data_volume,secret,atomic
app=modal.App("compute-forecast-ce-continuation-v21-future")
async def infer(tasks,p,lock):
    import tinker
    from tinker_cookbook.renderers import get_renderer
    from tinker_cookbook.recipes.decisions import DecisionRenderer,sample_decision
    service=tinker.ServiceClient(display_name="Frozen categorical continuation v21",user_metadata={"study_id":p["study_id"],"phase":"inference_only"})
    rest=tinker.RestClient();items=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);items.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    samplers={};errors={}
    for identifier in {r["checkpoint_id"] for r in lock["records"]}:
        try:
            matches=[c for c in items if hashlib.sha256(c.tinker_path.encode()).hexdigest()[:24]==identifier]
            assert len(matches)==1,"Frozen checkpoint unavailable"
            trainer=await service.create_training_client_from_state(matches[0].tinker_path)
            assert hashlib.sha256(trainer.get_tokenizer().backend_tokenizer.to_str().encode()).hexdigest()==lock["tokenizer_sha256"]
            samplers[identifier]=await trainer.save_weights_and_get_sampling_client()
        except Exception as exc:errors[identifier]=type(exc).__name__
    base=await service.create_sampling_client(base_model=lock["base_model"]);tok=base.get_tokenizer()
    assert hashlib.sha256(tok.backend_tokenizer.to_str().encode()).hexdigest()==lock["tokenizer_sha256"]
    renderer=DecisionRenderer(get_renderer(lock["renderer"],tok));sem=asyncio.Semaphore(4);calls=0;cache={}
    async def get(identifier,t,h):
        nonlocal calls
        key=(identifier,t["task_id"],h)
        if key in cache:return cache[key]
        if identifier in errors:raise RuntimeError(errors[identifier])
        assert calls<p["limits"]["max_probability_requests_per_origin"];calls+=1
        d=parent_decision({**t,"arm":"price"},h,lock["log_levels"])
        async with sem:
            rendered=renderer.render(d);assert len(rendered.tokens)<=6144
            values=await asyncio.wait_for(sample_decision(samplers[identifier],rendered),timeout=120)
        m=[float(values[str(i)]) for i in range(len(lock["log_levels"]))]
        cache[key]=(m,digest(d.text));return cache[key]
    async def one(t,h):
        z=support(t["anchor"],lock["log_levels"]);rows=[]
        for record in lock["records"]:
            method=record["arm"]
            if method not in p["methods"]:continue
            r={"task_id":t["task_id"],"series_id":t["series_id"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"contract_sha256":digest(t["contract"]),"method":method,"checkpoint_id":record["checkpoint_id"]}
            try:
                m,prompt=await get(record["checkpoint_id"],t,h);q=quantiles(m,z)
                r.update(probabilities=m,support_prices=z,prompt_sha256=prompt,fallback=False,failure_type=None)
            except Exception as exc:
                from .market_state_v19 import prompt
                m=[float(v==0) for v in lock["log_levels"]];q=[t["anchor"]]*3
                r.update(probabilities=m,support_prices=z,prompt_sha256=digest(prompt({**t,"arm":"price"},h)),fallback=True,failure_type=type(exc).__name__)
            r.update(q10=q[0],q50=q[1],q90=q[2],probability_sha256=digest(r["probabilities"]));rows.append(r)
        return rows
    groups=await asyncio.gather(*(one(t,h) for t in tasks for h in p["horizons"]))
    return [r for rows in groups for r in rows],calls
@app.function(image=image,cpu=2,memory=4096,timeout=2400,max_containers=1,volumes={"/data":data_volume},secrets=[secret])
async def execute(p,lock,receipts):
    at=datetime.now(timezone.utc);root=pathlib.Path("/data/ce-continuation-v21/future");root.mkdir(parents=True,exist_ok=True)
    if at>=utc(p["limits"]["stop_after_utc"]):raise ValueError("Fixed panel stop")
    atomic(root/"registration.json",{"protocol":p,"protocol_sha256":digest(p)},True)
    attempts=[json.loads(f.read_bytes()) for f in sorted(pathlib.Path("/data/market-state-v19/capture/attempts").glob("*.json"))]
    origin=(at.date()-timedelta(days=(at.weekday()+1)%7)).isoformat();cohort=None
    for path in (root/"cohort.json",pathlib.Path("/data/market-state-v19/future/cohort.json")):
        if path.exists():cohort=json.loads(path.read_bytes());break
    prep=prepare(attempts,origin,at.isoformat(),p,cohort)
    outputs={};index={"study_id":p["study_id"],"checked_at":at.isoformat(),"protocol_sha256":digest(p),"status":"pending","reasons":list(prep["reasons"]),"latest_observation":prep["latest_observation"],"first_eligible_origin":p["first_eligible_origin"],"final_analysis_not_before":p["final_analysis_not_before"],"model_lock_sha256":digest(lock) if lock else None,"issued_origins":sum(x.get("eligible_publication_window",False) for x in receipts.values()),"verified_publication_receipts":receipts,"new_optimizer_updates":0,"model_calls":0,"provider_cost_usd":None,"prospective_accuracy":"not established"}
    if lock is None:index["reasons"].append("frozen_completed_pilot_pending")
    elif prep["eligible"]:
        assert digest({name:hashlib.sha256(pathlib.Path(__file__).with_name(name).read_bytes()).hexdigest() for name in lock["engine_files"]})==lock["engine_sha256"]
        target=root/"commitments"/(origin+".json")
        if target.exists():commitment=json.loads(target.read_bytes());validate(commitment,p,lock)
        else:
            tasks=prep["tasks"]
            try:rows,calls=await asyncio.wait_for(infer(tasks,p,lock),timeout=1800)
            except Exception as exc:
                calls=None;rows=[]
                for t in tasks:
                    for h in p["horizons"]:
                        for method in p["methods"][:-1]:rows.append({"task_id":t["task_id"],"series_id":t["series_id"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"contract_sha256":digest(t["contract"]),"method":method,"q10":t["anchor"],"q50":t["anchor"],"q90":t["anchor"],"fallback":True,"failure_type":"InferenceDeadlineOrInitialization"+type(exc).__name__,"checkpoint_id":next(v["checkpoint_id"] for v in lock["records"] if v["arm"]==method),"probabilities":[float(v==0) for v in lock["log_levels"]],"probability_sha256":digest([float(v==0) for v in lock["log_levels"]]),"support_prices":support(t["anchor"],lock["log_levels"]),"prompt_sha256":digest(__import__("compute_forecast.market_state_v19",fromlist=["prompt"]).prompt({**t,"arm":"price"},h))})
            from .signals_remote_v6 import native_references
            snapshots=[{"captured_at":r["retrieved_at"],"prices":{"date":r["observed_day"],"cohort":[{"id":t["series_id"],"family":t["metadata"]["family"]} for t in tasks],"rows":[{"id":v["series_id"],"date":v["date"],"value":v["value"]} for v in r["observations"]]}} for day,r in sorted(first_source_vintages(attempts,origin+"T23:59:59.999999+00:00",p).items())]
            try:refs=native_references(snapshots,origin)
            except Exception:refs=[]
            refs={(r["series_id"],r["horizon_days"]):r for r in refs if r["forecaster"]=="drift"}
            for t in tasks:
                for h in p["horizons"]:
                    r=refs.get((t["series_id"],h));q=[r[k] for k in ("q10","q50","q90")] if r else [t["anchor"]]*3
                    rows.append({"task_id":t["task_id"],"series_id":t["series_id"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"contract_sha256":digest(t["contract"]),"method":"official_drift","q10":q[0],"q50":q[1],"q90":q[2],"fallback":r is None,"failure_type":None if r else "NativeDriftUnavailable"})
            commitment={"study_id":p["study_id"],"protocol_sha256":digest(p),"model_lock_sha256":digest(lock),"origin":origin,"issued_at":datetime.now(timezone.utc).isoformat(),"information_cutoff":origin+"T23:59:59.999999+00:00","cohort":prep["cohort"],"price_inputs":tasks,"rows":rows,"input_vintages":prep["input_vintages"],"capture_receipts":[r for r in attempts if r.get("eligible_for_origin") and r.get("retrieved_at","")<=origin+"T23:59:59.999999+00:00"],"model_calls":calls,"new_optimizer_updates":0,"publication_requires_workflow_receipt":True}
            validate(commitment,p,lock);atomic(root/"model-lock.json",lock,True);atomic(target,commitment,True);atomic(root/"cohort.json",prep["cohort"],True);data_volume.commit()
        outputs["commitment-"+origin+".json"]=commitment;index.update(status="produced_pending_publication",reasons=[],model_calls=commitment["model_calls"])
    if lock is not None and at>=utc(p["final_analysis_not_before"]):
        for file in sorted((root/"commitments").glob("*.json")):outputs["score-"+file.name]=score(json.loads(file.read_bytes()),attempts,at.isoformat(),p,lock,receipts.get(file.stem))
        from .continuation_future_v21 import final_analysis
        cells=[r for name,value in outputs.items() if name.startswith("score-") for r in value["cells"]]
        outputs["paired-analysis.json"]=final_analysis(cells,p,lock,[v for name,v in outputs.items() if name.startswith("score-")])
    resolved={}
    for name,value in outputs.items():
        if name.startswith("score-"):
            for r in value["cells"]:resolved[(r["origin"],r["series_id"],r["horizon_days"])]=r["outcome"]
    figures=[]
    for file in sorted((root/"commitments").glob("*.json")):
        value=json.loads(file.read_bytes());receipt=receipts.get(value["origin"])
        if not receipt or not receipt.get("eligible_publication_window") or receipt["commitment_sha256"]!=digest(value):continue
        for task in value["price_inputs"]:
            figures.append({"task_id":task["task_id"],"series_id":task["series_id"],"origin":value["origin"],"issued_at":value["issued_at"],"metadata":task["metadata"],"history":task["context"],"predictions":[{k:r[k] for k in ("method","horizon_days","target_date","q10","q50","q90","fallback","failure_type")} for r in value["rows"] if r["series_id"]==task["series_id"]],"outcomes":[{"horizon_days":h,"target_date":task["target_dates"][(1,3,7).index(h)],"value":resolved[(value["origin"],task["series_id"],h)]} for h in p["horizons"] if (value["origin"],task["series_id"],h) in resolved],"commitment_sha256":digest(value),"publication_receipt":receipt,"outcome_gate":p["final_analysis_not_before"]})
    index["forecast_cases"]=figures
    index["produced_origins"]=len(list((root/"commitments").glob("*.json")));index["model_lock"]=lock
    outputs["index.json"]=index;atomic(root/"latest.json",index);data_volume.commit();return outputs
def verified_receipts():
    import importlib.util
    spec=importlib.util.spec_from_file_location("attest_continuation_v21",pathlib.Path("scripts/attest_continuation_v21.py"));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result={}
    for root in pathlib.Path("results/ce-continuation-v21/future").glob("*"):
        if not root.is_dir() or not (root/"attestation.bundle.json").exists():continue
        for origin,r in module.verify(root).items():
            if origin in result:assert result[origin]["commitment_sha256"]==r["commitment_sha256"]
            if origin not in result or r["created_at"]<result[origin]["created_at"]:result[origin]=r
    return result
@app.local_entrypoint()
def main():
    cfg=json.loads(pathlib.Path("configs/ce-continuation-v21.json").read_bytes());parent=json.loads(pathlib.Path(cfg["parent"]["report_path"]).read_bytes())
    raw=pathlib.Path(cfg["parent"]["report_path"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==cfg["parent"]["report_sha256"]
    protocol=json.loads(pathlib.Path(cfg["future_protocol"]).read_bytes())
    binding=json.loads(pathlib.Path("configs/ce-continuation-v21-inputs.json").read_bytes())
    audit=json.loads(pathlib.Path(binding["audit_path"]).read_bytes())
    p=effective_protocol(protocol,parent["future_protocol"],audit["expanded_ready"]);lock=None
    pointer=pathlib.Path("results/ce-continuation-v21/latest.json")
    if pointer.exists():
        ref=json.loads(pointer.read_bytes());raw=pathlib.Path(ref["report_path"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==ref["report_sha256"]
        report=json.loads(raw)
        if report.get("model_lock"):
            files=["continuation_future_v21.py","continuation_future_remote_v21.py","market_future_v19.py","market_state_v19.py","probability_v18.py","signals_remote_v6.py"]
            lock={**report["model_lock"],"study_protocol_sha256":digest(cfg),"registered_future_protocol_sha256":digest(protocol),"engine_files":files,"engine_sha256":digest({name:hashlib.sha256(pathlib.Path(__file__).with_name(name).read_bytes()).hexdigest() for name in files})}
    values=execute.remote(p,lock,verified_receipts());out=pathlib.Path("artifacts/ce-continuation-v21-future");out.mkdir(parents=True,exist_ok=True)
    known={digest(json.loads(f.read_bytes())):str(f) for f in pathlib.Path("results/ce-continuation-v21/future").glob("*/commitment-*.json")}
    run=os.environ["GITHUB_RUN_ID"]+("-attempt-"+os.environ["GITHUB_RUN_ATTEMPT"] if int(os.environ.get("GITHUB_RUN_ATTEMPT","1"))>1 else "")
    for name,value in values.items():
        if name.startswith("commitment-"):known[digest(value)]="results/ce-continuation-v21/future/"+run+"/"+name
    for case in values["index.json"].get("forecast_cases",[]):case["artifact_path"]=known.get(case["commitment_sha256"])
    for name,value in values.items():(out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
    print(json.dumps(values["index.json"]),flush=True)
