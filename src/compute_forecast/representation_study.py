"""Preregistered 24-arm study; actual official targets and scorer, remote execution only."""
from __future__ import annotations
import csv
import hashlib
import itertools
import json
import math
import os
from datetime import date, timedelta
from pathlib import Path
import modal
from .starter_probe import PACK_NAME, PACK_SHA256, volume

TRAIN_TASKS = ["2026-05-09", "2026-05-16", "2026-05-23", "2026-05-30", "2026-06-06", "2026-06-13", "2026-06-20", "2026-06-27", "2026-07-04", "2026-07-11", "2026-07-18", "2026-07-24"]
DEV_TASKS = ["2026-08-08", "2026-08-15", "2026-08-22", "2026-08-29", "2026-09-05", "2026-09-12"]
METHODS = ("last_value", "last_value_empirical", "drift", "seasonal_naive")
CONFIGS = [{"id": f"ridge_{space}_{aux}_{days}_{alpha}", "space": space, "aux": aux, "days": days, "alpha": alpha} for space,aux,days,alpha in itertools.product(("level","log"),("target_only","raw","fixed_basket"),(28,56),(1,100))]
ORIGINS = sorted({(date.fromisoformat(t)-timedelta(days=d)).isoformat() for t in TRAIN_TASKS+DEV_TASKS for d in (0,7,14,21)})
app = modal.App("compute-forecast-representation-study")
image = modal.Image.debian_slim(python_version="3.11").pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","pyarrow>=16,<24").add_local_python_source("compute_forecast")

def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")

def features_at(values, day, space, extra=None):
    import numpy as np
    if day not in values or values[day] <= 0:
        return None
    transform = math.log if space == "log" else float
    now = transform(values[day])
    changes = [now-transform(values[day-timedelta(days=k)]) if day-timedelta(days=k) in values and values[day-timedelta(days=k)]>0 else float("nan") for k in (1,3,7)]
    returns = [math.log(values[t]/values[t-timedelta(days=1)]) for k in range(7) if (t:=day-timedelta(days=k)) in values and t-timedelta(days=1) in values and values[t]>0 and values[t-timedelta(days=1)]>0]
    x = [now, *changes, float(np.std(returns)) if returns else float("nan"), len(returns)/7]
    if extra is not None:
        row = extra.get(day, {})
        x += [row.get(k,float("nan")) for k in ("log_index", "change_1", "change_3", "change_7", "coverage", "log_configs", "provider_hhi")]
    return x

def ridge_prediction(x, y, query, alpha):
    import numpy as np
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float); query=np.asarray(query,dtype=float)
    # Training-only imputation, scaling and missingness indicators.
    masks=np.isfinite(x)
    means=np.divide(np.where(masks,x,0).sum(axis=0),masks.sum(axis=0),out=np.zeros(x.shape[1]),where=masks.sum(axis=0)>0)
    clean=np.where(masks,x,means); q=np.where(np.isfinite(query),query,means)
    clean=np.concatenate((clean,(~masks).astype(float)),axis=1)
    q=np.concatenate((q,(~np.isfinite(query)).astype(float)))
    center=clean.mean(axis=0); scale=clean.std(axis=0); scale=np.where(scale>1e-12,scale,1)
    clean=(clean-center)/scale; q=(q-center)/scale
    ymean=y.mean(); weights=np.linalg.solve(clean.T@clean+alpha*np.eye(clean.shape[1]),clean.T@(y-ymean))
    return float(ymean+q@weights)

