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
    service=tinker.ServiceClient(display_name="Frozen market-state v19 prospective",user_metadata={"study_id":p["study_id"],"phase":"inference_only"})
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
            async with sem:probs=await sample_decision(samplers[method],renderer.render(decision({**t,"arm":arm},h,lock["log_levels"])))
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
    if path.exists():assert json.loads(path.read_bytes())==reg,"Frozen registration differs"
    else:atomic(path,reg,True)
    if lock is not None:
        model_path=root/"model-lock.json"
        if model_path.exists():assert json.loads(model_path.read_bytes())=={"model":lock,"numerical":numeric},"Frozen model lock differs"
        else:atomic(model_path,{"model":lock,"numerical":numeric},True)
    attempts=[json.loads(f.read_bytes()) for f in sorted(pathlib.Path("/data/market-state-v19/capture/attempts").glob("*.json"))]
    day=at.date();origin=(day-timedelta(days=(day.weekday()+1)%7)).isoformat()
    cohort=json.loads((root/"cohort.json").read_bytes()) if (root/"cohort.json").exists() else None
    prepared=prepare(attempts,origin,at.isoformat(),p,cohort)
    result={"study_id":p["study_id"],"checked_at":at.isoformat(),"protocol_sha256":digest(p),"model_lock_sha256":digest(lock),"origin":origin,"status":"pending","reasons":prepared["reasons"],"latest_observation":prepared["latest_observation"],"first_eligible_origin":p["first_eligible_origin"],"final_analysis_not_before":p["final_analysis_not_before"],"prospective_accuracy":"not established","new_optimizer_updates":0,"model_calls":0,"issued_origins":len(list((root/"commitments").glob("*.json"))),"provider_cost_usd":None}
    outputs={}
    if lock is None:result["reasons"].append("trained_model_lock_pending")
    elif prepared["eligible"]:
        existing=root/"commitments"/(origin+".json")
        if existing.exists():commitment=json.loads(existing.read_bytes());validate(commitment,p,lock)
        else:
            from .market_controls_v19 import vector
            from .signals_remote_v6 import native_references
            tasks=prepared["tasks"];rows,calls=await infer(tasks,p,lock);result["model_calls"]=calls
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
            refs=native_references(snapshots,origin);refmap={(r["series_id"],r["horizon_days"],r["forecaster"]):r for r in refs}
            for t in tasks:
                for h in p["horizons"]:
                    for method in ("last_value","last_value_empirical","drift","seasonal_naive"):
                        r=refmap.get((t["series_id"],h,method));rows.append(row(t,h,method,[r[k] for k in ("q10","q50","q90")] if r else [t["anchor"]]*3,failure=None if r else "NativeRowMissing"))
            commitment={"study_id":p["study_id"],"protocol_sha256":digest(p),"model_lock_sha256":digest(lock),"origin":origin,"issued_at":datetime.now(timezone.utc).isoformat(),"information_cutoff":origin+"T23:59:59.999999+00:00","cohort":prepared["cohort"],"price_inputs":tasks,"rows":rows,"input_vintages":prepared["input_vintages"],"capture_receipts":[r for r in attempts if r.get("eligible_for_origin") and r.get("retrieved_at","")<=origin+"T23:59:59.999999+00:00"],"model_calls":calls,"new_optimizer_updates":0,"publication_requires_workflow_receipt":True}
            validate(commitment,p,lock);atomic(existing,commitment,True)
            if cohort is None:atomic(root/"cohort.json",prepared["cohort"],True)
            data_volume.commit()
        outputs["commitment-"+origin+".json"]=commitment;result.update(status="issued_pending_outcomes",reasons=[],issued_origins=len(list((root/"commitments").glob("*.json"))))
    if lock is not None and at>=utc(p["final_analysis_not_before"]):
        for file in sorted((root/"commitments").glob("*.json")):outputs["score-"+file.name]=score(json.loads(file.read_bytes()),attempts,at.isoformat(),p,lock,publication_receipts.get(file.stem))
    outputs["index.json"]=result;atomic(root/"latest.json",result);data_volume.commit();return outputs
@app.local_entrypoint()
def verified_receipts(p):
    """Server metadata and downloaded archive bytes, not author-entered commit times."""
    import io,subprocess,zipfile
    receipts={}
    if datetime.now(timezone.utc)<utc(p["final_analysis_not_before"]):return receipts
    for directory in pathlib.Path("results/market-state-v19/future").iterdir():
        if not directory.is_dir() or not (directory/"github-publication-receipt.json").exists():continue
        saved=json.loads((directory/"github-publication-receipt.json").read_bytes());identity=str(saved["id"])
        server=json.loads(subprocess.check_output(["gh","api","repos/"+os.environ["GITHUB_REPOSITORY"]+"/actions/artifacts/"+identity],text=True))
        assert server["id"]==saved["id"] and server["created_at"]==saved["created_at"] and server["digest"]==saved["digest"]
        archive=subprocess.check_output(["gh","api","repos/"+os.environ["GITHUB_REPOSITORY"]+"/actions/artifacts/"+identity+"/zip"])
        assert hashlib.sha256(archive).hexdigest()==server["digest"].removeprefix("sha256:")
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            for name in z.namelist():
                if not pathlib.PurePosixPath(name).name.startswith("commitment-"):continue
                value=json.loads(z.read(name));receipts[value["origin"]]={"artifact_id":server["id"],"created_at":server["created_at"],"archive_digest":server["digest"],"commitment_sha256":digest(value)}
    return receipts
def main():
    p=json.loads(pathlib.Path("configs/market-state-v19-prospective.json").read_bytes());pointer=pathlib.Path("results/market-state-v19/latest.json")
    lock=None;numeric=None
    if pointer.exists():
        entry=json.loads(pointer.read_bytes());raw=pathlib.Path(entry["report_path"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==entry["report_sha256"]
        report=json.loads(raw);lock=report.get("model_lock");numeric=report.get("numerical_lock")
    values=execute.remote(p,lock,numeric,verified_receipts(p));out=pathlib.Path("artifacts/market-state-v19-future");out.mkdir(parents=True,exist_ok=True)
    for name,value in values.items():(out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
    print(json.dumps(values["index.json"]),flush=True)
