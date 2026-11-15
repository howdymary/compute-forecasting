"""Diagnostic: remove every price predictor, retain coverage and availability."""
from __future__ import annotations
import csv,json,math,os,shutil,statistics,time,uuid
from datetime import date,timedelta
from pathlib import Path
import modal
from .campaign_v2 import image,unpack,invoke,validate_origin,now,write,digest,protocol
from .representation_study import auxiliary_panels,ridge_prediction
from .starter_probe import volume,PACK_SHA256
app=modal.App("compute-forecast-v2-price-free")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
def availability_features(values,at,panel):
    row=panel.get(at,{})
    return [float(at-timedelta(days=k) in values) for k in (0,1,3,7)]+[sum(at-timedelta(days=k) in values for k in range(28))/28]+[float(row.get(k,float("nan"))) for k in ("coverage","log_configs","provider_hhi")]
def predict(values,at,h,panel,space):
    import numpy as np
    transform=math.log if space=="log" else float
    def point(t):
        xs=[];ys=[]
        for k in range(h,57):
            start=t-timedelta(days=k);end=start+timedelta(days=h)
            if end in values and values[end]>0:
                xs.append(availability_features(values,start,panel));ys.append(transform(values[end]))
        if len(xs)<12:return None
        return ridge_prediction(xs,ys,availability_features(values,t,panel),100)
    center=point(at);residuals=[]
    if center is not None:
        for k in range(h,h+22):
            start=at-timedelta(days=k);end=start+timedelta(days=h);p=point(start)
            if p is not None and end in values and values[end]>0:residuals.append(transform(values[end])-p)
    if center is None or len(residuals)<5:
        ys=[transform(v) for d,v in values.items() if at-timedelta(days=56)<=d<=at and v>0]
        if not ys:raise ValueError("No matured training targets for price-free intercept fallback")
        qs=np.quantile(ys,[.1,.5,.9]);fallback="training_target_unconditional_quantiles"
    else:qs=center+np.quantile(residuals,[.1,.5,.9]);fallback=None
    if space=="log":qs=np.exp(np.clip(qs,-30,30))
    return np.maximum(qs,1e-6).tolist(),fallback
@app.function(image=image,cpu=4,memory=8192,timeout=1200,max_containers=4,volumes={"/data":volume})
def evaluate(source):
    import pandas as pd
    origin=source["origin"];validate_origin(origin);started=time.perf_counter()
    folder=Path("/data/campaign-v2/experiments")/source["run_id"]
    receipt=json.loads((folder/"summary.json").read_text())
    if receipt["origin"]!=origin or receipt["dataset_sha256"]!=PACK_SHA256:raise ValueError("Source artifact mismatch")
    temp,root=unpack();work=temp/"ablation";work.mkdir()
    history=pd.read_csv(folder/"history.csv");history["day"]=pd.to_datetime(history["date"]).dt.date
    if history["day"].max()>date.fromisoformat(origin):raise ValueError("Future features")
    catalog=pd.read_csv(folder/"primary.csv",keep_default_na=False)
    panels,_=auxiliary_panels(root,origin);values={sid:dict(zip(g["day"],g["value"])) for sid,g in history.groupby("series_id")}
    run=uuid.uuid4().hex;reports=[];private=Path("/data/campaign-v2/price-free")/run;private.mkdir(parents=True)
    for space in ("level","log"):
        rows=[];fallbacks=0
        for item in catalog.to_dict("records"):
            sid=item["series_id"];extra=panels.get(tuple(str(item[k]) for k in ("source_id","instrument_class","gpu_model","pricing_tier")),{})
            panel=extra.get("fixed_basket",{})
            for h in (1,3,7):
                qs,why=predict(values[sid],date.fromisoformat(origin),h,panel,space);fallbacks+=int(why is not None)
                rows.append(dict(zip(("series_id","origin_date","horizon_days","q10","q50","q90"),(sid,origin,h,*qs))))
        forecast=work/(space+".csv")
        with forecast.open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=("series_id","origin_date","horizon_days","q10","q50","q90"));writer.writeheader();writer.writerows(rows)
        cells=work/(space+"-cells.csv");score=work/(space+"-score.json")
        invoke(root,work,"score_"+space,["scorer.py","--forecast",str(forecast),"--truth",str(folder/"truth.csv"),"--history",str(folder/"history.csv"),"--frozen-cutoff",origin,"--catalog",str(folder/"primary.csv"),"--tier","headline","--out",str(score),"--per-cell",str(cells)])
        scored=json.loads(score.read_text())
        if scored["forecast_validation"]["n_problems"] or scored["cells"]["missing_forecast"]:raise ValueError("Invalid price-free forecast")
        cases=[]
        with cells.open() as f:
            for c in csv.DictReader(f):
                try:v=float(c["loss"]);b=float(c["baseline_loss"]);y=float(c["y"]);lo=float(c["q10"]);hi=float(c["q90"])
                except (ValueError,TypeError):continue
                if math.isfinite(v):cases.append({"series_id":c["series_id"],"horizon_days":int(c["horizon_days"]),"loss":v,"baseline_loss":b,"covered":lo<=y<=hi,"width":hi-lo})
        reports.append({"config_id":"no_price_predictors_"+space,"pinball":statistics.mean(c["loss"] for c in cases),"n_cells":len(cases),"fallbacks":fallbacks,"cases":cases,"comparison_with_price_history":next(m["pinball"] for m in receipt["methods"] if m["config_id"]=="coverage_"+space)})
        shutil.copyfile(forecast,private/forecast.name);shutil.copyfile(cells,private/cells.name)
    result={"schema_version":2,"origin":origin,"run_id":run,"source_run_id":source["run_id"],"methods":reports,"runtime_seconds":time.perf_counter()-started,"modal_call_id":modal.current_function_call_id(),"new_numerical_execution":True,"cache_hit":False}
    write(private/"summary.json",result);volume.commit();shutil.rmtree(temp);return result
@app.function(image=image,cpu=.25,memory=512,timeout=120,volumes={"/public":public})
def publish(result):
    public.reload();write(Path("/public/experimental-v2/price-free.json"),result);public.commit();return {"sha256":digest(result)}
@app.local_entrypoint()
def main(grid:str="inputs/grid.json"):
    source=json.loads(Path(grid).read_text())
    if source["code_sha"]!="a147797ec4557a337e2157ac60857d575e121630":raise ValueError("Wrong registered grid source")
    wanted=set(protocol()["training_origins"]+protocol()["development_origins"]+protocol()["evaluation_origins"])
    refs=[{"origin":r["origin"],"run_id":r["run_id"]} for r in source["origins"] if r["origin"] in wanted and r["status"]=="completed"]
    reports=list(evaluate.map(refs))
    result={"schema_version":2,"kind":"strict_price_predictor_ablation","code_sha":os.environ["GITHUB_SHA"],"dataset_sha256":PACK_SHA256,"created_at":now(),"origins":reports,"scope":"diagnostic outside the frozen 42-configuration policy pool; policy scores are not retuned","definition":"No target level, target returns, auxiliary index or price changes in predictors. Coverage and availability remain. Historical price labels still train the model and residual quantiles.","prior_coverage_ablation":"The 42-arm coverage configurations remove auxiliary price indices only; they retain target price history."}
    write(Path("artifacts/v2-price-free/results.json"),result);result["public_receipt"]=publish.remote(result);print("V2_PRICE_FREE:"+json.dumps({"origins":len(reports),"runtime_seconds":sum(r["runtime_seconds"] for r in reports),"public_receipt":result["public_receipt"]}))