def forecast_series(values, origin, horizon, config, extras):
    import numpy as np
    transform=math.log if config["space"]=="log" else float
    extra=extras.get(config["aux"]) if config["aux"]!="target_only" else None
    if config["aux"]!="target_only" and not extra:
        return None,"unsupported_auxiliary_contract"
    def predict_at(at):
        query=features_at(values,at,config["space"],extra)
        if query is None:
            return None
        x,y=[],[]
        for k in range(horizon,config["days"]+1):
            t=at-timedelta(days=k); end=t+timedelta(days=horizon)
            vector=features_at(values,t,config["space"],extra)
            if vector is not None and end in values and values[end]>0:
                x.append(vector);y.append(transform(values[end])-transform(values[t]))
        if len(x)<12:
            return None
        return ridge_prediction(x,y,query,config["alpha"])
    delta=predict_at(origin)
    if delta is None:
        return None,"insufficient_matured_fit_labels"
    residuals=[]
    for k in range(horizon,22):
        t=origin-timedelta(days=k); end=t+timedelta(days=horizon)
        if t not in values or end not in values or values[t]<=0 or values[end]<=0:
            continue
        prediction=predict_at(t)
        if prediction is not None:
            residuals.append(transform(values[end])-transform(values[t])-prediction)
    if len(residuals)<5:
        return None,"insufficient_prequential_residuals"
    center=transform(values[origin])+delta
    quantiles=center+np.quantile(residuals,[.1,.5,.9])
    if config["space"]=="log":
        quantiles=np.exp(np.clip(quantiles,-30,30))
    quantiles=np.maximum(quantiles,1e-6)
    return [float(q) for q in quantiles],None

def auxiliary_panels(root, cutoff):
    import duckdb
    import pandas as pd
    import numpy as np
    con=duckdb.connect()
    pattern=str(root/"rental_observations"/"*"/"*"/"*.parquet")
    required={"dt","snapshot_ts_utc","provider","gpu_model","pricing_tier","instrument_class","source_id","sku_raw","region_canonical","gpu_count","gpu_memory_gb","usd_per_gpu_hour","quality_flag"}
    schema={row[0] for row in con.execute("DESCRIBE SELECT * FROM read_parquet(?,hive_partitioning=false)",[pattern]).fetchall()}
    if not required<=schema:
        raise RuntimeError("REFUSED: offer schema differs from verified DATA.md: "+str(sorted(required-schema)))
    raw=con.execute("SELECT * FROM read_parquet(?,hive_partitioning=false) WHERE source_id='afhubbard' AND CAST(dt AS DATE)<=CAST(? AS DATE) AND usd_per_gpu_hour>0 AND quality_flag='ok'",[pattern,cutoff]).df()
    raw["day"]=pd.to_datetime(raw["dt"],utc=True).dt.date
    raw["captured"]=pd.to_datetime(raw["snapshot_ts_utc"],utc=True,errors="raise")
    bound=pd.Timestamp(cutoff+"T23:59:59.999999Z")
    raw=raw[raw["captured"]<=bound].copy()
    identity=["provider","sku_raw","region_canonical","gpu_count","gpu_memory_gb"]
    for column in identity:
        raw[column]=raw[column].astype("string").fillna("<missing>")
    raw["config_key"]=raw[identity].agg("|".join,axis=1)
    keys=["source_id","instrument_class","gpu_model","pricing_tier"]
    panels={}; audit=[]
    for key,group in raw.groupby(keys,dropna=False):
        if not str(key[2]).upper().startswith(("H100","A100")):
            continue
        group=group.sort_values("captured").drop_duplicates(["day","config_key"],keep="last")
        first=min(group["day"]);anchor_end=first+timedelta(days=6)
        anchor=group[group["day"]<=anchor_end].groupby("config_key")["usd_per_gpu_hour"].median()
        anchor=anchor[anchor>0]
        if not len(anchor):
            continue
        anchor_hash=hashlib.sha256(json.dumps({str(k):float(v) for k,v in anchor.items()},sort_keys=True).encode()).hexdigest()
        raw_panel={};basket_panel={}
        for day,rows in group.groupby("day"):
            if day<anchor_end:continue
            prices=rows.set_index("config_key")["usd_per_gpu_hour"]
            matched=prices.reindex(anchor.index);coverage=float(matched.notna().mean())
            shares=rows.groupby("provider").size()/len(rows)
            common={"coverage":coverage,"log_configs":math.log1p(len(rows)),"provider_hhi":float((shares**2).sum())}
            pooled=float(rows["usd_per_gpu_hour"].median())
            raw_panel[day]={**common,"log_index":math.log(pooled)}
            index=float(np.log(matched/anchor).mean()) if coverage==1 and day>=anchor_end else float("nan")
            basket_panel[day]={**common,"log_index":index}
        for panel in (raw_panel,basket_panel):
            for day,row in panel.items():
                for lag in (1,3,7):
                    before=panel.get(day-timedelta(days=lag),{}).get("log_index",float("nan"))
                    row["change_"+str(lag)]=row["log_index"]-before
        panels[tuple(str(v) for v in key)]={"raw":raw_panel,"fixed_basket":basket_panel}
        audit.append({"contract":list(key),"anchor_start":first.isoformat(),"anchor_end":anchor_end.isoformat(),"members":len(anchor),"membership_sha256":anchor_hash,"last_day":max(group["day"]).isoformat(),"complete_basket_days":sum(r["coverage"]==1 for d,r in basket_panel.items() if d>=anchor_end),"days":len(basket_panel),"missing_identity_rows":int(group[identity].eq("<missing>").any(axis=1).sum())})
    return panels,audit

