"""Versioned v2 experiments. Frozen v1 numerical sources are never edited."""
from __future__ import annotations
import argparse,csv,hashlib,itertools,json,math,os,shutil,subprocess,tempfile,time,uuid,zipfile
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import modal
from .starter_probe import volume,PACK_SHA256,verify_manifest
from .representation_study import CONFIGS as RIDGE_CONFIGS,forecast_series,auxiliary_panels,features_at,ridge_prediction

MODEL="Qwen/Qwen3.5-4B"
REFS=("last_value","last_value_empirical","drift","seasonal_naive")
REGISTRY=[{"id":m,"family":"reference"} for m in REFS]
REGISTRY += [{**c,"family":"ridge"} for c in RIDGE_CONFIGS]
REGISTRY += [{"id":f"ar_{w}_{a}","family":"ar","days":w,"alpha":a} for w,a in itertools.product((28,56),(1,100))]
REGISTRY += [{"id":f"ewma_{a}","family":"ewma","days":56,"smoothing":a} for a in (.2,.6)]
REGISTRY += [{"id":f"tree_{w}_{leaves}","family":"tree","days":w,"leaves":leaves} for w,leaves in itertools.product((28,56),(3,7))]
REGISTRY += [{"id":f"ensemble_{w}","family":"ensemble","weight":w} for w in (.25,.5)]
REGISTRY += [{"id":f"coverage_{space}","family":"coverage","space":space,"days":56,"alpha":100} for space in ("level","log")]
BY_ID={c["id"]:c for c in REGISTRY}
assert len(BY_ID)==len(REGISTRY)<=48
ROOT=Path(__file__).resolve().parents[2]
app=modal.App("compute-forecast-v2-experiments")
image=(modal.Image.debian_slim(python_version="3.11")
       .pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","pyarrow>=16,<24","scikit-learn>=1.5,<2")
       .add_local_python_source("compute_forecast"))

def now():return datetime.now(timezone.utc).isoformat()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
REGISTERED_PROTOCOL=json.loads(r"""{"schema_version":2,"campaign":"compute-forecast-v2","registered_at_utc":"2026-11-15T01:46:58Z","original_release_sha":"2a9eecc96d5084b7c8b6c805487628eb6981ba28","measurement":"advertised_rental_offer_rate","dataset_sha256":"f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c","evaluation_status":"retrospective reuse of previously inspected pack; not an untouched or prospective test","training_origins":["2026-06-20","2026-06-27","2026-07-04","2026-07-11","2026-07-18","2026-07-24"],"development_origins":["2026-08-08","2026-08-15","2026-08-22"],"evaluation_origins":["2026-08-29","2026-09-05","2026-09-12"],"validation_lags_days":[7,14],"train_last_label":"2026-07-31","primary_contrast":"trained versus starting policy on the same six-trial tasks; static and adaptive search are competitive controls","trial_budget":6,"common_initial":["last_value","last_value_empirical"],"training_seeds":[17,29,43],"objectives":["hard","soft"],"learning_rate":0.00003,"sft_max_updates":100,"sft_checkpoints":[0,20,50,100],"rl_max_updates":60,"rl_seeds":[17,29,43],"rl_gate":"nonconstant training rewards and valid sampled-action probabilities","max_parallel_modal_containers":6,"exa_max_queries":40,"embargoed_competition_outcomes":"2026-11-07 through 2026-11-13; never loaded","protected_final_period":"2026-09-27 through 2026-10-25; not used in v2","cutoff_notes":["All training reward labels end by July31","Development labels end August29; evaluation begins August29 after matured prior labels","All partitions share a retrospective frozen pack; prior v1 development outcomes were published"],"selection_rule":"Select checkpoint by development pooled official pinball; ties choose earlier checkpoint. Freeze before v2 evaluation.","available_history_limitations":"No guarantee of historical real-time accessibility or absence of foundation-model pretraining contamination","compute_policy":{"topups":false,"billing_changes":false,"deadline":"2026-11-15T22:00:00Z","stop_new_campaigns_before":"2026-11-15T20:30:00Z","costs":"Provider receipts where available; unknown is not zero"}}""")
def protocol():
    return json.loads(json.dumps(REGISTERED_PROTOCOL))
def phase_for(origin):
    p=protocol()
    for phase,key in (("training","training_origins"),("development","development_origins"),("evaluation","evaluation_origins")):
        if origin in p[key]:return phase
    return "validation_support"
