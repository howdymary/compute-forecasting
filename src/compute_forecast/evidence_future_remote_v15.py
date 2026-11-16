"""Frozen prospective inference on Modal; existing collection and studies are read-only."""
from __future__ import annotations
import asyncio,hashlib,json,os,pathlib,time
from datetime import datetime,timedelta,timezone
import modal
from .direct_forecast_v12 import digest,parse,price_quantiles
from .direct_future_v12 import utc,issuance_status
from .evidence_future_v15 import prepare,validate,score
from .evidence_v14 import messages
from .signals_remote_v6 import native_references
app=modal.App("compute-forecast-evidence-future-v15")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
secret=modal.Secret.from_name("compute-forecast-evidence-future-v15",required_keys=["TINKER_API_KEY"])
image=(modal.Image.debian_slim(python_version="3.11")
 .pip_install("tinker==0.39.1","tinker-cookbook==0.6.1","tml-renderers==0.4.1","torch==2.15.0+cpu","transformers==5.23.0","tokenizers==0.23.3","numpy==2.2.6","pandas==2.3.1","duckdb==1.2.2","pyarrow>=16,<24",extra_index_url="https://download.pytorch.org/whl/cpu")
 .env({"GITHUB_SHA":os.environ.get("GITHUB_SHA","unknown")})
 .add_local_dir("configs","/root/configs",copy=True)
 .add_local_dir("inputs/evidence-future-v15","/root/inputs/evidence-future-v15",copy=True)
 .add_local_python_source("compute_forecast"))
def now():return datetime.now(timezone.utc).isoformat()
def load(path):return json.loads(path.read_bytes())
def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(".pending")
    temp.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n");temp.replace(path)
def retain(root,kind,value,key=None):
    path=root/kind/((key or digest(value))+".json");path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)
    if path.exists():
        if path.read_text()!=raw:raise ValueError("Immutable future artifact conflict")
    else:
        with path.open("x") as f:f.write(raw)
    return path
def records(root,kind):return [load(p) for p in sorted((root/kind).glob("*.json"))] if (root/kind).exists() else []
async def paths_and_lock(p,receipt,existing=None):
    import tinker
    rest=tinker.RestClient();available=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);available.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    private={};lock={"study_id":p["study_id"],"operational_seed":17,"locked_at":now(),"parent_retention_receipt_sha256":digest(receipt),"protocol_sha256":digest(p)}
    for row in receipt["records"]:
        matches=[c for c in available if hashlib.sha256(c.tinker_path.encode()).hexdigest()[:24]==row["checkpoint_id"]]
        if len(matches)!=1:raise ValueError("Frozen operational model missing or ambiguous")
        c=matches[0];meta=c.user_metadata or {}
        assert meta.get("study_id")=="direct-evidence-v14" and meta.get("seed")=="17" and meta.get("arm")==row["arm"]
        private[row["arm"]]=c.tinker_path
        lock[row["arm"]]={"checkpoint_sha256":hashlib.sha256(c.tinker_path.encode()).hexdigest(),"checkpoint_id":row["checkpoint_id"],"selected_update":row["selected_update"],"base_model":"Qwen/Qwen3.5-4B"}
    if existing:
        assert all(existing[a]["checkpoint_sha256"]==lock[a]["checkpoint_sha256"] for a in ("price_only","price_evidence"))
        lock=existing
    return private,lock
