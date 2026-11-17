"""New finite v19 issuance runner. Existing panels and gates are never imported or changed."""
import asyncio,hashlib,json,os,pathlib,pickle,time
from datetime import datetime,timedelta,timezone
import modal
from .probability_v18 import digest,support,quantiles
from .market_state_v19 import decision,utc
from .market_future_v19 import prepare,validate,score
app=modal.App("compute-forecast-market-v19-future")
data_volume=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
secret=modal.Secret.from_name("compute-forecast-evidence-future-v15",required_keys=["TINKER_API_KEY"])
image=(modal.Image.debian_slim(python_version="3.11").pip_install("tinker==0.39.1","tinker-cookbook==0.6.1","tml-renderers==0.4.1","torch==2.15.0+cpu","transformers==5.23.0","tokenizers==0.23.3","numpy==2.2.6","pandas==2.3.1","duckdb==1.2.2","scikit-learn==1.7.1",extra_index_url="https://download.pytorch.org/whl/cpu").add_local_python_source("compute_forecast"))
def atomic(path,value,immutable=False):
    path.parent.mkdir(parents=True,exist_ok=True);raw=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
    if immutable and path.exists():assert path.read_bytes()==raw,"Immutable commitment conflict";return
    temp=path.with_suffix(".pending");temp.write_bytes(raw);temp.replace(path)
def row(t,h,method,q,mass=None,z=None,failure=None):
    return {"task_id":t["task_id"],"series_id":t["series_id"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"contract_sha256":digest(t["contract"]),"method":method,"q10":q[0],"q50":q[1],"q90":q[2],"probabilities":mass,"support_prices":z,"fallback":failure is not None,"failure_type":failure}
async def infer(tasks,p,lock):
    import tinker
    from tinker_cookbook.renderers import get_renderer
    from tinker_cookbook.recipes.decisions import DecisionRenderer,sample_decision
    service=tinker.ServiceClient(display_name="Frozen market-state v19 prospective",user_metadata={"study_id":p["study_id"],"phase":"synthetic_readiness" if p.get("synthetic_probe") else "inference_only"})
    base=await service.create_sampling_client(base_model=lock["base_model"]);renderer=DecisionRenderer(get_renderer(lock["renderer"],base.get_tokenizer()))
    assert hashlib.sha256(base.get_tokenizer().backend_tokenizer.to_str().encode()).hexdigest()==lock["tokenizer_sha256"]
    available=[];rest=tinker.RestClient()
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);available.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    samplers={"untuned_price":base,"untuned_market":base};errors={}
    for record in lock["records"]:
        arm=record["arm"]
        try:
            if record["selected_update"]==0:samplers[arm]=base;continue
            matches=[c for c in available if hashlib.sha256(c.tinker_path.encode()).hexdigest()[:24]==record["checkpoint_id"]]
            assert len(matches)==1 and (matches[0].user_metadata or {}).get("study_id")=="market-state-v19"
            trainer=await service.create_training_client_from_state(matches[0].tinker_path)
            samplers[arm]=await trainer.save_weights_and_get_sampling_client()
        except Exception as error:errors[arm]=type(error).__name__
    sem=asyncio.Semaphore(4);calls=0
    async def one(t,h,method):
        nonlocal calls
        arm="market" if method.endswith("market") or method=="market" else "price";z=support(t["anchor"],lock["log_levels"])
        error=None
        try:
            if method in errors:raise RuntimeError(errors[method])
            if calls>=p["limits"]["max_probability_requests_per_origin"]:raise ValueError("Registered inference limit")
            calls+=1
            async with sem:probs=await asyncio.wait_for(sample_decision(samplers[method],renderer.render(decision({**t,"arm":arm},h,lock["log_levels"]))),timeout=60)
            mass=[float(probs[str(i)]) for i in range(len(z))];q=quantiles(mass,z)
        except Exception as exc:error=type(exc).__name__;mass=[float(v==0) for v in lock["log_levels"]];q=[t["anchor"]]*3
        return row(t,h,method,q,mass,z,error)
    values=await asyncio.gather(*(one(t,h,m) for t in tasks for h in p["horizons"] for m in ("price","market","untuned_price","untuned_market")))
    return values,calls
