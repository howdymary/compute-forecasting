"""New bounded weekly probability panel; old collection and panels are never modified."""
import asyncio,hashlib,json,os,pathlib,time
from datetime import datetime,timezone
import modal
from .probability_v18 import digest,decision,support,quantiles
from .probability_future_v18 import prepare,validate,score
from .signals_remote_v6 import native_references
from .direct_future_v12 import issuance_status
app=modal.App("compute-forecast-probability-v18-future")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
secret=modal.Secret.from_name("compute-forecast-evidence-future-v15",required_keys=["TINKER_API_KEY"])
image=(modal.Image.debian_slim(python_version="3.11").pip_install("tinker==0.39.1","tinker-cookbook==0.6.1","tml-renderers==0.4.1","torch==2.15.0+cpu","transformers==5.23.0","tokenizers==0.23.3","numpy==2.2.6","pandas==2.3.1","duckdb==1.2.2","pyarrow>=16,<24",extra_index_url="https://download.pytorch.org/whl/cpu").add_local_dir("configs","/root/configs",copy=True).add_local_dir("inputs/probability-v18-future","/root/inputs/probability-v18-future",copy=True).add_local_python_source("compute_forecast"))
def read(p):return json.loads(p.read_bytes())
def atomic(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_suffix(".pending");temp.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n");temp.replace(p)
def retain(root,kind,value,key=None):
    p=root/kind/((key or digest(value))+".json");p.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)
    if p.exists():assert p.read_text()==raw,"Immutable future record conflict"
    else:
        with p.open("x") as f:f.write(raw)
