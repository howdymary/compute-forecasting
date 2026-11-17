"""Matched small learner and unchanged official baselines on the new targets."""
import csv,hashlib,json,math,pathlib,pickle,subprocess,tempfile,time
import modal
from .probability_v18 import digest,summarize
from .market_state_v19 import shared_features,MARKET_FIELDS,SHARED_FIELDS
from .direct_forecast_v12 import cell_loss
app=modal.App("compute-forecast-market-v19-controls")
volume=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","scikit-learn==1.7.1").add_local_python_source("compute_forecast")
def vector(task,h,arm,impute=None):
    values=shared_features(task);values.update({k:task["market_state"].get(k) for k in MARKET_FIELDS})
    keys=list(SHARED_FIELDS)+(list(MARKET_FIELDS) if arm=="market" else [])
    row=[float(h),math.log(task["anchor"]),float(task["metadata"]["family"]=="H100")]
    for k in keys:row.extend([float(values[k]) if values[k] is not None else (impute or {}).get(k,0.),float(values[k] is None)])
    return row
@app.function(image=image,cpu=4,memory=8192,timeout=1800,max_containers=1,volumes={"/data":volume})
def execute(key):
    import duckdb,numpy as np,pandas as pd
    from sklearn.ensemble import GradientBoostingRegressor
    from .starter_probe import PACK_NAME,verify_manifest
    start=time.monotonic();base=pathlib.Path("/data/market-state-v19/inputs")/key
    data=json.loads((base/"dataset.json").read_bytes());audit=json.loads((base/"audit.json").read_bytes())
    assert digest(data)==audit["dataset_sha256"] and audit["training_ready"]
    root=pathlib.Path("/data/pacific")/PACK_NAME;verify_manifest(root)
    script=root/"starter/baselines.py";native_sha=hashlib.sha256(script.read_bytes()).hexdigest()
    assert native_sha=="e5ed0b9f6342989a89a7e5c3a52a74654bd9eae49700ccdc82486b479e76e81c"
    fields=["source_id","gpu_model","instrument_class","pricing_tier","provider","sku_raw","region_canonical","gpu_count","gpu_memory_gb"]
    c=duckdb.connect();f=c.execute("SELECT * FROM read_parquet(?,hive_partitioning=false) WHERE dt<=DATE '2026-11-06' AND source_id IN ('afhubbard','gpurentalprices','fastgpu_daily') AND quality_flag='ok' AND upper(licence_id)='CC-BY-4.0' AND instrument_class IN ('hyperscaler_spot','neocloud_rate_card') AND pricing_tier IN ('spot','on_demand') AND usd_per_gpu_hour>0 AND (gpu_model LIKE 'H100%' OR gpu_model LIKE 'A100%')",[str(root/"rental_observations"/"*"/"*"/"*.parquet")]).df()
    f["day"]=pd.to_datetime(f.dt).dt.strftime("%Y-%m-%d");f=f[f.day==pd.to_datetime(f.snapshot_ts_utc).dt.strftime("%Y-%m-%d")]
    from .market_data_v19 import clean
    history=[]
    for _,r in f.groupby(fields+["day"],dropna=False).agg(value=("usd_per_gpu_hour","median")).reset_index().iterrows():
        ident={k:clean(r[k]) for k in fields};sid="pack-market-v19-"+digest(ident)[:24]
        if sid in data["selected_groups"]:history.append({"series_id":sid,"date":r["day"],"value":float(r["value"])})
    results={phase:{} for phase in ("development","retrospective")};work=pathlib.Path(tempfile.mkdtemp())
    for phase in results:
        for origin in sorted({t["origin"] for t in data["groups"][phase]}):
            tasks=[t for t in data["groups"][phase] if t["origin"]==origin];directory=work/origin;directory.mkdir(exist_ok=True)
            path=directory/"history.csv";ids=directory/"ids.txt";ids.write_text("\n".join(t["series_id"] for t in tasks))
            with path.open("w") as file:
                w=csv.DictWriter(file,fieldnames=["series_id","date","value"]);w.writeheader();w.writerows(r for r in history if r["date"]<=origin)
            for method in ("last_value","last_value_empirical","drift","seasonal_naive"):
                out=directory/(method+".csv")
                subprocess.run(["python","-I","-B",str(script),"--history",str(path),"--origin",origin,"--series-ids","@"+str(ids),"--method",method,"--out",str(out)],check=True,capture_output=True,timeout=90)
                forecasts={(r["series_id"],int(r["horizon_days"])):r for r in csv.DictReader(out.open())}
                cells=results[phase].setdefault(method,[])
                for t in tasks:
                    for h,y in zip((1,3,7),t["outcomes"]):
                        r=forecasts.get((t["series_id"],h));q=[float(r[k]) for k in ("q10","q50","q90")] if r else [t["anchor"]]*3
                        cells.append(cell(t,h,y,q,method,fallback=r is None))
    train=[(t,h,y) for t in data["groups"]["training"] for h,y in zip((1,3,7),t["outcomes"])]
    state={"dataset_sha256":digest(data),"models":{}}
    for arm in ("price","market"):
        x=np.array([vector(t,h,arm) for t,h,y in train]);y=np.array([math.log(y/t["anchor"]) for t,h,y in train])
        models=[GradientBoostingRegressor(loss="quantile",alpha=tau,n_estimators=50,max_depth=2,learning_rate=.05,random_state=17,min_samples_leaf=8).fit(x,y) for tau in (.1,.5,.9)]
        state["models"][arm]=models
        for phase in results:
            cells=[]
            for t in data["groups"][phase]:
                for h,y in zip((1,3,7),t["outcomes"]):
                    raw=[t["anchor"]*math.exp(float(m.predict([vector(t,h,arm)])[0])) for m in models];q=sorted(raw)
                    cells.append({**cell(t,h,y,q,"numerical_"+arm),"crossing_corrected":raw!=q})
            results[phase]["numerical_"+arm]=cells
    private=pathlib.Path("/data/market-state-v19/numerical")/key;private.mkdir(parents=True,exist_ok=True)
    raw=pickle.dumps(state);(private/"state.pkl").write_bytes(raw);volume.commit()
    return {"study_id":"market-state-v19","dataset_sha256":digest(data),"native_baseline_sha256":native_sha,"numerical_state_sha256":hashlib.sha256(raw).hexdigest(),"results":{phase:{name:{"cells":rows,"summary":summarize(rows)} for name,rows in methods.items()} for phase,methods in results.items()},"runtime_seconds":time.monotonic()-start,"provider_cost_usd":None,"new_optimizer_updates":0,"history_scope":"All available past source-defined group observations, no network; labels outside origin excluded","imputation":"Fixed zero plus missingness indicator; training-only numerical fit","state_format":"Private pickle; only load hash-verified state created by this module"}
def cell(t,h,y,q,method,fallback=False):
    assert 0<q[0]<=q[1]<=q[2]
    return {"task_id":t["task_id"],"series_id":t["series_id"],"origin":t["origin"],"horizon_days":h,"target_date":t["target_dates"][(1,3,7).index(h)],"outcome":y,"anchor":t["anchor"],"method":method,"q10":q[0],"q50":q[1],"q90":q[2],"loss":cell_loss(y,q),"fallback":fallback,"changed_price":y!=t["anchor"]}
@app.local_entrypoint()
def main():
    pointer=json.loads(pathlib.Path("inputs/market-state-v19/input-key.json").read_bytes());value=execute.remote(pointer["private_key"])
    out=pathlib.Path("artifacts/market-state-v19-controls");out.mkdir(parents=True,exist_ok=True);(out/"controls.json").write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps({phase:{k:v["summary"]["primary_pinball"] for k,v in groups.items()} for phase,groups in value["results"].items()}))