def registered_origins():
    p=protocol();tasks=p["training_origins"]+p["development_origins"]+p["evaluation_origins"]
    return sorted(set(tasks+[(date.fromisoformat(t)-timedelta(days=k)).isoformat() for t in tasks for k in p["validation_lags_days"]]))
def validate_origin(origin):
    if origin not in registered_origins() or date.fromisoformat(origin)+timedelta(days=7)>date(2026,9,19):
        raise ValueError("REFUSED: outside registered v2 retrospective period")
def audit_values(values,origin):
    at=date.fromisoformat(origin);days=sorted(d for d,v in values.items() if d<=at and v>0 and math.isfinite(v))
    changes=sum(values[a]!=values[b] for a,b in zip(days,days[1:]))
    return {"observations":len(days),"first_day":str(days[0]) if days else None,
            "last_day":str(days[-1]) if days else None,"price_changes":changes,
            "missing_calendar_days":(at-days[0]).days+1-len(days) if days else None,
            "days_since_last_observation":(at-days[-1]).days if days else None,
            "verified_quote_age_days":None,
            "freshness_note":"Observation recency is not verification that an unchanged quote was re-fetched."}
def basic_features(values,at):
    x=features_at(values,at,"level")
    if x is None:return None
    return x+[math.sin(2*math.pi*at.weekday()/7),math.cos(2*math.pi*at.weekday()/7)]
def calibrated(values,at,h,c):
    import numpy as np
    def point(t):
        if t not in values:return None
        if c["family"]=="ewma":
            ys=[values[t-timedelta(days=k)] for k in range(c["days"],-1,-1) if t-timedelta(days=k) in values]
            if len(ys)<12:return None
            level=ys[0]
            for y in ys[1:]:level=c["smoothing"]*y+(1-c["smoothing"])*level
            return float(level)
        xs=[];ys=[]
        for k in range(h,c["days"]+1):
            start=t-timedelta(days=k);end=start+timedelta(days=h)
            x=basic_features(values,start)
            if x is not None and end in values:
                xs.append(x);ys.append(values[end]-values[start])
        query=basic_features(values,t)
        if len(xs)<12 or query is None:return None
        return float(values[t]+ridge_prediction(xs,ys,query,c["alpha"]))
    center=point(at)
    if center is None:return None,"insufficient_matured_fit_labels"
    residuals=[]
    for k in range(h,h+22):
        start=at-timedelta(days=k);end=start+timedelta(days=h)
        pred=point(start)
        if pred is not None and end in values:residuals.append(values[end]-pred)
    if len(residuals)<8:return None,"insufficient_prequential_residuals"
    return np.maximum(center+np.quantile(residuals,[.1,.5,.9]),1e-6).tolist(),None
def predict_custom(values,origin,h,c,extras,baseline,cache):
    import numpy as np
    key=(c["id"],h)
    if key in cache:return cache[key]
    at=date.fromisoformat(origin);reason=None;repair=False
    if c["family"]=="ridge":
        qs,reason=forecast_series(values,at,h,c,extras)
    elif c["family"]=="coverage":
        masked={}
        for family,panel in extras.items():
            masked[family]={d:{k:v for k,v in row.items() if k in ("coverage","log_configs","provider_hhi")} for d,row in panel.items()}
        old={"space":c["space"],"aux":"fixed_basket","days":56,"alpha":100}
        qs,reason=forecast_series(values,at,h,old,masked)
    elif c["family"] in ("ar","ewma"):
        qs,reason=calibrated(values,at,h,c)
    elif c["family"]=="tree":
        from sklearn.ensemble import HistGradientBoostingRegressor
        xs=[];ys=[]
        for k in range(h,c["days"]+1):
            start=at-timedelta(days=k);end=start+timedelta(days=h)
            x=basic_features(values,start)
            if x is not None and end in values:xs.append(x);ys.append(values[end]-values[start])
        query=basic_features(values,at)
        if len(xs)<24 or query is None:qs,reason=None,"insufficient_tree_labels"
        else:
            qs=[]
            for q in (.1,.5,.9):
                model=HistGradientBoostingRegressor(loss="quantile",quantile=q,max_iter=40,max_leaf_nodes=c["leaves"],min_samples_leaf=8,l2_regularization=1,early_stopping=False,random_state=17)
                model.fit(xs,ys);qs.append(max(1e-6,float(values[at]+model.predict([query])[0])))
            repair=qs!=sorted(qs);qs=sorted(qs)
    elif c["family"]=="ensemble":
        component,why,_=predict_custom(values,origin,h,BY_ID["ar_56_100"],extras,baseline,cache)
        if why:qs,reason=None,"ensemble_component_"+why
        else:qs=[(1-c["weight"])*b+c["weight"]*v for b,v in zip(baseline,component)]
    else:raise ValueError("Unregistered numerical family")
    result=(qs,reason,repair);cache[key]=result;return result

