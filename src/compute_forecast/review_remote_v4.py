"""Remote v4 operations with separate immutable records and public summaries."""
from __future__ import annotations
import argparse,asyncio,hashlib,json,os,time,uuid
from datetime import datetime,timedelta,timezone,date
from pathlib import Path
import modal
from .review_v4 import encoded,digest,read_archive,one,ARCHIVE_URL
app=modal.App("compute-forecast-review-v4-operations")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
def configuration(image):
    return image.env({"GITHUB_SHA":os.environ.get("GITHUB_SHA","unknown")}).add_local_file("configs/prospective-selector-v4.json","/root/configs/prospective-selector-v4.json",copy=True).add_local_file("configs/review-v4-experiments.json","/root/configs/review-v4-experiments.json",copy=True).add_local_file("configs/market-context-v4.json","/root/configs/market-context-v4.json",copy=True).add_local_python_source("compute_forecast")
light=configuration(modal.Image.debian_slim(python_version="3.11").pip_install("numpy==2.2.6","pandas==2.3.1","pyarrow>=16,<24","scipy>=1.12,<2","scikit-learn>=1.5,<2"))
forecast_image=configuration(modal.Image.debian_slim(python_version="3.11").pip_install("torch==2.15.0",index_url="https://download.pytorch.org/whl/cpu").pip_install("numpy==2.2.6","pandas==2.3.1","pyarrow>=16,<24","scipy>=1.12,<2","scikit-learn>=1.5,<2","tinker==0.39.0","tinker-cookbook==0.6.1","chronos-forecasting==2.3.2","transformers==5.23.0"))
def interval_diagnostic(context):
    from .interval_v4 import empirical_interval
    from .prospective_panel_v4 import reference,pinball
    cases=[];failures=[]
    for s in context["history_context"]["series"]:
        values={date.fromisoformat(p["date"]):p["value"] for p in s["points"]}
        for origin in ("2026-06-20","2026-07-04","2026-07-18"):
            at=date.fromisoformat(origin);history={d:v for d,v in values.items() if d<=at}
            for h in (1,3,7):
                target=at+timedelta(days=h);candidate=empirical_interval(history,at,h);base,why=reference(history,at,h,"last_value_empirical")
                if target not in values or candidate["status"]!="completed" or base is None:failures.append({"series_id":s["id"],"origin":origin,"horizon":h,"reason":candidate["status"] if candidate["status"]!="completed" else why or "missing_label"});continue
                y=values[target];qs=candidate["quantiles"]
                def row(q):return dict(zip(("q10","q50","q90"),q))
                cases.append({"series_id":s["id"],"origin":origin,"horizon_days":h,"candidate_pinball":pinball(y,row(qs)),"reference_pinball":pinball(y,row(base)),"candidate_covered":qs[0]<=y<=qs[2],"reference_covered":base[0]<=y<=base[2],"candidate_width":qs[2]-qs[0],"reference_width":base[2]-base[0],"residual_count":candidate["residual_count"],"effective_residuals":candidate["effective_residuals"],"last_calibration_label":candidate["last_label_date"]})
    n=len(cases)
    return {"schema_version":4,"status":"completed_training_period_diagnostic" if n else "pending_insufficient_residuals","classification":"Additional retrospective diagnostic on independently licensed context; no tuning or independent accuracy claim","origins":["2026-06-20","2026-07-04","2026-07-18"],"n_cells":n,"metrics":{key:sum(c[key] for c in cases)/n for key in ("candidate_pinball","reference_pinball","candidate_covered","reference_covered","candidate_width","reference_width")} if n else None,"cases":cases,"failures":failures,"future_comparison":"Registered prospective interval arm; outcomes pending","source_hash":digest(context["history_context"])}
@app.function(image=light,cpu=2,memory=4096,timeout=900,max_containers=1,volumes={"/data":data})
def initialize(context,archive,source_sha):
    from .vintage_v4 import seed_context
    from .policy_v2 import make_tasks
    from .learning_v4 import split_and_gate
    root=Path("/data/review-v4");root.mkdir(exist_ok=True);receipt=seed_context(context,root/"vintages")
    members,_=read_archive(archive);_,grid=one(members,"/grid.json");tasks,_=make_tasks(grid);_,_,gate=split_and_gate(tasks)
    # Persist derived tasks privately for a later, gated, separately identified run.
    path=root/"training"/"original-pack-tasks.json";path.parent.mkdir(exist_ok=True);raw=encoded(tasks)
    if not path.exists():path.write_bytes(raw)
    result={"schema_version":4,"source_sha":source_sha,"run_id":uuid.uuid4().hex,"created_at":datetime.now(timezone.utc).isoformat(),"vintage":receipt,"learning":gate,"interval":interval_diagnostic(context),"new_training_updates":0,"cost_usd":None}
    dest=root/"operations"/result["run_id"];dest.mkdir(parents=True);(dest/"initialize.json").write_bytes(encoded(result));data.commit();return result
