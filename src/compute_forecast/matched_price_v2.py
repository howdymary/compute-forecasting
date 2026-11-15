"""Matched diagnostic: identical target, calibration and missingness; mask price values only."""
from __future__ import annotations
import csv,json,math,os,shutil,statistics,time,uuid
from datetime import date,timedelta
from pathlib import Path
import modal
from .campaign_v2 import image,unpack,invoke,validate_origin,now,write,digest,protocol
from .representation_study import auxiliary_panels,features_at
from .starter_probe import volume,PACK_SHA256
app=modal.App("compute-forecast-v2-matched-price-ablation")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
def predictors(values,at,panel,space):
    availability=[float(at-timedelta(days=k) in values) for k in (0,1,3,7)]+[sum(at-timedelta(days=k) in values for k in range(28))/28]+[float(panel.get(at,{}).get(k,float("nan"))) for k in ("coverage","log_configs","provider_hhi")]
    target=features_at(values,at,space)
    prices=target[:5] if target is not None else [float("nan")]*5
    auxiliary=[float(panel.get(at,{}).get(k,float("nan"))) for k in ("log_index","change_1","change_3","change_7")]
    return availability+prices+auxiliary
def ridge_with_price_mask(matrix,targets,query,remove_prices):
    import numpy as np
    x=np.asarray(matrix,dtype=float);q=np.asarray(query,dtype=float);y=np.asarray(targets,dtype=float)
    observed=np.isfinite(x);q_observed=np.isfinite(q)
    means=np.divide(np.where(observed,x,0).sum(axis=0),observed.sum(axis=0),out=np.zeros(x.shape[1]),where=observed.sum(axis=0)>0)
    clean=np.where(observed,x,means);query_clean=np.where(q_observed,q,means)
    if remove_prices:clean[:,8:]=0;query_clean[8:]=0
    # The ORIGINAL missingness indicators remain identical under both conditions.
    clean=np.concatenate((clean,(~observed).astype(float)),axis=1)
    query_clean=np.concatenate((query_clean,(~q_observed).astype(float)))
    center=clean.mean(axis=0);scale=clean.std(axis=0);scale=np.where(scale>1e-12,scale,1)
    clean=(clean-center)/scale;query_clean=(query_clean-center)/scale
    mean=y.mean();coeff=np.linalg.solve(clean.T@clean+100*np.eye(clean.shape[1]),clean.T@(y-mean))
    return float(mean+query_clean@coeff)