def unpack():
    temporary=Path(tempfile.mkdtemp(prefix="compute-v2-"));archive=temporary/"pack.zip"
    shutil.copyfile("/data/pacific/pack.zip",archive)
    with archive.open("rb") as f:
        if hashlib.file_digest(f,"sha256").hexdigest()!=PACK_SHA256:raise ValueError("Archive digest mismatch")
    with zipfile.ZipFile(archive) as z:
        for m in z.infolist():
            p=Path(m.filename)
            if p.is_absolute() or ".." in p.parts or (m.external_attr>>16)&0o170000==0o120000:raise ValueError("Unsafe archive")
        z.extractall(temporary/"pack")
    manifests=list((temporary/"pack").rglob("MANIFEST.sha256"))
    if len(manifests)!=1:raise ValueError("Pack manifest ambiguous")
    root=manifests[0].parent
    if verify_manifest(root)!=672:raise ValueError("Manifest file count changed")
    return temporary,root
def invoke(root,work,label,args):
    result=subprocess.run(["python","-I","-B",str(root/"starter"/args[0]),*args[1:]],capture_output=True,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1"))
    (work/(label+".stdout.txt")).write_text(result.stdout);(work/(label+".stderr.txt")).write_text(result.stderr)
    if result.returncode:raise RuntimeError(label+": "+result.stderr[-1800:])
def build_history(root,work,origin):
    import pandas as pd
    invoke(root,work,"build_history",["build_series.py","--pack",str(root),"--cutoff",origin,"--out",str(work/"history.csv"),"--catalog",str(work/"catalog.csv"),"--report",str(work/"build-history.json")])
    hist=pd.read_csv(work/"history.csv");cat=pd.read_csv(work/"catalog.csv",keep_default_na=False)
    if not {"series_id","date","value"}<=set(hist) or not {"series_id","tier","table","source_id","gpu_model","instrument_class","pricing_tier","statistic"}<=set(cat):raise ValueError("Official schema changed")
    hist["day"]=pd.to_datetime(hist["date"]).dt.date
    if len(hist) and hist["day"].max()>date.fromisoformat(origin):raise ValueError("History crossed origin")
    return hist,cat
META=("series_id","tier","table","source_id","gpu_model","instrument_class","pricing_tier","statistic")
def metadata(frame):return [{k:str(row[k]) for k in META} for row in frame.to_dict("records")]
def scope_catalog(cat):
    return cat[(cat["tier"]=="headline")&cat["gpu_model"].str.upper().str.startswith(("H100","A100"))&(cat["table"]=="daily_statistics")].copy()

@app.function(image=image,cpu=4,memory=8192,timeout=1800,max_containers=6,volumes={"/data":volume})
def audit_pack():
    import duckdb
    started=time.perf_counter();temp,root=unpack();work=temp/"work";work.mkdir()
    observations=[]
    for origin in ("2026-06-20","2026-07-24","2026-08-22","2026-09-12","2026-11-06"):
        atwork=work/origin;atwork.mkdir();hist,cat=build_history(root,atwork,origin)
        selected=scope_catalog(cat)
        values={sid:dict(zip(rows["day"],rows["value"])) for sid,rows in hist.groupby("series_id")}
        panels,baskets=auxiliary_panels(root,origin)
        observations.append({"origin":origin,"headline_catalog":metadata(cat[cat["tier"]=="headline"]),"eligible_daily_h100_a100":metadata(selected),
            "excluded_h100_a100_non_daily":metadata(cat[(cat["tier"]=="headline")&cat["gpu_model"].str.upper().str.startswith(("H100","A100"))&(cat["table"]!="daily_statistics")]),
            "series_audit":[{"series_id":sid,**audit_values(values.get(sid,{}),origin)} for sid in selected["series_id"]],
            "basket_audit":baskets})
    pattern=str(root/"rental_observations"/"*"/"*"/"*.parquet")
    con=duckdb.connect()
    raw_audit=con.execute("SELECT source_id,COUNT(*) n,COUNT(*) FILTER(WHERE provider IS NULL OR sku_raw IS NULL OR region_canonical IS NULL OR gpu_count IS NULL OR gpu_memory_gb IS NULL) missing_identity_rows,COUNT(*) FILTER(WHERE CAST(snapshot_ts_utc AS DATE)>CAST(dt AS DATE)) capture_after_observation_date_rows FROM read_parquet(?,hive_partitioning=false) GROUP BY source_id",[pattern]).fetchdf().to_dict("records")
    out={"schema_version":2,"kind":"data_eligibility_audit","created_at":now(),"dataset_sha256":PACK_SHA256,"manifest_entries":672,
         "observations":observations,"capture_audit":raw_audit,"runtime_seconds":time.perf_counter()-started,
         "historical_availability":"retrospective frozen pack; captures at outer cutoff do not establish each residual's own vintage",
         "raw_data_redistributed":False,"cost_status":"unavailable","cost":None,"modal_call_id":modal.current_function_call_id()}
    run=uuid.uuid4().hex;write(Path("/data/campaign-v2/audit")/(run+".json"),out);volume.commit();shutil.rmtree(temp);return out

@app.function(image=image,cpu=4,memory=8192,timeout=3600,max_containers=6,volumes={"/data":volume})
def evaluate_origin(origin,config_ids=None,scope_ids=None):
    import importlib.metadata
    import pandas as pd
    validate_origin(origin);started=time.perf_counter();temp,root=unpack();work=temp/"work";work.mkdir()
    hist,cat=build_history(root,work,origin);primary=scope_catalog(cat)
    if scope_ids is not None:primary=primary[primary["series_id"].isin(scope_ids)].copy()
    run=uuid.uuid4().hex;output=Path("/data/campaign-v2/experiments")/run;output.mkdir(parents=True)
    selected=list(BY_ID) if config_ids is None else list(config_ids)
    if set(selected)-set(BY_ID):raise ValueError("Unregistered experiment")
    label_end=(date.fromisoformat(origin)+timedelta(days=7)).isoformat()
    if primary.empty:
        shutil.rmtree(temp);return {"origin":origin,"status":"ineligible","catalog":[],"methods":[],"label_end":label_end,"run_id":run}
    primary_path=work/"primary.csv";primary.to_csv(primary_path,index=False)
    invoke(root,work,"build_truth",["build_series.py","--pack",str(root),"--cutoff",label_end,"--members-from",str(work/"catalog.csv"),"--out",str(work/"truth.csv"),"--catalog",str(work/"truth-catalog.csv"),"--report",str(work/"build-truth.json")])
    values={sid:dict(zip(rows["day"],rows["value"])) for sid,rows in hist.groupby("series_id")}
    panels,baskets=auxiliary_panels(root,origin);baselines={};methods=[]
    for method in REFS:
        invoke(root,work,"baseline_"+method,["baselines.py","--history",str(work/"history.csv"),"--origin",origin,"--method",method,"--catalog",str(primary_path),"--tier","headline","--frozen","--out",str(work/(method+"_all.csv"))])
        with (work/(method+"_all.csv")).open() as f:
            baselines[method]=[{k:r[k] for k in ("series_id","origin_date","horizon_days","q10","q50","q90")} for r in csv.DictReader(f) if int(r["horizon_days"]) in (1,3,7)]
    baseline={(r["series_id"],int(r["horizon_days"])):r for r in baselines["last_value_empirical"]}
    cache_by_series={}
    for identifier in selected:
        c=BY_ID[identifier];fallbacks={};repairs=0
        if c["family"]=="reference":rows=baselines[identifier]
        else:
            rows=[]
            for item in primary.to_dict("records"):
                sid=item["series_id"];extra=panels.get(tuple(str(item[k]) for k in ("source_id","instrument_class","gpu_model","pricing_tier")),{})
                cache=cache_by_series.setdefault(sid,{})
                for h in (1,3,7):
                    row=dict(baseline[sid,h]);b=[float(row[k]) for k in ("q10","q50","q90")]
                    qs,reason,repair=predict_custom(values.get(sid,{}),origin,h,c,extra,b,cache)
                    if reason:fallbacks[reason]=fallbacks.get(reason,0)+1
                    else:row.update(dict(zip(("q10","q50","q90"),qs)))
                    repairs+=int(repair);rows.append(row)
        forecast=work/(identifier+".csv")
        with forecast.open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=("series_id","origin_date","horizon_days","q10","q50","q90"));writer.writeheader();writer.writerows(rows)
        score=work/(identifier+"-score.json");cells=work/(identifier+"-cells.csv")
        invoke(root,work,"score_"+identifier,["scorer.py","--forecast",str(forecast),"--truth",str(work/"truth.csv"),"--history",str(work/"history.csv"),"--frozen-cutoff",origin,"--catalog",str(primary_path),"--tier","headline","--out",str(score),"--per-cell",str(cells)])
        scored=json.loads(score.read_text())
        if scored["forecast_validation"]["n_problems"] or scored["cells"]["missing_forecast"]:raise ValueError("Invalid official forecast")
        cases=[]
        with cells.open() as f:
            for r in csv.DictReader(f):
                try:loss=float(r["loss"]);base=float(r["baseline_loss"]);truth=float(r["y"]);lo=float(r["q10"]);hi=float(r["q90"])
                except (ValueError,TypeError):continue
                if math.isfinite(loss) and math.isfinite(base):
                    cases.append({"series_id":r["series_id"],"horizon_days":int(r["horizon_days"]),"loss":loss,"baseline_loss":base,"covered":lo<=truth<=hi,"width":hi-lo})
        if len(cases)!=scored["overall"]["n_cells"]:raise ValueError("Scored cell mismatch")
        metric=sum(r["loss"] for r in cases)/len(cases)
        if abs(metric-scored["overall"]["pinball"])>.00000051:raise ValueError("Official aggregate disagrees")
        methods.append({"config_id":identifier,"pinball":metric,"n_cells":len(cases),"cases":cases,"fallbacks":fallbacks,"quantile_order_repairs":repairs,"official_overall":scored["overall"]})
    report={"schema_version":2,"origin":origin,"phase":phase_for(origin),"status":"completed","label_end":label_end,"run_id":run,
        "dataset_sha256":PACK_SHA256,"catalog":metadata(primary),"methods":methods,"basket_audit":baskets,
        "series_audit":[{"series_id":sid,**audit_values(values.get(sid,{}),origin)} for sid in primary["series_id"]],
        "runtime_seconds":time.perf_counter()-started,"modal_call_id":modal.current_function_call_id(),"cache_hit":False,"new_numerical_execution":True,
        "cost_status":"unavailable","cost":None,"historical_availability":"retrospective frozen pack, not real-time vintage proof",
        "packages":{n:importlib.metadata.version(n) for n in ("numpy","pandas","scikit-learn","duckdb")}}
    for p in work.iterdir():
        if p.is_file():shutil.copyfile(p,output/p.name)
    write(output/"summary.json",report);volume.commit();shutil.rmtree(temp);return report