@app.function(image=light,cpu=2,memory=8192,timeout=1800,max_containers=1,volumes={"/data":data})
def capture_source(cutoff):
    from .vintage_v4 import capture
    try:return {"status":"captured","receipt":capture("/data/review-v4/vintages",cutoff)}
    except Exception as error:return {"status":"collection_failed","cutoff":cutoff,"retrieved_at":datetime.now(timezone.utc).isoformat(),"error_type":type(error).__name__,"no_forecast_inputs_replaced":True}
    finally:data.commit()
@app.function(image=forecast_image,cpu=4,memory=8192,timeout=1800,max_containers=2,volumes={"/data":data},secrets=[modal.Secret.from_dict({"TINKER_API_KEY":os.environ["TINKER_API_KEY"]})] if os.environ.get("TINKER_API_KEY") else [])
def issue_origin(origin,scale):
    from .prospective_panel_v4 import issue,retain_commitment
    record=asyncio.run(issue("/data/review-v4/vintages",origin,scale));receipt=retain_commitment("/data/review-v4",record);data.commit();return {"record":record,"receipt":receipt}
@app.function(image=light,cpu=1,memory=2048,timeout=300,volumes={"/data":data})
def score_origin(origin,commitment_sha):
    from .prospective_panel_v4 import score_locked
    from .vintage_v4 import select_snapshot
    path=Path("/data/review-v4/commitments")/(origin+".json");record=json.loads(path.read_bytes())
    # Maturity is checked by the scorer before it uses supplied truth.
    target=max(r["target_date"] for r in record["rows"]) if record["rows"] else origin
    if datetime.now(timezone.utc).date()<=date.fromisoformat(target):raise ValueError("Future outcomes remain sealed")
    files=[p for p in Path("/data/review-v4/vintages").glob("*.json") if not p.name.endswith(".receipt.json")]
    needed={(r["series_id"],r["target_date"]) for r in record["rows"]}
    eligible=[]
    from .vintage_v4 import utc
    for file in files:
        v=json.loads(file.read_bytes())
        if v["cutoff"]<target or utc(v["retrieved_at"]).date()<=date.fromisoformat(target):continue
        present={(s["id"],p["date"]) for s in v["series"] for p in s["points"]}
        if needed<=present:eligible.append(v)
    if not eligible:return {"schema_version":4,"status":"pending_missing_outcomes","scores":None,"required_cells":len(needed)}
    truth=min(eligible,key=lambda v:v["retrieved_at"])
    return score_locked(record,commitment_sha,truth)
@app.function(image=light,cpu=.25,memory=512,timeout=120,volumes={"/data":data})
def retain_private(identifier,files):
    if not identifier.isalnum():raise ValueError("Private run identity")
    root=Path("/data/review-v4/evidence")/identifier;root.mkdir(parents=True,exist_ok=False)
    for name,raw in files.items():
        if Path(name).name!=name or not name.endswith(".json"):raise ValueError("Private filename")
        (root/name).write_bytes(raw)
    data.commit();return {"private_retained":True,"files":len(files)}
@app.function(image=light,cpu=.25,memory=1024,timeout=120,volumes={"/public":public})
def publish_operation(kind,payload):
    from .public_results import private_guard
    private_guard(payload)
    if kind not in ("initialize","feedback","capture","issuance","scoring","learning","market"):raise ValueError("Operation kind")
    public.reload();root=Path("/public/review-v4");root.mkdir(exist_ok=True);identifier=uuid.uuid4().hex
    raw=encoded(payload);version=root/(kind+"-"+identifier+".json");version.write_bytes(raw)
    pointer=root/"operations.json";state=json.loads(pointer.read_bytes()) if pointer.exists() else {"schema_version":4,"operations":{}}
    state["operations"][kind]={"artifact":version.name,"sha256":hashlib.sha256(raw).hexdigest(),"payload":payload};state["updated_at"]=datetime.now(timezone.utc).isoformat()
    temp=root/"operations.pending";temp.write_bytes(encoded(state));temp.replace(pointer);public.commit()
    return {"artifact":version.name,"sha256":hashlib.sha256(raw).hexdigest()}
