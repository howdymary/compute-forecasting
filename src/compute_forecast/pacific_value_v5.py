"""Pacific-target history, exact starter controls and licensed GPU capability context."""
from __future__ import annotations
import csv,hashlib,io,json,math,os,subprocess,tempfile,time,uuid
from datetime import datetime,timezone
from pathlib import Path
import modal
from .starter_probe import PACK_NAME,PACK_SHA256,verify_manifest
from .review_v4 import digest,encoded
from .pricing_contract import FORECAST_SHA
app=modal.App("compute-forecast-pacific-value-v5")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=(modal.Image.debian_slim(python_version="3.11").pip_install("duckdb==1.2.2","pandas==2.3.1","numpy==2.2.6","pyarrow>=16,<24").env({"GITHUB_SHA":os.environ.get("GITHUB_SHA","unknown")}).add_local_file("configs/pacific-value-v5.json","/root/configs/pacific-value-v5.json",copy=True).add_local_python_source("compute_forecast"))
def rows(path):
    with Path(path).open() as f:return list(csv.DictReader(f))
def write_csv(path,records,columns):
    with Path(path).open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore");w.writeheader();w.writerows(records)
def invoke(root,out,label,args):
    p=subprocess.run(["python","-I","-B",str(root/"starter"/args[0]),*map(str,args[1:])],capture_output=True,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1"),timeout=180)
    (out/(label+".stdout.txt")).write_text(p.stdout);(out/(label+".stderr.txt")).write_text(p.stderr)
    if p.returncode:raise RuntimeError(label+": "+p.stderr[-1600:])
def build_history(root,out,cutoff):
    hist=out/"history.csv";cat=out/"catalog.csv"
    invoke(root,out,"build",["build_series.py","--pack",root,"--cutoff",cutoff,"--out",hist,"--catalog",cat,"--report",out/"build.json"])
    h=rows(hist);c=rows(cat)
    if any(r["date"]>cutoff for r in h):raise ValueError("History crossed cutoff")
    return h,c,hist,cat
def baseline_audit(root,out,config,cohort):
    expected={(r["origin"],r["series_id"],int(r["horizon_days"])) for r in cohort}
    forecasts={m:[] for m in config["baseline_audit"]["methods"]}
    for origin in config["baseline_audit"]["origins"]:
        work=out/origin;work.mkdir();h,c,hist,cat=build_history(root,work,origin)
        ids=sorted({sid for o,sid,h in expected if o==origin})
        for method in forecasts:
            fc=work/(method+".csv")
            invoke(root,work,method,["baselines.py","--history",hist,"--origin",origin,"--method",method,"--series-ids",",".join(ids),"--horizons","1,3,7","--frozen","--out",fc])
            forecasts[method]+=[r for r in rows(fc) if (r["origin_date"],r["series_id"],int(r["horizon_days"])) in expected]
    # This is a retrospective scoring input through Nov6, not a forecast-generation history.
    full=out/"full";full.mkdir();_,_,history,catalog=build_history(root,full,"2026-11-06")
    reports=[];ids=sorted({sid for _,sid,_ in expected})
    for method,records in forecasts.items():
        fc=full/(method+".csv");columns=list(records[0]) if records else []
        write_csv(fc,records,columns)
        report=full/(method+"-report.json");cells=full/(method+"-cells.csv")
        invoke(root,full,"score-"+method,["scorer.py","--forecast",fc,"--truth",history,"--history",history,"--catalog",catalog,"--series-ids",",".join(ids),"--horizons","1,3,7","--no-missing-as-baseline","--out",report,"--per-cell",cells])
        raw=json.loads(report.read_bytes());cr=rows(cells)
        actual={(r["origin_date"],r["series_id"],int(r["horizon_days"])) for r in cr}
        if actual!=expected:raise ValueError("Official control cohort changed: "+method)
        reports.append({"method":method,"official_report":raw,"n_cells":len(cr),"cells":cr,"forecast_sha256":hashlib.sha256(fc.read_bytes()).hexdigest()})
    return {"classification":"Additional retrospective official-starter audit on exact previously opened 12-cell A100 cohort; no reselection","eligible_keys":[list(k) for k in sorted(expected)],"methods":reports,"official_drift":"Historical same-horizon log-change quantiles, multiplied into latest rate; q50 carries median change","independent_adapter_note":"The v4 prospective additive reference is separately defined and is not relabeled as the official drift baseline."}
@app.function(image=image,cpu=4,memory=8192,timeout=1200,max_containers=1,volumes={"/data":data})
def derive(forecast_bytes,cohort):
    start=time.perf_counter();config=json.loads(Path("/root/configs/pacific-value-v5.json").read_bytes());root=Path("/data/pacific")/PACK_NAME
    if verify_manifest(root)!=672:raise ValueError("Pack manifest")
    if hashlib.sha256(forecast_bytes).hexdigest()!=FORECAST_SHA:raise ValueError("Official export changed")
    temp=Path(tempfile.mkdtemp(prefix="pacific-v5-"));h,c,hist,cat=build_history(root,temp,"2026-11-06")
    export=list(csv.DictReader(io.StringIO(forecast_bytes.decode())));ids={r["series_id"] for r in export};headline={r["series_id"] for r in c if r["tier"]=="headline"}
    if ids!=headline or len(export)!=111:raise ValueError("Official submission/catalog scope differs")
    registry={r["source_id"]:r for r in rows(root/"sources_register.csv")}
    decisions=[];series=[]
    for m in c:
        if m["series_id"] not in ids:continue
        source=registry.get(m["source_id"],{})
        allowed=m.get("table")=="daily_statistics" and m["source_id"] in config["publication"]["allowed_sources"] and m["instrument_class"] not in config["publication"]["excluded_instruments"] and source.get("licence_id")=="CC-BY-4.0" and source.get("ship_status") in ("SHIP","SHIP-WITH-FILTER")
        reason="CC-BY-4.0 shipped filtered daily statistics, current official compilation grant and source-specific attribution verified" if allowed else "Marketplace asks or unsupported source/target: source-register owner-decision caveats retained; forecast still published unchanged"
        decisions.append({"series_id":m["series_id"],"approved":allowed,"reason":reason,"source_id":m["source_id"],"instrument_class":m["instrument_class"],"license":source.get("licence_id"),"source_url":source.get("source_url"),"attribution":source.get("attribution_string")})
        if not allowed:continue
        points=[{"date":r["date"],"value":float(r["value"])} for r in h if r["series_id"]==m["series_id"]]
        points.sort(key=lambda p:p["date"])
        if not points:continue
        series.append({"id":m["series_id"],"gpu_model":m["gpu_model"],"source_id":m["source_id"],"instrument_class":m["instrument_class"],"pricing_tier":m["pricing_tier"],"statistic":m["statistic"],"unit":"USD per GPU-hour","points":points,"points_sha256":digest(points),"source_url":source["source_url"],"attribution":source["attribution_string"],"license":"CC BY 4.0","license_url":"https://creativecommons.org/licenses/by/4.0/","catalog":m})
    pairs=[]
    for a in series:
        if a["gpu_model"]!="A100_SXM_80GB":continue
        for b in series:
            if b["gpu_model"]!="H100_SXM_80GB" or any(a[k]!=b[k] for k in ("source_id","instrument_class","pricing_tier")):continue
            av={p["date"]:p["value"] for p in a["points"]};bv={p["date"]:p["value"] for p in b["points"]};common=sorted(set(av)&set(bv))
            if not common:continue
            day=common[-1]
            pairs.append({"id":digest([a["id"],b["id"]])[:16],"a100_series_id":a["id"],"h100_series_id":b["id"],"date":day,"a100_rate":av[day],"h100_rate":bv[day],"rental_premium":bv[day]/av[day],"source_id":a["source_id"],"instrument_class":a["instrument_class"],"pricing_tier":a["pricing_tier"],"matched_dates":len(common),"limitation":"Same collector, instrument and tier; provider populations are not pair-matched"})
    units=[r for r in rows(root/"capability"/"capability_units_a100ref.csv") if r["gpu_generation"] in ("A100","H100")]
    ladder=[r for r in rows(root/"capability"/"capability_ladder_a100_link.csv") if "A100" in r["gen_from"] and "H100" in r["gen_to"]]
    hardware=[r for r in rows(root/"hardware_fundamentals"/"hardware_fundamentals.csv") if any(g in r["accelerator"].upper() for g in ("A100","H100"))]
    notices={}
    for path in sorted((root/"licences").glob("*")):
        if path.is_file() and path.suffix==".txt":
            text=path.read_text()
            if path.name=="CC-BY-4.0_legalcode.txt" or ("Apache License" in text and "Version 2.0" in text):notices[path.name]=text
    # Include exact source attribution and the hardware/capability copyright notices.
    notices["ATTRIBUTION.md"]=(root/"ATTRIBUTION.md").read_text()
    result={"schema_version":5,"study_id":config["study_id"],"created_at":datetime.now(timezone.utc).isoformat(),"source_sha":os.environ["GITHUB_SHA"],"config_sha256":digest(config),"pack_sha256":PACK_SHA256,"official_csv_sha256":FORECAST_SHA,"files":{"total":673,"manifest_entries":672,"unlisted":["MANIFEST.sha256"]},"history":{"origin":"2026-11-06","series":series,"publication_decisions":decisions,"official_catalog_sha256":hashlib.sha256(cat.read_bytes()).hexdigest(),"source_file_hashes":{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ("DATA.md","ATTRIBUTION.md","sources_register.csv","daily_statistics.csv")},"source_vintage":"Frozen Nov9 compilation, cutoff Nov6; date labels do not prove real-time historical accessibility"},"capability":{"units_a100_reference":units,"ladder_a100_h100":ladder,"rental_pairs":pairs,"hardware":hardware,"warning":"Derived MLPerf ladder ratios are not official or verified MLCommons scores; benchmark, precision, form factor and round must remain explicit"},"baseline_audit":baseline_audit(root,temp/"audit",config,cohort) if False else None,"economic_config":config["economic_model"],"resource_usage":{"new_optimizer_updates":0,"provider_cost_usd":None},"protected_outcomes_loaded":False}
    work=temp/"audit";work.mkdir();result["baseline_audit"]=baseline_audit(root,work,config,cohort)
    result["resource_usage"]["runtime_seconds"]=time.perf_counter()-start
    private=Path("/data/value-v5")/uuid.uuid4().hex;private.mkdir(parents=True);(private/"study.json").write_bytes(encoded(result));data.commit()
    if verify_manifest(root)!=672:raise ValueError("Pack changed")
    return {"study":result,"notices":notices}
@app.function(image=image,cpu=.25,memory=1024,timeout=120,max_containers=1,volumes={"/public":public})
def publish(study,notices):
    from .public_results import private_guard
    private_guard(study)
    if study["official_csv_sha256"]!=FORECAST_SHA or study["protected_outcomes_loaded"]:raise ValueError("Study publication boundary")
    root=Path("/public/value-v5");root.mkdir(exist_ok=True)
    raw=encoded(study);version=root/(digest(study)+".json")
    if not version.exists():version.write_bytes(raw)
    temp=root/"current.pending";temp.write_bytes(raw);temp.replace(root/"current.json")
    license_root=root/"notices";license_root.mkdir(exist_ok=True)
    for name,text in notices.items():
        if Path(name).name!=name:raise ValueError("Notice name")
        (license_root/name).write_text(text)
    public.commit();return {"study_sha256":hashlib.sha256(raw).hexdigest(),"published_series":len(study["history"]["series"]),"artifact":version.name}

@app.function(image=image,cpu=4,memory=8192,timeout=600,volumes={"/data":data})
def reproduce_and_notices():
    from .reproduce_pacific_v5 import reproduce
    root=Path("/data/pacific")/PACK_NAME
    out=Path(tempfile.mkdtemp(prefix="value-v5-reproduction-"))
    report=reproduce(root,out)
    notices={}
    for name in ("licences/afhubbard_DATA_LICENSE.txt","licences/gpurentalprices_github_LICENSE.txt","hardware_fundamentals/README_epoch_ml_hardware.md"):
        p=root/name
        if not p.is_file():raise ValueError("Required source notice missing: "+name)
        notices[p.name]=p.read_text()
    return {"report":report,"notices":notices}
@app.function(image=image,cpu=.25,memory=512,timeout=120,volumes={"/public":public})
def publish_reproduction(value):
    root=Path("/public/value-v5");root.mkdir(exist_ok=True)
    (root/"reproduction.json").write_bytes(encoded(value["report"]))
    notices=root/"notices";notices.mkdir(exist_ok=True)
    for name,text in value["notices"].items():(notices/name).write_text(text)
    public.commit();return {"status":"published","sha256":digest(value["report"])}
def main():
    with app.run():
        result=derive.remote(Path("results/frozen-v1/forecasts.csv").read_bytes(),json.loads(Path("results/review-v4/findings.json").read_bytes())["comparisons"][0]["cells"])
        receipt=publish.remote(result["study"],result["notices"])
    out=Path("artifacts/value-v5");out.mkdir(parents=True,exist_ok=True)
    (out/"study.json").write_bytes(encoded(result["study"]));(out/"publication.json").write_bytes(encoded(receipt))
    notices=out/"notices";notices.mkdir(exist_ok=True)
    for name,text in result["notices"].items():(notices/name).write_text(text)
    print("PACIFIC_V5_RESULT:"+json.dumps({"publication":receipt,"files":result["study"]["files"],"series":[{"id":s["id"],"points":len(s["points"])} for s in result["study"]["history"]["series"]],"baseline":result["study"]["baseline_audit"],"capability":result["study"]["capability"],"runtime":result["study"]["resource_usage"]}),flush=True)
if __name__=="__main__":main()
