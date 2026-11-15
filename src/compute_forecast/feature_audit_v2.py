"""Count actual feature-availability masks without refitting or changing scores."""
from __future__ import annotations
import json,os,shutil,time
from datetime import date,timedelta
from pathlib import Path
import modal
from .campaign_v2 import image,unpack,write,now,validate_origin
from .representation_study import auxiliary_panels,features_at
from .starter_probe import volume,PACK_SHA256
app=modal.App("compute-forecast-v2-feature-audit")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
def missing_counts(matrix,query,auxiliary):
    import numpy as np
    x=np.asarray(matrix,dtype=float);q=np.asarray(query,dtype=float)
    if not len(x):return {"rows":0,"missing_training_cells":0,"missing_auxiliary_training_cells":0,"missing_query_cells":int((~np.isfinite(q)).sum())}
    return {"rows":len(x),"missing_training_cells":int((~np.isfinite(x)).sum()),"missing_auxiliary_training_cells":int((~np.isfinite(x[:,6:])).sum()) if auxiliary else 0,"missing_query_cells":int((~np.isfinite(q)).sum()),"entirely_missing_columns":int((~np.isfinite(x)).all(axis=0).sum())}
@app.function(image=image,cpu=4,memory=8192,timeout=900,max_containers=6,volumes={"/data":volume})
def audit(source):
    import pandas as pd
    origin=source["origin"];validate_origin(origin);started=time.perf_counter();folder=Path("/data/campaign-v2/experiments")/source["run_id"]
    report=json.loads((folder/"summary.json").read_text())
    if report["origin"]!=origin or report["dataset_sha256"]!=PACK_SHA256:raise ValueError("Numerical source mismatch")
    temp,root=unpack();hist=pd.read_csv(folder/"history.csv");hist["day"]=pd.to_datetime(hist["date"]).dt.date
    cat=pd.read_csv(folder/"primary.csv",keep_default_na=False);values={sid:dict(zip(g["day"],g["value"])) for sid,g in hist.groupby("series_id")}
    panels,baskets=auxiliary_panels(root,origin);rows=[]
    for item in cat.to_dict("records"):
        sid=item["series_id"];series=values[sid];extras=panels.get(tuple(str(item[k]) for k in ("source_id","instrument_class","gpu_model","pricing_tier")),{})
        for space in ("level","log"):
            for aux in ("target_only","raw","fixed_basket"):
                for days in (28,56):
                    for h in (1,3,7):
                        panel=extras.get(aux) if aux!="target_only" else None
                        row={"series_id":sid,"space":space,"aux":aux,"lookback_days":days,"horizon_days":h,"alphas":[1,100],"fit_masks":[]}
                        if aux!="target_only" and not panel:row["fallback"]="unsupported_auxiliary_contract";rows.append(row);continue
                        for lag in [0,*range(h,22)]:
                            at=date.fromisoformat(origin)-timedelta(days=lag);query=features_at(series,at,space,panel)
                            if query is None:
                                if lag==0:break
                                continue
                            end=at+timedelta(days=h)
                            if lag and (end not in series or series[end]<=0):continue
                            matrix=[]
                            for k in range(h,days+1):
                                start=at-timedelta(days=k);end=start+timedelta(days=h)
                                vector=features_at(series,start,space,panel)
                                if vector is not None and end in series and series[end]>0:matrix.append(vector)
                            mask=missing_counts(matrix,query,aux!="target_only")
                            mask.update(as_of=at.isoformat(),fit_role="primary" if lag==0 else "prequential_calibration",used=mask["rows"]>=12,last_permitted_label=at.isoformat())
                            row["fit_masks"].append(mask)
                            if lag==0 and mask["rows"]<12:break
                        rows.append(row)
    result={"origin":origin,"source_run_id":source["run_id"],"rows":rows,"basket_audit":baskets,"runtime_seconds":time.perf_counter()-started,"modal_call_id":modal.current_function_call_id(),"imputation":"Used fits employ the frozen train-only mean and missingness-indicator algorithm; alpha does not alter masks","scope":"Original 24 Ridge representations; auxiliary-price and strict price-free diagnostics remain separate","numerical_scores_changed":False}
    write(Path("/data/campaign-v2/feature-audit")/(source["run_id"]+".json"),result);volume.commit();shutil.rmtree(temp);return result
@app.function(image=image,cpu=.25,memory=512,timeout=120,volumes={"/public":public})
def publish(result):
    public.reload();write(Path("/public/experimental-v2/feature-audit.json"),result);public.commit()
@app.local_entrypoint()
def main(grid:str="inputs/grid.json"):
    source=json.loads(Path(grid).read_text())
    if source["code_sha"]!="a147797ec4557a337e2157ac60857d575e121630":raise ValueError("Wrong frozen grid")
    refs=[{"origin":r["origin"],"run_id":r["run_id"]} for r in source["origins"] if r["status"]=="completed"]
    results=list(audit.map(refs));summary={"schema_version":2,"code_sha":os.environ["GITHUB_SHA"],"created_at":now(),"dataset_sha256":PACK_SHA256,"origins":results}
    write(Path("artifacts/v2-feature-audit/results.json"),summary);publish.remote(summary)
    print("V2_FEATURE_AUDIT:"+json.dumps({"origins":len(results),"fit_mask_records":sum(len(row["fit_masks"]) for r in results for row in r["rows"]),"runtime_seconds":sum(r["runtime_seconds"] for r in results),"numerical_scores_changed":False}),flush=True)