def predict(values,at,h,panel,space,remove_prices):
    import numpy as np
    transform=math.log if space=="log" else float
    def point(t):
        xs=[];ys=[]
        for k in range(h,57):
            start=t-timedelta(days=k);end=start+timedelta(days=h)
            if end in values and values[end]>0:
                xs.append(predictors(values,start,panel,space));ys.append(transform(values[end]))
        if len(xs)<12:return None
        return ridge_with_price_mask(xs,ys,predictors(values,t,panel,space),remove_prices)
    center=point(at);residuals=[]
    if center is not None:
        for k in range(h,h+22):
            start=at-timedelta(days=k);end=start+timedelta(days=h);p=point(start)
            if p is not None and end in values and values[end]>0:residuals.append(transform(values[end])-p)
    if center is None or len(residuals)<5:
        ys=[transform(v) for d,v in values.items() if at-timedelta(days=56)<=d<=at and v>0]
        if not ys:raise ValueError("No matured training targets")
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
    run=uuid.uuid4().hex;reports=[];private=Path("/data/campaign-v2/matched-price-ablation")/run;private.mkdir(parents=True)
    for space,remove_prices in __import__("itertools").product(("level","log"),(False,True)):
        variant=("prices_removed_" if remove_prices else "prices_present_")+space
        rows=[];fallbacks=0
        for item in catalog.to_dict("records"):
            sid=item["series_id"];extra=panels.get(tuple(str(item[k]) for k in ("source_id","instrument_class","gpu_model","pricing_tier")),{})
            panel=extra.get("fixed_basket",{})
            for h in (1,3,7):
                qs,why=predict(values[sid],date.fromisoformat(origin),h,panel,space,remove_prices);fallbacks+=int(why is not None)
                rows.append(dict(zip(("series_id","origin_date","horizon_days","q10","q50","q90"),(sid,origin,h,*qs))))
        forecast=work/(variant+".csv")
        with forecast.open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=("series_id","origin_date","horizon_days","q10","q50","q90"));writer.writeheader();writer.writerows(rows)
        cells=work/(variant+"-cells.csv");score=work/(variant+"-score.json")
        invoke(root,work,"score_"+variant,["scorer.py","--forecast",str(forecast),"--truth",str(folder/"truth.csv"),"--history",str(folder/"history.csv"),"--frozen-cutoff",origin,"--catalog",str(folder/"primary.csv"),"--tier","headline","--out",str(score),"--per-cell",str(cells)])
        scored=json.loads(score.read_text())
        if scored["forecast_validation"]["n_problems"] or scored["cells"]["missing_forecast"]:raise ValueError("Invalid price-free forecast")
        cases=[]
        with cells.open() as f:
            for c in csv.DictReader(f):
                try:v=float(c["loss"]);b=float(c["baseline_loss"]);y=float(c["y"]);lo=float(c["q10"]);hi=float(c["q90"])
                except (ValueError,TypeError):continue
                if math.isfinite(v):cases.append({"series_id":c["series_id"],"horizon_days":int(c["horizon_days"]),"loss":v,"baseline_loss":b,"covered":lo<=y<=hi,"width":hi-lo})
        reports.append({"config_id":variant,"space":space,"price_values_removed":remove_prices,"pinball":statistics.mean(c["loss"] for c in cases),"n_cells":len(cases),"fallbacks":fallbacks,"cases":cases,"comparison_with_price_history":next(m["pinball"] for m in receipt["methods"] if m["config_id"]=="coverage_"+space)})
        shutil.copyfile(forecast,private/forecast.name);shutil.copyfile(cells,private/cells.name)
    result={"schema_version":2,"origin":origin,"run_id":run,"source_run_id":source["run_id"],"methods":reports,"runtime_seconds":time.perf_counter()-started,"modal_call_id":modal.current_function_call_id(),"new_numerical_execution":True,"cache_hit":False}
    write(private/"summary.json",result);volume.commit();shutil.rmtree(temp);return result
@app.function(image=image,cpu=.25,memory=512,timeout=120,volumes={"/public":public})
def publish(result):
    public.reload();write(Path("/public/experimental-v2/matched-price-ablation.json"),result);public.commit();return {"sha256":digest(result)}
@app.local_entrypoint()
def main(grid:str="inputs/grid.json"):
    source=json.loads(Path(grid).read_text())
    if source["code_sha"]!="a147797ec4557a337e2157ac60857d575e121630":raise ValueError("Wrong registered grid source")
    wanted=set(protocol()["training_origins"]+protocol()["development_origins"]+protocol()["evaluation_origins"])
    refs=[{"origin":r["origin"],"run_id":r["run_id"]} for r in source["origins"] if r["origin"] in wanted and r["status"]=="completed"]
    reports=list(evaluate.map(refs))
    result={"schema_version":2,"kind":"matched_price_value_ablation","code_sha":os.environ["GITHUB_SHA"],"dataset_sha256":PACK_SHA256,"created_at":now(),"origins":reports,"scope":"Post-hoc diagnostic outside the frozen 42-configuration policy pool; policy selection and official export unchanged","definition":"Both conditions fit absolute level/log targets with identical 56-day windows, Ridge alpha100, train-only mean imputation, original missingness indicators and prequential calibration. The removed condition masks nine price-value predictors after imputation; coverage, availability and every original missingness flag remain identical. Price labels necessarily remain training outcomes.","prior_coverage_ablation":"The earlier strict price-free diagnostic also changed the target/anchor formulation. It remains available as an unmatched diagnostic; this paired design addresses that limitation."}
    write(Path("artifacts/v2-matched-price/results.json"),result);result["public_receipt"]=publish.remote(result);print("V2_MATCHED_PRICE:"+json.dumps({"origins":len(reports),"runtime_seconds":sum(r["runtime_seconds"] for r in reports),"public_receipt":result["public_receipt"]}))