def records(root,kind):return [read(p) for p in sorted((root/kind).glob("*.json"))] if (root/kind).exists() else []
async def infer(tasks,p,parent,lock):
    import tinker
    from tinker_cookbook.renderers import get_renderer
    from tinker_cookbook.recipes.decisions import DecisionRenderer,sample_decision
    service=tinker.ServiceClient(display_name="Compute Forecast frozen probability transfer",user_metadata={"study_id":p["study_id"],"phase":"prospective_inference"})
    base=await service.create_sampling_client(base_model=parent["model"]["base"]);renderer=DecisionRenderer(get_renderer(parent["model"]["renderer"],base.get_tokenizer()))
    assert hashlib.sha256(base.get_tokenizer().backend_tokenizer.to_str().encode()).hexdigest()==lock["tokenizer_sha256"]
    samplers={"untuned":base};rest=tinker.RestClient();available=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);available.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    for obj in ("ce","crps"):
        row=next(r for r in lock["records"] if r["objective"]==obj)
        if row["selected_update"]==0:samplers[obj+"_selected"]=base;continue
        matches=[c for c in available if hashlib.sha256(c.tinker_path.encode()).hexdigest()[:24]==row["checkpoint_id"]]
        if len(matches)!=1:raise ValueError("Frozen selected probability checkpoint missing")
        assert (matches[0].user_metadata or {}).get("study_id")==parent["study_id"]
        trainer=await service.create_training_client_from_state(matches[0].tinker_path)
        samplers[obj+"_selected"]=await trainer.save_weights_and_get_sampling_client()
    sem=asyncio.Semaphore(4)
    async def one(t,h,method):
        z=support(t["anchor"],lock["log_levels"]);error=None
        try:
            rendering=renderer.render(decision(t,h,lock["log_levels"]))
            async with sem:mass=await sample_decision(samplers[method],rendering)
            prob=[mass[str(i)] for i in range(len(z))];q=quantiles(prob,z)
        except Exception as exc:error=type(exc).__name__;prob=[float(r==0) for r in lock["log_levels"]];q=[t["anchor"]]*3
        return {"task_id":t["task_id"],"method":method,"series_id":t["series_id"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"contract_sha256":digest(t["metadata"]["contract"]),"probabilities":prob,"probability_sha256":digest(prob),"support_prices":z,"q10":q[0],"q50":q[1],"q90":q[2],"fallback":error is not None,"failure_type":error}
    return await asyncio.gather(*(one(t,h,m) for t in tasks for h in p["horizons"] for m in samplers))
@app.function(image=image,cpu=2,memory=4096,timeout=1800,max_containers=1,secrets=[secret],volumes={"/data":data,"/public":public},schedule=modal.Cron("10 0 * * 1"))
def tick():
    at=datetime.now(timezone.utc).isoformat();p=read(pathlib.Path("/root/configs/probability-v18-prospective.json"))
    if at>=p["limits"]["stop_after_utc"]:return {"status":"finite_panel_closed","new_optimizer_updates":0}
    data.reload();public.reload()
    parent=read(pathlib.Path("/root/configs/direct-probability-v18.json"));lock=read(pathlib.Path("/root/inputs/probability-v18-future/model-lock.json"))
    assert lock["protocol_sha256"]==digest(parent)
    root=pathlib.Path("/data/probability-v18-future");root.mkdir(parents=True,exist_ok=True)
    engine=digest({n:hashlib.sha256(pathlib.Path(__file__).with_name(n).read_bytes()).hexdigest() for n in ("probability_v18.py","probability_future_v18.py","probability_future_remote_v18.py","direct_future_v12.py","evidence_future_v15.py")})
    registration={"protocol_sha256":digest(p),"model_lock_sha256":digest(lock),"engine_sha256":engine}
    f=root/"registration.json"
    if f.exists():assert read(f)==registration,"Future registration changed"
    else:atomic(f,registration)
    snapshots=records(pathlib.Path("/data/signals-v6"),"snapshots");state=prepare(snapshots,at,p)
    commitments=records(root,"commitments");origin=state["origin"];cohort_path=root/"cohort.json";frozen=read(cohort_path) if cohort_path.exists() else None
    if state["eligible"] and not (root/"commitments"/(origin+".json")).exists():
        try:
            tasks=state["tasks"]
            if not frozen:tasks=tasks[:p["limits"]["max_targets"]]
            if frozen:
                by_id={t["series_id"]:t for t in tasks};assert all(sid in by_id for sid in frozen),"Frozen origin contract missing";tasks=[by_id[sid] for sid in frozen]
            assert len(tasks)*3*3<=p["limits"]["max_probability_requests_per_origin"]
            predictions=asyncio.run(infer(tasks,p,parent,lock));native=native_references(state["snapshots"],origin);lookup={(r["forecaster"],r["series_id"],r["horizon_days"]):r for r in native}
            for t in tasks:
                for h in p["horizons"]:
                    for method in ("last_value","last_value_empirical","drift","seasonal_naive"):
                        r=lookup.get((method,t["series_id"],h));q=[r[k] for k in ("q10","q50","q90")] if r else [t["anchor"]]*3
                        predictions.append({"task_id":t["task_id"],"method":method,"series_id":t["series_id"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"contract_sha256":digest(t["metadata"]["contract"]),"q10":q[0],"q50":q[1],"q90":q[2],"fallback":r is None})
            issued=datetime.now(timezone.utc).isoformat()
            used=[s for s in state["snapshots"] if s["prices"]["date"]<=origin]
            value={"study_id":p["study_id"],"status":"issued","protocol_sha256":digest(p),"model_lock_sha256":digest(lock),"origin":origin,"information_cutoff":origin+"T23:59:59+00:00","issued_at":issued,"input_vintages":[{"captured_at":s["captured_at"],"snapshot_sha256":digest(s)} for s in used],"rows":predictions,"target_contracts":{t["series_id"]:t["metadata"]["contract"] for t in tasks},"new_optimizer_updates":0,"provider_cost_usd":None}
            validate(value,p,lock);retain(root,"commitments",value,origin)
            retain(pathlib.Path("/public/probability-v18-future"),"artifacts",value);public.commit()
            published=datetime.now(timezone.utc).isoformat()
            retain(root,"publication_receipts",{"commitment_sha256":digest(value),"published_at":published,"deadline_status":issuance_status(origin,published,p),"trust_boundary":"Provider runtime clock and public volume publication; not an independent trusted timestamp"},origin)
            if not frozen:atomic(cohort_path,[t["series_id"] for t in tasks])
            commitments.append(value)
        except Exception as error:retain(root,"failures",{"at":issued if "issued" in locals() else at,"origin":origin,"error_type":type(error).__name__,"status":"not_issued"})
    evaluations=[]
    receipts=records(root,"publication_receipts")
    for c in commitments:
        receipt=next((r for r in receipts if r["commitment_sha256"]==digest(c)),None)
        if not receipt or receipt["deadline_status"]!="eligible":continue
        value=score(c,snapshots,at,p,lock);retain(root,"evaluations",value);evaluations.append(value)
    index={"study_id":p["study_id"],"checked_at":at,"registration":registration,"issued_origins":len(commitments),"readiness":{k:v for k,v in state.items() if k not in ("tasks","snapshots")},"evaluations":evaluations,"new_optimizer_updates":0,"prospective_accuracy":"not established","classification":p["classification"]}
    atomic(pathlib.Path("/public/probability-v18-future/index.json"),index);data.commit();public.commit()
    return index
@app.local_entrypoint()
def main():
    value=tick.remote();out=pathlib.Path("artifacts/probability-v18-future");out.mkdir(parents=True,exist_ok=True);atomic(out/"readiness.json",value);print(json.dumps({k:value.get(k) for k in ("study_id","issued_origins","new_optimizer_updates","classification")}),flush=True)