async def infer(tasks,private,p,parent,lock):
    import tinker
    from tinker_cookbook.renderers import get_renderer,get_text_content
    service=tinker.ServiceClient(display_name="Compute Forecast frozen prospective inference",user_metadata={"study_id":p["study_id"],"optimizer_updates":"0"})
    base=await service.create_sampling_client(base_model=parent["model"]["base"]);renderer=get_renderer(parent["model"]["renderer"],base.get_tokenizer())
    samplers={"base_price_only":base,"base_price_evidence":base}
    for arm in ("price_only","price_evidence"):
        trainer=await service.create_training_client_from_state(private[arm])
        samplers[arm]=await trainer.save_weights_and_get_sampling_client()
    sem=asyncio.Semaphore(4)
    async def one(task,method):
        arm="price_evidence" if method.endswith("price_evidence") else "price_only"
        prompt=renderer.build_generation_prompt(messages(task,arm))
        params=tinker.SamplingParams(max_tokens=p["sampling"]["max_tokens"],temperature=p["sampling"]["temperature"],stop=renderer.get_stop_sequences())
        async with sem:response=await samplers[method].sample(prompt=prompt,num_samples=p["sampling"]["samples"],sampling_params=params)
        good=[];bad=[];tokens=0
        for sequence in response.sequences:
            tokens+=len(sequence.tokens)
            try:
                message,termination=renderer.parse_response(sequence.tokens)
                if hasattr(termination,"is_clean") and not termination.is_clean:raise ValueError("Unclean termination")
                good.append(parse(get_text_content(message),parent["sampling"]["min_log_return"],parent["sampling"]["max_log_return"]))
            except (ValueError,TypeError,KeyError,OverflowError) as e:bad.append(type(e).__name__)
        fallback=len(good)<p["sampling"]["min_valid"];quantiles=price_quantiles(good,task["anchor"]) if not fallback else [[task["anchor"]]*3 for _ in p["horizons"]]
        rows=[]
        for i,h in enumerate(p["horizons"]):
            rows.append({"task_id":task["task_id"],"series_id":task["series_id"],"horizon_days":h,"target_date":task["target_dates"][i],"method":method,"reference":method.startswith("base_"),"contract_sha256":digest(task["metadata"]["contract"]),"checkpoint_sha256":lock[method]["checkpoint_sha256"] if method in private else digest(parent["model"]["base"]),"q10":quantiles[i][0],"q50":quantiles[i][1],"q90":quantiles[i][2],"fallback":fallback})
        return {"method":method,"task_id":task["task_id"],"prompt_sha256":digest(messages(task,arm)),"history_sha256":digest(task["context"]),"sample_returns":good,"sample_sha256":digest(good),"requested_samples":p["sampling"]["samples"],"returned_samples":len(response.sequences),"valid_samples":len(good),"invalid_samples":len(bad),"invalid_error_types":bad,"distinct_vectors":len({tuple(v) for v in good}),"output_tokens":tokens,"sampling_seed":None,"rows":rows}
    samples=await asyncio.gather(*(one(t,method) for t in tasks for method in samplers))
    assert sum(s["requested_samples"] for s in samples)<=p["limits"]["max_sampling_vectors_per_origin"]
    return samples