@app.function(image=forecast_image,cpu=4,memory=8192,timeout=2400,max_containers=1,volumes={"/data":data},secrets=[modal.Secret.from_dict({"TINKER_API_KEY":os.environ["TINKER_API_KEY"]})] if os.environ.get("TINKER_API_KEY") else [])
def train_successor(task_set,mode="sft",resume_id="",parent_id=""):
    from .learning_v4 import train
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}",task_set):raise ValueError("Training task identity")
    for value in (resume_id,parent_id):
        if value and not re.fullmatch(r"[0-9a-f]{32}",value):raise ValueError("Private training identity")
    root=Path("/data/review-v4");tasks=json.loads((root/"training"/(task_set+".json")).read_bytes())
    run_root=root/"training-runs";run_root.mkdir(exist_ok=True);output=root/"training-reports"/uuid.uuid4().hex
    try:
        return asyncio.run(train(tasks,run_root,output,mode=mode,parent=str(run_root/parent_id/"selected.json") if parent_id else None,resume=str(run_root/resume_id/"resume.json") if resume_id else None))
    finally:data.commit()


@app.function(image=forecast_image,cpu=2,memory=4096,timeout=900,volumes={"/data":data})
def runtime_contract():
    import importlib.metadata
    import numpy as np
    from chronos import Chronos2Pipeline
    from .prospective_panel_v4 import protocol
    p=protocol();pipeline=Chronos2Pipeline.from_pretrained(p["chronos"]["model"],revision=p["chronos"]["revision"],device_map="cpu")
    quantiles,_=pipeline.predict_quantiles(inputs=[np.arange(1,65,dtype=np.float32)],prediction_length=8,quantile_levels=[.1,.5,.9],cross_learning=False)
    values=quantiles[0].detach().cpu().numpy()
    native_shape=list(values.shape)
    if values.shape==(1,8,3):values=values[0]
    values=values.tolist()
    if len(values)!=8 or any(len(row)!=3 or row!=sorted(row) for row in values):raise ValueError("Chronos runtime contract")
    from tinker_cookbook.recipes.decisions import Decision,DecisionRenderer
    from .prospective_panel_v4 import numerical
    from datetime import date,timedelta
    at=date(2000,8,1)
    synthetic={"series":[{"id":"hubbard-independent-a100-40","points":[{"date":(at-timedelta(days=i)).isoformat(),"value":2.+i*.001} for i in range(200)],"auxiliary":{}}]}
    fits,failures=numerical(synthetic,"hubbard-independent-a100-40","2000-08-02")
    if fits is None or len(fits)!=42 or any(len(rows)!=3 for rows in fits.values()):raise ValueError("Synthetic selector numerical contract")
    if any(row["fallback"] is not None for identifier in ("tree_28_3","tree_56_7") for row in fits[identifier]):raise ValueError("Core target-only tree adapter failed its synthetic contract")
    vintages=[]
    for file in Path("/data/review-v4/vintages").glob("*.json"):
        if file.name.endswith(".receipt.json"):continue
        value=json.loads(file.read_bytes())
        if "series" not in value:continue
        vintages.append({"snapshot_sha256":digest(value),"retrieved_at":value["retrieved_at"],"requested_cutoff":value["cutoff"],"source_objects":len(value["source_objects"]),"source_bytes":sum(o["bytes"] for o in value["source_objects"]),"actual_coverage":[{"series_id":s["id"],"observations":len(s["points"]),"first_observation":min((p["date"] for p in s["points"]),default=None),"last_observation":max((p["date"] for p in s["points"]),default=None),"quote_freshness_verified":False} for s in value["series"]]})
    return {"status":"passed","actual_retained_vintage_metadata":vintages,"synthetic_numerical_candidates":42,"synthetic_numerical_rows":126,"fallbacks":sum(r["fallback"] is not None for rows in fits.values() for r in rows),"fixture":"Explicitly synthetic increasing sequence; no historical prices or accuracy result","chronos_revision":p["chronos"]["revision"],"prediction_shape":[8,3],"native_prediction_shape":native_shape,"versions":{name:importlib.metadata.version(name) for name in ("tinker","tinker-cookbook","torch","transformers","chronos-forecasting")},"new_training_updates":0}

