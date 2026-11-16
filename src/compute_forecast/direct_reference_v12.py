"""Repair reference coverage without changing targets or trained predictions."""
import hashlib,json,os,tempfile,time
from pathlib import Path
import modal
from .direct_data_v12 import config,digest,image,data
from .starter_probe import PACK_NAME,verify_manifest
from .pacific_value_v5 import build_history,invoke,rows
app=modal.App("compute-forecast-direct-v12-references")
@app.function(image=image,cpu=4,memory=8192,timeout=900,volumes={"/data":data})
def repair(original,eligible,protocol_sha):
    p=config();assert protocol_sha==digest(p)
    root=Path("/data/pacific")/PACK_NAME;assert verify_manifest(root)==672
    source_sha=hashlib.sha256((root/"starter/baselines.py").read_bytes()).hexdigest()
    assert source_sha=="e5ed0b9f6342989a89a7e5c3a52a74654bd9eae49700ccdc82486b479e76e81c"
    ids=sorted({r["series_id"] for r in eligible});key=lambda r:(r["method"],r["series_id"],r["origin_date"],int(r["horizon_days"]))
    old={key(r):r for r in original};new=dict(old);added=[];discrepancies=[]
    for origin in sorted({r["origin"] for r in eligible}):
        out=Path(tempfile.mkdtemp(prefix="direct-v12-reference-"));hist,_,hp,_=build_history(root,out,origin)
        names=out/"series-ids.txt";names.write_text("\n".join(ids)+"\n")
        values={(r["series_id"],r["date"]):float(r["value"]) for r in hist}
        for method in p["evaluation"]["references"]:
            destination=out/(method+".csv")
            invoke(root,out,method,["baselines.py","--history",hp,"--origin",origin,"--series-ids","@"+str(names),"--method",method,"--frozen","--out",destination])
            emitted={}
            for r in rows(destination):
                if int(r["horizon_days"]) not in (1,3,7):continue
                r={**r,"method":method};emitted[key(r)]=r
                if key(r) in old:
                    if any(abs(float(old[key(r)][q])-float(r[q]))>1e-10 for q in ("q10","q50","q90")):discrepancies.append({"key":list(key(r)),"old":old[key(r)],"new":r})
                else:new[key(r)]=r;added.append({"key":list(key(r)),"reason":"Explicit fixed-series native export; no dynamic headline filter"})
            for task in eligible:
                if task["origin"]!=origin:continue
                for h in (1,3,7):
                    k=(method,task["series_id"],origin,h)
                    if k in new:continue
                    anchor=values[(task["series_id"],origin)]
                    r={"method":method,"series_id":task["series_id"],"origin_date":origin,"horizon_days":h,"q10":anchor,"q50":anchor,"q90":anchor,"reference_fallback":"Native starter omitted row; same last-value completion used by official scoring"}
                    new[k]=r;added.append({"key":list(k),"reason":r["reference_fallback"]})
    if discrepancies:raise ValueError("Reference formula discrepancy; correction must not silently replace original numerical values")
    for t in eligible:
        for h in (1,3,7):
            for method in p["evaluation"]["references"]:assert (method,t["series_id"],t["origin"],h) in new
    return {"study_id":"direct-v12-reference-coverage-repair","protocol_sha256":protocol_sha,"source_sha":os.environ.get("GITHUB_SHA"),"original_rows_sha256":digest(original),"native_baseline_source_sha256":source_sha,"existing_rows_unchanged":True,"original_rows":len(original),"corrected_rows":len(new),"additions":added,"rows":[new[k] for k in sorted(new)],"protected_outcomes_loaded":False,"classification":"Operational comparator-export correction; no model training, selection, target or cohort changes","provider_cost_usd":None}
@app.local_entrypoint()
def main(inputs:str="inputs/direct-v12"):
    source=Path(inputs);dataset=json.loads((source/"dataset.json").read_text());eligible=[{"series_id":t["series_id"],"origin":t["origin"]} for phase in ("development","retrospective") for t in dataset["groups"][phase]]
    result=repair.remote(dataset["baselines"],eligible,dataset["protocol_sha256"])
    out=Path("artifacts/direct-v12-reference");out.mkdir(parents=True,exist_ok=True);(out/"reference-repair.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ("rows","additions")},indent=2))