@app.function(image=image,cpu=2,memory=4096,timeout=1800,max_containers=1,volumes={"/data":data_volume},secrets=[secret])
async def execute(p,lock,numeric,publication_receipts):
    at=datetime.now(timezone.utc);root=pathlib.Path("/data/market-state-v19/future");root.mkdir(parents=True,exist_ok=True)
    if at>=utc(p["limits"]["stop_after_utc"]):raise ValueError("Registered future panel stop reached")
    reg={"protocol":p,"protocol_sha256":digest(p)}
    path=root/"registration.json"
    if path.exists():
        previous=json.loads(path.read_bytes())
        assert previous.get("protocol")==p and previous.get("protocol_sha256")==digest(p),"Frozen scientific protocol differs"
        if previous!=reg:
            assert set(previous)==set(reg)|{"registered_model_lock"} and previous["registered_model_lock"] is None,"Unknown registration format"
            migration={"old_registration_sha256":digest(previous),"protocol_sha256":digest(p),"change":"Remove a null model-lock placeholder from registration format; original file retained; scientific protocol, dates and candidates unchanged"}
            record=root/"registration-format-upgrade.json"
            if record.exists():assert json.loads(record.read_bytes())==migration
            else:
                assert not list((root/"commitments").glob("*.json")),"Format migration must precede first issuance"
                atomic(record,migration,True)
    else:atomic(path,reg,True)
    if lock is not None and list((root/"commitments").glob("*.json")):
        model_path=root/"model-lock.json"
        if model_path.exists():assert json.loads(model_path.read_bytes())=={"model":lock,"numerical":numeric},"Frozen model lock differs"
        else:atomic(model_path,{"model":lock,"numerical":numeric},True)
    attempts=[json.loads(f.read_bytes()) for f in sorted(pathlib.Path("/data/market-state-v19/capture/attempts").glob("*.json"))]
    day=at.date();origin=(day-timedelta(days=(day.weekday()+1)%7)).isoformat()
    cohort=json.loads((root/"cohort.json").read_bytes()) if (root/"cohort.json").exists() else None
    prepared=prepare(attempts,origin,at.isoformat(),p,cohort)
    result={"study_id":p["study_id"],"checked_at":at.isoformat(),"protocol_sha256":digest(p),"model_lock_sha256":digest(lock),"origin":origin,"status":"pending","reasons":prepared["reasons"],"latest_observation":prepared["latest_observation"],"first_eligible_origin":p["first_eligible_origin"],"final_analysis_not_before":p["final_analysis_not_before"],"prospective_accuracy":"not established","new_optimizer_updates":0,"model_calls":0,"produced_origins":len(list((root/"commitments").glob("*.json"))),"issued_origins":sum(r.get("eligible_publication_window",False) for r in publication_receipts.values()),"verified_publication_receipts":publication_receipts,"provider_cost_usd":None}
    outputs={}
    if lock is None:result["reasons"].append("trained_model_lock_pending")
    elif prepared["eligible"]:
        existing=root/"commitments"/(origin+".json")
        expected_engine=digest({name:hashlib.sha256(pathlib.Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ("market_future_remote_v19.py","market_future_v19.py","market_analysis_v19.py","market_controls_v19.py","market_state_v19.py","probability_v18.py")})
        assert lock["future_engine_sha256"]==expected_engine,"Frozen future engine changed"
        if existing.exists():commitment=json.loads(existing.read_bytes());validate(commitment,p,lock)
        else:
            from .market_controls_v19 import vector
            from .signals_remote_v6 import native_references
            tasks=prepared["tasks"]
            try:rows,calls=await asyncio.wait_for(infer(tasks,p,lock),timeout=900)
            except Exception as error:
                calls=None;rows=[]
                for t in tasks:
                    z=support(t["anchor"],lock["log_levels"]);mass=[float(v==0) for v in lock["log_levels"]]
                    for h in p["horizons"]:
                        for method in ("price","market","untuned_price","untuned_market"):rows.append(row(t,h,method,[t["anchor"]]*3,mass,z,"InferenceInitializationOrDeadline"+type(error).__name__))
            result["model_calls"]=calls
            private=pathlib.Path("/data/market-state-v19/numerical")/numeric["input_key"]/"state.pkl";raw=private.read_bytes()
            assert hashlib.sha256(raw).hexdigest()==numeric["state_sha256"],"Numerical model changed"
            models=pickle.loads(raw)["models"]
            for t in tasks:
                for h in p["horizons"]:
                    for arm in ("price","market"):
                        try:q=sorted(t["anchor"]*__import__("math").exp(float(m.predict([vector(t,h,arm)])[0])) for m in models[arm]);failure=None
                        except Exception as e:q=[t["anchor"]]*3;failure=type(e).__name__
                        rows.append(row(t,h,"numerical_"+arm,q,failure=failure))
            snapshots=[]
            for receipt in attempts:
                if not receipt.get("eligible_for_origin") or receipt.get("status")!="captured" or receipt["retrieved_at"]>origin+"T23:59:59.999999+00:00":continue
                snapshots.append({"captured_at":receipt["retrieved_at"],"prices":{"date":receipt["observed_day"],"cohort":[{"id":t["series_id"],"family":t["metadata"]["family"]} for t in tasks],"rows":[{"id":r["series_id"],"date":r["date"],"value":r["value"]} for r in receipt["observations"]]}})
            try:refs=native_references(snapshots,origin)
            except Exception:refs=[]
            refmap={(r["series_id"],r["horizon_days"],r["forecaster"]):r for r in refs}
            for t in tasks:
                for h in p["horizons"]:
                    for method in ("last_value","last_value_empirical","drift","seasonal_naive"):
                        r=refmap.get((t["series_id"],h,method));rows.append(row(t,h,method,[r[k] for k in ("q10","q50","q90")] if r else [t["anchor"]]*3,failure=None if r else "NativeRowMissing"))
            commitment={"study_id":p["study_id"],"protocol_sha256":digest(p),"model_lock_sha256":digest(lock),"origin":origin,"issued_at":datetime.now(timezone.utc).isoformat(),"information_cutoff":origin+"T23:59:59.999999+00:00","cohort":prepared["cohort"],"price_inputs":tasks,"rows":rows,"input_vintages":prepared["input_vintages"],"capture_receipts":[r for r in attempts if r.get("eligible_for_origin") and r.get("retrieved_at","")<=origin+"T23:59:59.999999+00:00"],"model_calls":calls,"new_optimizer_updates":0,"publication_requires_workflow_receipt":True}
            validate(commitment,p,lock);atomic(root/"model-lock.json",{"model":lock,"numerical":numeric},True);atomic(existing,commitment,True)
            if cohort is None:atomic(root/"cohort.json",prepared["cohort"],True)
            data_volume.commit()
        outputs["commitment-"+origin+".json"]=commitment;result.update(status="produced_pending_publication",reasons=[],produced_origins=len(list((root/"commitments").glob("*.json"))))
    if lock is not None and at>=utc(p["final_analysis_not_before"]):
        for file in sorted((root/"commitments").glob("*.json")):outputs["score-"+file.name]=score(json.loads(file.read_bytes()),attempts,at.isoformat(),p,lock,publication_receipts.get(file.stem))
    if at>=utc(p["final_analysis_not_before"]) and lock is not None:
        from .market_analysis_v19 import paired
        cells=[row for name,value in outputs.items() if name.startswith("score-") for row in value["cells"]]
        outputs["paired-analysis.json"]={"study_id":p["study_id"],"contrasts":[paired(cells,a,b) for a,b in (("market","price"),("market","drift"),("market","numerical_market"),("numerical_market","numerical_price"))],"effective_origins":len({r["origin"] for r in cells}),"no_automatic_promotion":True}
    figures=[];resolved={}
    for name,value in outputs.items():
        if name.startswith("score-"):
            for r in value["cells"]:
                key=(r["origin"],r["series_id"],r["horizon_days"])
                if key in resolved:assert resolved[key]==r["outcome"]
                resolved[key]=r["outcome"]
    for file in sorted((root/"commitments").glob("*.json")):
        committed=json.loads(file.read_bytes())
        for task in committed["price_inputs"]:
            predictions=[r for r in committed["rows"] if r["series_id"]==task["series_id"] and r["method"] in ("price","market")]
            figures.append({"id":task["task_id"],"origin":committed["origin"],"issued_at":committed["issued_at"],"series_id":task["series_id"],"metadata":task["metadata"],"history":task["context"],"predictions":predictions,"outcomes":[{"horizon_days":h,"target_date":task["target_dates"][(1,3,7).index(h)],"value":resolved[(committed["origin"],task["series_id"],h)]} for h in p["horizons"] if (committed["origin"],task["series_id"],h) in resolved],"market_state":task["market_state"],"input_sha256":task["market_input_identity"],"commitment_sha256":digest(committed),"publication_receipt":publication_receipts.get(committed["origin"])})
    result["forecast_cases"]=figures
    if at>=utc(p["final_analysis_not_before"]) and lock is not None:
        from .probability_v18 import summarize
        cells=[r for name,value in outputs.items() if name.startswith("score-") for r in value["cells"]]
        result["by_method"]={method:summarize([r for r in cells if r["method"]==method]) for method in p["methods"]}
        origins=sorted({r["origin"] for r in cells});result["paired_by_origin"]=[]
        for origin in origins:
            parts={method:[r for r in cells if r["origin"]==origin and r["horizon_days"]==7 and r["method"]==method] for method in ("price","market")}
            if parts["price"] and {(r["series_id"],r["outcome"]) for r in parts["price"]}=={(r["series_id"],r["outcome"]) for r in parts["market"]}:
                result["paired_by_origin"].append({"origin":origin,"n":len(parts["price"]),"market_minus_price":sum(r["loss"] for r in parts["market"])/len(parts["market"])-sum(r["loss"] for r in parts["price"])/len(parts["price"])})
    migration_path=root/"registration-format-upgrade.json"
    if migration_path.exists():outputs["registration-format-upgrade.json"]=json.loads(migration_path.read_bytes())
    outputs["index.json"]=result;atomic(root/"latest.json",result);data_volume.commit();return outputs
@app.function(image=image,cpu=2,memory=4096,timeout=900,max_containers=1,volumes={"/data":data_volume},secrets=[secret])
async def model_probe(p,lock):
    target=pathlib.Path("/data/market-state-v19/future/probes")/(digest(lock)+".json")
    if target.exists():
        value=json.loads(target.read_bytes());return {**value,"reused_probe":True,"new_model_calls":0}
    origin="2026-01-01";history=[{"date":(datetime.fromisoformat(origin)-timedelta(days=i)).date().isoformat(),"value":1.0,"available_at":(datetime.fromisoformat(origin)-timedelta(days=i)).date().isoformat()+"T17:40:00+00:00"} for i in reversed(range(42))]
    task={"task_id":"synthetic-v19-readiness","series_id":"synthetic-v19-readiness","origin":origin,"anchor":1.0,"context":history,"context_missing_days":0,"metadata":{"source_id":"synthetic_fixture","provider":"synthetic","family":"A100","gpu_model":"synthetic A100 fixture","instrument_class":"synthetic_test_only","pricing_tier":"synthetic","benchmark_contract":"Synthetic API alignment fixture; not a market observation"},"contract":{"kind":"synthetic_not_market"},"market_state":{},"target_dates":["2026-01-02","2026-01-04","2026-01-08"]}
    rows,calls=await infer([task],{**p,"synthetic_probe":True},lock)
    assert len(rows)==12 and calls==12 and not any(r["fallback"] for r in rows),"Frozen model inference readiness failed"
    assert all(len(r["probabilities"])==len(lock["log_levels"])==19 for r in rows)
    result={"study_id":"market-state-v19","status":"passed","model_lock_sha256":digest(lock),"fixture":"Explicitly synthetic API-only probe, not a GPU forecast","probability_vectors":len(rows),"probability_sha256":[digest(r["probabilities"]) for r in rows],"new_model_calls":calls,"new_optimizer_updates":0,"market_forecasts_issued":0,"provider_cost_usd":None}
    atomic(target,result,True);data_volume.commit();return result
def verified_receipts(p):
    receipts={}
    import importlib.util
    spec=importlib.util.spec_from_file_location("attest_market_v19",pathlib.Path("scripts/attest_market_v19.py"));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for directory in sorted(pathlib.Path("results/market-state-v19/future").iterdir()):
        if not directory.is_dir() or not (directory/"attestation.bundle.json").exists():continue
        for origin,receipt in module.verify(directory).items():
            if origin not in receipts or receipt["created_at"]<receipts[origin]["created_at"]:receipts[origin]=receipt
    return receipts
@app.local_entrypoint()
def main():
    p=json.loads(pathlib.Path("configs/market-state-v19-prospective.json").read_bytes());pointer=pathlib.Path("results/market-state-v19/latest.json")
    lock=None;numeric=None
    if pointer.exists():
        entry=json.loads(pointer.read_bytes());raw=pathlib.Path(entry["report_path"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==entry["report_sha256"]
        report=json.loads(raw);lock=report.get("model_lock");numeric=report.get("numerical_lock")
    probe=model_probe.remote(p,lock) if lock is not None else None
    values=execute.remote(p,lock,numeric,verified_receipts(p))
    if probe is not None:values["model-readiness.json"]=probe
    out=pathlib.Path("artifacts/market-state-v19-future");out.mkdir(parents=True,exist_ok=True)
    known={}
    for file in pathlib.Path("results/market-state-v19/future").glob("*/commitment-*.json"):known[digest(json.loads(file.read_bytes()))]=str(file)
    run=os.environ["GITHUB_RUN_ID"]+("-attempt-"+os.environ["GITHUB_RUN_ATTEMPT"] if int(os.environ.get("GITHUB_RUN_ATTEMPT","1"))>1 else "")
    for name,value in values.items():
        if name.startswith("commitment-"):known[digest(value)]="results/market-state-v19/future/"+run+"/"+name
    for case in values["index.json"].get("forecast_cases",[]):case["artifact_path"]=known.get(case["commitment_sha256"])
    for name,value in values.items():(out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
    print(json.dumps(values["index.json"]),flush=True)