@app.function(image=image,cpu=2,memory=4096,timeout=1800,max_containers=1,secrets=[secret],volumes={"/data":data,"/public":public},schedule=modal.Cron("3,45 0 * * *"))
def tick():
    begin=time.monotonic();at=now()
    if utc(at)>utc("2027-03-03T00:00:00Z"):return {"study_id":"direct-evidence-v14-prospective","readiness":{"reasons":["finite_panel_complete"]},"issued_origins":None,"new_optimizer_updates":0}
    p=load(pathlib.Path("/root/configs/evidence-v14-prospective.json"));parent=load(pathlib.Path("/root/configs/direct-evidence-v14-final.json"))
    source=pathlib.Path("/data/signals-v6");root=pathlib.Path("/data/evidence-v14-future");root.mkdir(parents=True,exist_ok=True)
    engine=digest({name:hashlib.sha256(pathlib.Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ("evidence_future_v15.py","evidence_future_remote_v15.py","prospective_evidence_v14.py","direct_future_v12.py","direct_forecast_v12.py","evidence_v14.py","signals_remote_v6.py","starter_probe.py")})
    registration={"protocol_sha256":digest(p),"engine_sha256":engine,"source_sha":os.environ.get("GITHUB_SHA"),"first_registered_at":at}
    registration_path=root/"registration.json"
    if registration_path.exists():
        previous=load(registration_path);assert previous["protocol_sha256"]==digest(p),"Registered protocol changed"
        if previous["engine_sha256"]!=engine:
            assert not records(root,"commitments") and at<p["first_eligible_origin"]+"T23:59:59+00:00","Frozen future engine changed after issuance window opened"
            retain(root,"superseded_preissuance_registrations",previous);atomic(registration_path,registration)
        else:registration=previous
    else:atomic(registration_path,registration)
    originals=records(source,"snapshots");bls=load(pathlib.Path("/root/inputs/evidence-future-v15/bls-vintages.json"))["records"]
    receipt=load(pathlib.Path("/root/inputs/evidence-future-v15/model-lock.json"))
    lock_path=root/"model-lock.json";existing=load(lock_path) if lock_path.exists() else None
    private,lock=asyncio.run(paths_and_lock(p,receipt,existing))
    if not existing:atomic(lock_path,lock)
    state=prepare(originals,bls,at,p);origin=state["origin"];commitment_path=root/"commitments"/(origin+".json")
    commitments=records(root,"commitments")
    if state["eligible"] and not commitment_path.exists():
        try:
            frozen_path=root/"cohort.json";frozen=load(frozen_path) if frozen_path.exists() else None
            tasks=[t for t in state["tasks"] if frozen is None or t["series_id"] in frozen]
            if not tasks:raise ValueError("Frozen cohort has no eligible source contracts")
            native=native_references(state["snapshots"],origin);lookup={(r["forecaster"],r["series_id"],r["horizon_days"]):r for r in native}
            samples=asyncio.run(infer(tasks,private,p,parent,lock));rows=[r for s in samples for r in s["rows"]]
            for task in tasks:
                for method in ("last_value","last_value_empirical","drift","seasonal_naive"):
                    for i,h in enumerate(p["horizons"]):
                        item=lookup[(method,task["series_id"],h)]
                        rows.append({"task_id":task["task_id"],"series_id":task["series_id"],"horizon_days":h,"target_date":task["target_dates"][i],"method":method,"reference":True,"contract_sha256":digest(task["metadata"]["contract"]),"q10":item["q10"],"q50":item["q50"],"q90":item["q90"],"fallback":False})
            issued=now()
            value={"study_id":p["study_id"],"status":"issued","protocol_sha256":digest(p),"model_lock_sha256":digest(lock),"origin":origin,"information_cutoff":origin+"T23:59:59+00:00","issued_at":issued,"input_snapshot_hashes":[digest(s) for s in state["snapshots"] if s["prices"]["date"]<=origin],"bls_feature_sha256":digest(tasks[0]["bls"]),"rows":rows,"sample_records":samples,"runtime_seconds":time.monotonic()-begin,"new_optimizer_updates":0,"provider_cost_usd":None}
            validate(value,p,lock);retain(root,"commitments",value,origin);commitments.append(value)
            destination=pathlib.Path("/public/evidence-v14-future")
            retain(destination,"artifacts",value);public.commit()
            publication_at=now()
            receipt_value={"origin":origin,"commitment_sha256":digest(value),"public_volume_committed_at":publication_at,"within_registered_deadline":issuance_status(origin,publication_at,p)=="eligible","trust_boundary":"Provider runtime clock and public Modal volume, not an independent trusted timestamp"}
            retain(root,"publication_receipts",receipt_value,origin);data.commit()
            if frozen is None:atomic(frozen_path,[t["series_id"] for t in tasks])
        except Exception as e:
            retain(root,"failures",{"at":now(),"origin":origin,"phase":"issuance","error_type":type(e).__name__,"status":"not_issued"})
    # Score only actual matured compatible target observations, in the same source window.
    evaluations=[]
    publication_receipts=records(root,"publication_receipts")
    for value in commitments:
        receipt_value=next((r for r in publication_receipts if r["commitment_sha256"]==digest(value)),None)
        if receipt_value is None or not receipt_value["within_registered_deadline"]:
            continue
        result=score(value,originals,now(),p,lock);result["commitment_sha256"]=digest(value)
        retain(root,"evaluations",result);evaluations.append(result)
    readiness={k:v for k,v in state.items() if k not in ("tasks","snapshots")}
    readiness["eligible_tasks"]=len(state["tasks"]);readiness["task_ids"]=[t["series_id"] for t in state["tasks"]]
    index={"study_id":p["study_id"],"updated_at":now(),"registration":registration,"model_lock":lock,"readiness":readiness,"issued_origins":len(commitments),"primary_analysis_required_eligible_origins":12,"prospective_accuracy":"not_established","publication_boundary":"Public Modal artifacts are timestamped and hash-addressed. This is not an independently trusted timestamp or an automatic GitHub anchor.","source_attribution":"GPU Rental Prices, exact provider contract quotes, CC BY 4.0: https://gpurentalprices.com/data. US BLS original PPI releases. Pacific pack supplied the prior frozen training, not prospective truth.","new_optimizer_updates":0,"provider_cost_usd":None,"ledger":[{"origin":c["origin"],"issued_at":c["issued_at"],"commitment_sha256":digest(c),"rows":len(c["rows"]),"target_dates":sorted({r["target_date"] for r in c["rows"]}),"publication_receipt":next((r for r in publication_receipts if r["commitment_sha256"]==digest(c)),None),"evaluation":next((e["status"] for e in evaluations if e["commitment_sha256"]==digest(c)),"not_publicly_committed_within_deadline")} for c in commitments]}
    if utc(now())>utc("2027-03-03T00:00:00Z"):index["schedule_status"]="completed_finite_panel"
    destination=pathlib.Path("/public/evidence-v14-future");destination.mkdir(parents=True,exist_ok=True)
    for kind,values in (("commitments",commitments),("evaluations",evaluations)):
        for value in values:retain(destination,"artifacts",value)
    atomic(destination/"index.json",index);retain(root,"readiness",readiness);data.commit();public.commit()
    return index
def main():
    with app.run():index=tick.remote()
    out=pathlib.Path("artifacts/evidence-v14-audit");out.mkdir(parents=True,exist_ok=True);atomic(out/"prospective-readiness.json",index)
    print(json.dumps({"study_id":index["study_id"],"readiness":index["readiness"],"issued_origins":index["issued_origins"],"new_optimizer_updates":0}),flush=True)
if __name__=="__main__":main()