@app.function(image=light,cpu=.25,memory=512,timeout=120,volumes={"/data":data})
def retain_market(payload):
    from .public_results import private_guard
    private_guard(payload);root=Path("/data/review-v4/market");root.mkdir(parents=True,exist_ok=True)
    identifier=payload["run_id"]
    if len(identifier)!=32 or not identifier.isalnum():raise ValueError("Market run identity")
    file=root/(identifier+".json")
    with file.open("xb") as f:f.write(encoded(payload))
    data.commit();return {"retained_context_sha256":digest(payload)}

def main():
    p=argparse.ArgumentParser();p.add_argument("--mode",choices=["initialize","capture","issue","feedback","score","train","market"],required=True);p.add_argument("--origin");p.add_argument("--commitment-sha");p.add_argument("--task-set",default="original-pack-tasks");p.add_argument("--training-mode",choices=["sft","rl"],default="sft");p.add_argument("--resume-id",default="");p.add_argument("--parent-id",default="");a=p.parse_args()
    out=Path("artifacts/review-v4-operations");out.mkdir(parents=True,exist_ok=True)
    from urllib.request import urlopen
    if a.mode=="market":
        from .market_context_v4 import run as run_market
        private_dir=Path("inputs/private-market-v4");private_dir.mkdir(parents=True,exist_ok=True)
        with app.run():
            runtime=runtime_contract.remote()
        (out/"runtime-contract.json").write_bytes(encoded(runtime))
        payload=asyncio.run(run_market(private_dir,out/"market.json"))
        with app.run():
            retain_private.remote(payload["run_id"],{p.name:p.read_bytes() for p in private_dir.glob("*.json")})
            retain_market.remote(payload)
            receipt=publish_operation.remote("market",payload)
        (out/"market-publication.json").write_bytes(encoded(receipt))
    elif a.mode=="feedback":
        from .feedback_v4 import run
        archive=urlopen(ARCHIVE_URL,timeout=90).read();private_dir=Path("inputs/private-evidence-v4");private_dir.mkdir(parents=True,exist_ok=True)
        payload=asyncio.run(run(archive,private_dir,out/"feedback.json"))
        with app.run():
            retention=retain_private.remote(payload["provenance"]["run_id"],{p.name:p.read_bytes() for p in private_dir.glob("*.json")})
            receipt=publish_operation.remote("feedback",payload)
        (out/"feedback-retention.json").write_bytes(encoded(retention));(out/"feedback-publication.json").write_bytes(encoded(receipt))
    else:
        with app.run():
            if a.mode=="initialize":
                context=json.loads(Path("results/explorer-v3/history-and-traces.json").read_bytes());archive=urlopen(ARCHIVE_URL,timeout=90).read();payload=initialize.remote(context,archive,os.environ["GITHUB_SHA"]);kind="initialize"
            elif a.mode=="capture":
                cutoff=(datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat();payload=capture_source.remote(cutoff);kind="capture"
            elif a.mode=="issue":
                if not a.origin:raise ValueError("Origin required")
                # The scale comes only from original training tasks, never future outcomes.
                from .policy_v2 import make_tasks
                members,_=read_archive(urlopen(ARCHIVE_URL,timeout=90).read());_,grid=one(members,"/grid.json");tasks,_=make_tasks(grid)
                payload=issue_origin.remote(a.origin,next(t["scale"] for t in tasks if t["phase"]=="training"));kind="issuance"
            elif a.mode=="train":
                payload=train_successor.remote(a.task_set,a.training_mode,a.resume_id,a.parent_id);kind="learning"
            else:
                if not a.origin or not a.commitment_sha:raise ValueError("Locked commitment required")
                payload=score_origin.remote(a.origin,a.commitment_sha);kind="scoring"
            receipt=publish_operation.remote(kind,payload)
        (out/(a.mode+".json")).write_bytes(encoded(payload));(out/(a.mode+"-publication.json")).write_bytes(encoded(receipt))
    print("V4_OPERATION:"+json.dumps({"mode":a.mode,"status":payload.get("status","completed"),"publication":receipt}),flush=True)
if __name__=="__main__":main()