@app.function(image=image,cpu=4,memory=8192,timeout=1800,max_containers=6,volumes={"/data":volume})
def evaluate_origin(origin: str):
    import importlib.metadata
    import shutil
    import subprocess
    import tempfile
    import time
    import uuid
    import zipfile
    from datetime import datetime,timezone
    import pandas as pd
    started=time.perf_counter()
    if origin not in ORIGINS or date.fromisoformat(origin)+timedelta(days=7)>=date(2026,9,27):
        raise ValueError("REFUSED: origin is outside the registered development protocol")
    run_id=uuid.uuid4().hex
    output=Path("/data/representation")/run_id;output.mkdir(parents=True)
    # One sequential immutable archive read, then fast ephemeral container storage.
    temporary=Path(tempfile.mkdtemp(prefix="pacific-study-"))
    archive=temporary/"pack.zip";shutil.copyfile("/data/pacific/pack.zip",archive)
    with archive.open("rb") as f:
        if hashlib.file_digest(f,"sha256").hexdigest()!=PACK_SHA256:
            raise RuntimeError("REFUSED: archive hash mismatch")
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            p=Path(member.filename)
            if p.is_absolute() or ".." in p.parts or (member.external_attr>>16)&0o170000==0o120000:
                raise RuntimeError("REFUSED: unsafe archive")
        z.extractall(temporary/"pack")
    root=next((temporary/"pack").rglob("MANIFEST.sha256")).parent
    local=temporary/"work";local.mkdir()
    commands=[]
    def invoke(label,args):
        result=subprocess.run(["python","-I","-B",str(root/"starter"/args[0]),*args[1:]],capture_output=True,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1"))
        (local/(label+".stdout.txt")).write_text(result.stdout);(local/(label+".stderr.txt")).write_text(result.stderr)
        commands.append({"label":label,"arguments":args,"returncode":result.returncode})
        if result.returncode:
            raise RuntimeError(label+" failed: "+result.stderr[-3000:])
    history=local/"history.csv";catalog=local/"catalog.csv";truth=local/"truth.csv"
    invoke("build_history",["build_series.py","--pack",str(root),"--cutoff",origin,"--out",str(history),"--catalog",str(catalog),"--report",str(local/"history-build.json")])
    label_end=(date.fromisoformat(origin)+timedelta(days=7)).isoformat()
    invoke("build_truth",["build_series.py","--pack",str(root),"--cutoff",label_end,"--members-from",str(catalog),"--out",str(truth),"--catalog",str(local/"truth-catalog.csv"),"--report",str(local/"truth-build.json")])
    cat=pd.read_csv(catalog,keep_default_na=False)
    required={"series_id","tier","table","source_id","gpu_model","instrument_class","pricing_tier","statistic"}
    if not required<=set(cat.columns):
        raise RuntimeError("REFUSED: official catalog contract changed")
    primary=cat[(cat["tier"]=="headline")&(cat["table"]=="daily_statistics")&(cat["source_id"]=="afhubbard")&cat["gpu_model"].str.upper().str.startswith(("H100","A100"))].copy()
    if primary.empty:
        report={"schema_version":"1","is_synthetic":False,"status":"ineligible","reason":"No primary contracts meet the preregistered official headline criteria","run_id":run_id,"origin":origin,"label_end":label_end,"dataset_sha256":PACK_SHA256,"primary_catalog":[],"results":[],"per_cell_columns":[],"runtime_seconds":time.perf_counter()-started,"final_period_opened":False}
        dump(output/"summary.json",report);volume.commit();shutil.rmtree(temporary)
        return report
    primary_path=local/"primary-catalog.csv";primary.to_csv(primary_path,index=False)
    ids=set(primary["series_id"])
    hist=pd.read_csv(history);hist["day"]=pd.to_datetime(hist["date"]).dt.date
    at=date.fromisoformat(origin)
    if hist["day"].max()>at:
        raise RuntimeError("REFUSED: history crossed the forecast cutoff")
    values={sid:dict(zip(rows["day"],rows["value"])) for sid,rows in hist[hist["series_id"].isin(ids)].groupby("series_id")}
    panels,basket_audit=auxiliary_panels(root,origin)
    dump(local/"basket-audit.json",basket_audit)
    results=[]
    def score(identifier,forecast,fallbacks):
        report=local/("score_"+identifier+".json");cells=local/("cells_"+identifier+".csv")
        invoke("score_"+identifier,["scorer.py","--forecast",str(forecast),"--truth",str(truth),"--history",str(history),"--frozen-cutoff",origin,"--catalog",str(primary_path),"--tier","headline","--out",str(report),"--per-cell",str(cells)])
        scored=json.loads(report.read_text())
        if scored["forecast_validation"]["n_problems"] or scored["cells"]["missing_forecast"]:
            raise RuntimeError("REFUSED: invalid candidate export")
        with cells.open() as f:
            measured=list(csv.DictReader(f))
        valid=[]
        for row in measured:
            try: loss=float(row["loss"]);baseline_loss=float(row["baseline_loss"])
            except (TypeError,ValueError):continue
            if math.isfinite(loss) and math.isfinite(baseline_loss):
                valid.append({"series_id":row["series_id"],"horizon_days":int(row["horizon_days"]),"loss":loss,"baseline_loss":baseline_loss})
        if len(valid)!=scored["overall"]["n_cells"]:
            raise RuntimeError("REFUSED: exact per-cell count differs from official report")
        exact_loss=sum(r["loss"] for r in valid)/len(valid)
        exact_baseline=sum(r["baseline_loss"] for r in valid)/len(valid)
        if abs(exact_loss-scored["overall"]["pinball"])>0.00000051:
            raise RuntimeError("REFUSED: per-cell loss disagrees with official scorer")
        exact={"n_cells":len(valid),"pinball":exact_loss,"baseline_pinball":exact_baseline,"skill_pooled":1-exact_loss/exact_baseline if exact_baseline>0 else None,"provenance":"Unrounded loss columns emitted by the unmodified official scorer"}
        results.append({"config_id":identifier,"exact_metrics":exact,"exact_cases":valid,"overall":scored["overall"],"by_horizon":scored["by_horizon"],"scope":scored["scope"],"cells":scored["cells"],"fallbacks":fallbacks,"per_series":scored["per_series"]})
    baseline_rows={}
    for method in METHODS:
        full=local/("all_"+method+".csv")
        invoke("baseline_"+method,["baselines.py","--history",str(history),"--origin",origin,"--method",method,"--catalog",str(primary_path),"--tier","headline","--frozen","--out",str(full)])
        with full.open() as f:
            rows=[r for r in csv.DictReader(f) if int(r["horizon_days"]) in (1,3,7) and r["series_id"] in ids]
        baseline_rows[method]=rows
        forecast=local/("forecast_"+method+".csv")
        with forecast.open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        score(method,forecast,{})
    fallback={(r["series_id"],int(r["horizon_days"])):r for r in baseline_rows["last_value_empirical"]}
    for config in CONFIGS:
        rows=[];failures={}
        for item in primary.to_dict("records"):
            sid=item["series_id"];key=tuple(str(item[k]) for k in ("source_id","instrument_class","gpu_model","pricing_tier"))
            for h in (1,3,7):
                row=dict(fallback[(sid,h)])
                qs,reason=forecast_series(values.get(sid,{}),at,h,config,panels.get(key,{}))
                if reason:
                    failures[reason]=failures.get(reason,0)+1
                else:
                    row.update(dict(zip(("q10","q50","q90"),qs)))
                row.pop("method_note",None)
                rows.append(row)
        forecast=local/("forecast_"+config["id"]+".csv")
        with forecast.open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        score(config["id"],forecast,failures)
    files=[]
    for path in sorted(local.iterdir()):
        if path.is_file():
            payload=path.read_bytes();files.append({"path":path.name,"bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest()})
            shutil.copyfile(path,output/path.name)
    vectors=[v for series in values.values() if (v:=features_at(series,at,"log")) is not None]
    report={"schema_version":"1","is_synthetic":False,"status":"completed","run_id":run_id,"origin":origin,"label_end":label_end,"dataset_sha256":PACK_SHA256,"scope":"afhubbard official headline daily_statistics H100/A100; targets unchanged","primary_catalog":primary.to_dict("records"),"configs":CONFIGS,"observation":{"n_primary_series":len(primary),"mean_log_changes":[float(sum(v[i] for v in vectors if math.isfinite(v[i]))/max(1,sum(math.isfinite(v[i]) for v in vectors))) for i in (1,2,3,4)]},"results":results,"basket_audit":basket_audit,"commands":commands,"artifacts":files,"runtime_seconds":time.perf_counter()-started,"modal_call_id":modal.current_function_call_id(),"cost_status":"unavailable","cost_value":None,"created_at":datetime.now(timezone.utc).isoformat(),"final_period_opened":False,"per_cell_columns":next(csv.reader((local/"cells_drift.csv").open())),"packages":{n:importlib.metadata.version(n) for n in ("numpy","pandas","duckdb","pyarrow")}}
    dump(output/"summary.json",report);volume.commit();shutil.rmtree(temporary)
    return report

@app.local_entrypoint()
def main(output: str="artifacts/representation-grid.json", smoke: bool=True):
    # Smoke the complete 24-arm numerical path before starting all chronological folds.
    origins=["2026-07-24","2026-08-08"] if smoke else ORIGINS
    reports=[]
    for report in evaluate_origin.map(origins,order_outputs=False):
        report["code_sha"]=os.environ.get("GITHUB_SHA");reports.append(report)
        destination=Path(output);destination.parent.mkdir(parents=True,exist_ok=True)
        dump(destination,{"protocol":"representation-study-v2","code_sha":os.environ.get("GITHUB_SHA"),"final_period_opened":False,"origins":reports})
        print(json.dumps({"origin":report["origin"],"run_id":report["run_id"],"runtime_seconds":report["runtime_seconds"],"n_primary_series":len(report["primary_catalog"])}))
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
            f.write("## Actual representation study: "+report["origin"]+"\n\n")
            f.write("Primary H100/A100 series: "+str(len(report["primary_catalog"]))+". Official targets and scorer retained. Final period unopened.\n\n")
            concise={"origin":report["origin"],"run_id":report["run_id"],"runtime_seconds":report["runtime_seconds"],"per_cell_columns":report["per_cell_columns"],"results":[{"config_id":r["config_id"],"pinball":r["overall"]["pinball"],"skill_pooled":r["overall"]["skill_pooled"],"fallbacks":r["fallbacks"]} for r in report["results"]]}
            text=json.dumps(concise,indent=2)
            for start in range(0,len(text),3000):
                f.write("~~~json\n"+text[start:start+3000]+"\n~~~\n\n")