@app.local_entrypoint()
def main(mode:str="audit",output:str="artifacts/v2",smoke:bool=True):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    if mode=="audit":
        report=audit_pack.remote();report["code_sha"]=os.environ.get("GITHUB_SHA")
        write(out/"data-audit.json",report);print("AUDIT_JSON:"+json.dumps(report,allow_nan=False))
    elif mode=="grid":
        origins=["2026-07-24","2026-08-22"] if smoke else registered_origins()
        reports=[]
        for r in evaluate_origin.map(origins,order_outputs=False):
            reports.append(r);write(out/"grid.json",{"schema_version":2,"code_sha":os.environ.get("GITHUB_SHA"),"protocol":protocol(),"registry":REGISTRY,"origins":reports})
            print("V2_ORIGIN:"+json.dumps({k:r.get(k) for k in ("origin","status","run_id","runtime_seconds","modal_call_id")}))
        report={"origins":len(reports),"eligible":sum(r["status"]=="completed" for r in reports),"methods":len(REGISTRY)}
    else:raise ValueError("Unknown mode")
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
        f.write("# V2 "+mode+"\n\nRetrospective experimental campaign; frozen v1 unchanged.\n\n")
        f.write("~~~json\n"+json.dumps(report if mode!="audit" else {"manifest_entries":report["manifest_entries"],"capture_audit":report["capture_audit"],"origins":[{"origin":r["origin"],"headline":len(r["headline_catalog"]),"eligible_daily_h100_a100":len(r["eligible_daily_h100_a100"])} for r in report["observations"]]},indent=2)+"\n~~~\n")
