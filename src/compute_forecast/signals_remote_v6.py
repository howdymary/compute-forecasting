"""Bounded daily point-in-time capture and weekly prospective execution on Modal."""
from __future__ import annotations
import csv,hashlib,io,json,os,re,subprocess,tempfile,time,urllib.request,uuid
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import modal
from .review_v4 import digest,encoded
from .signals_v6 import config,utc,retain,normalize_prices,feature_vector,readiness,issue,evaluate,row_for,paired,asof_snapshots
from .starter_probe import PACK_NAME
app=modal.App("compute-forecast-signals-v6")
data=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
secret=modal.Secret.from_name("compute-forecast-signals-v6",required_keys=["EXA_API_KEY","PAST_API_KEY"])
image=(modal.Image.debian_slim(python_version="3.11").pip_install("numpy==2.2.6","pandas==2.3.1","scikit-learn==1.7.1","duckdb==1.2.2","pyarrow>=16,<24").env({"GITHUB_SHA":os.environ.get("GITHUB_SHA","unknown")}).add_local_file("configs/prospective-signals-v6.json","/root/configs/prospective-signals-v6.json",copy=True).add_local_python_source("compute_forecast"))
def now():return datetime.now(timezone.utc).isoformat()
def fetch(url,private,body=None,key=None,limit=2_000_000):
    headers={"User-Agent":"ComputeForecastResearch/1.0"}
    if body is not None:headers["Content-Type"]="application/json"
    if key:headers["x-api-key"]=key
    req=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers=headers)
    with urllib.request.urlopen(req,timeout=45) as r:
        raw=r.read(limit+1);at=now()
        if len(raw)>limit:raise ValueError("Source byte budget exceeded")
        receipt={"url":url,"retrieved_at":at,"status_code":r.status,"final_url":r.geturl(),"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"etag":r.headers.get("ETag"),"last_modified":r.headers.get("Last-Modified")}
    path=private/(receipt["sha256"]+".raw")
    if not path.exists():path.write_bytes(raw)
    return raw,receipt
def load_records(root,kind):
    return [json.loads(p.read_bytes()) for p in sorted((root/kind).glob("*.json"))] if (root/kind).exists() else []
def native_references(snapshots,origin):
    p=config();past=[s for s in snapshots if s["prices"]["date"]<=origin];targets=past[-1]["prices"]["cohort"] if past else []
    rows=[];seen=set()
    for s in sorted(past,key=lambda s:s["captured_at"]):
        for r in s["prices"]["rows"]:
            key=(r["id"],r["date"])
            if key in seen:continue
            rows.append({"series_id":r["id"],"date":r["date"],"value":r["value"]});seen.add(key)
    root=Path("/data/pacific")/PACK_NAME;script=root/"starter/baselines.py"
    expected="e5ed0b9f6342989a89a7e5c3a52a74654bd9eae49700ccdc82486b479e76e81c"
    if hashlib.sha256(script.read_bytes()).hexdigest()!=expected:raise ValueError("Official baseline source changed")
    temp=Path(tempfile.mkdtemp(prefix="signals-v6-baselines-"));history=temp/"history.csv";ids=temp/"ids.txt";ids.write_text("\n".join(t["id"] for t in targets))
    with history.open("w",newline="") as out:
        w=csv.DictWriter(out,fieldnames=["series_id","date","value"]);w.writeheader();w.writerows(rows)
    result=[]
    for method in p["references"]:
        output=temp/(method+".csv")
        process=subprocess.run(["python","-I","-B",str(script),"--history",str(history),"--origin",origin,"--series-ids","@"+str(ids),"--method",method,"--out",str(output)],capture_output=True,text=True,timeout=90)
        if process.returncode:raise RuntimeError("Native baseline failed: "+process.stderr[-1000:])
        for r in csv.DictReader(output.open()):
            h=int(r["horizon_days"])
            if h not in p["horizons"]:continue
            family=next(t["family"] for t in targets if t["id"]==r["series_id"])
            result.append({"series_id":r["series_id"],"family":family,"origin_date":origin,"horizon_days":h,"target_date":(date.fromisoformat(origin)+timedelta(days=h)).isoformat(),"forecaster":method,"q10":float(r["q10"]),"q50":float(r["q50"]),"q90":float(r["q90"]),"native_method_note":r.get("method_note"),"baseline_source_sha256":expected})
    return result
def capture(root,previous):
    p=config();private=root/"private";private.mkdir(parents=True,exist_ok=True);receipts=[];errors=[]
    raw,receipt=fetch(p["price_source"]["url"],private);receipts.append(receipt);payload=json.loads(raw)
    health_raw,health_receipt=fetch(p["price_source"]["health_url"],private);receipts.append(health_receipt)
    if payload["date"]!=json.loads(health_raw).get("snapshot_date"):raise ValueError("Quote and health vintages differ")
    cohort_file=root/"cohort.json";frozen=json.loads(cohort_file.read_bytes()) if cohort_file.exists() else None
    prices=normalize_prices(payload,json.loads(health_raw),now(),frozen)
    if not cohort_file.exists():
        if not prices["cohort"]:raise ValueError("No verifiable exact-configuration A100/H100 on-demand offers")
        with cohort_file.open("xb") as out:out.write(encoded(prices["cohort"]))
    events={e["id"]+":"+e["content_sha256"]:e for s in previous for e in s.get("events",[])}
    query="Official GPU cloud price announcements, hardware launches and infrastructure capacity deployments from NVIDIA, AWS, Google Cloud, CoreWeave and Lambda. Identify exact announcement dates and distinguish plans from operating capacity."
    try:
        body={"query":query,"type":"auto","numResults":p["signals"]["max_results"],"includeDomains":p["signals"]["primary_domains"],"startPublishedDate":(datetime.now(timezone.utc)-timedelta(days=30)).isoformat(),"endPublishedDate":now(),"contents":{"highlights":True}}
        discovery_raw,r=fetch("https://api.exa.ai/search",private,body,os.environ["EXA_API_KEY"]);receipts.append(r);discovery=json.loads(discovery_raw)
        receipts[-1].update(request_id=discovery.get("requestId"),cost_dollars=discovery.get("costDollars"),query=query)
        for item in discovery.get("results",[])[:p["signals"]["max_results"]]:
            url=item.get("url","")
            from urllib.parse import urlparse
            if not any(urlparse(url).hostname==d or (urlparse(url).hostname or "").endswith("."+d) for d in p["signals"]["primary_domains"]):continue
            try:
                html,r=fetch(url,private,limit=2_000_000);receipts.append(r);text=html.decode(errors="replace")
                pattern=r'(?:datePublished["\s:]+|property=["\x27]article:published_time["\x27][^>]*content=["\x27])(\d{4}-\d{2}-\d{2}(?:T[^"\x27<\s]+)?)'
                matches=re.findall(pattern,text,re.I);published=matches[0] if matches else None
                if published and len(published)==10:published+="T23:59:59.999999+00:00"
                if published:
                    try:utc(published)
                    except ValueError:published=None
                title=item.get("title","");lower=title.lower()
                kind="price_announcement" if any(v in lower for v in ("price","pricing","rate cut")) else "capacity_plan" if any(v in lower for v in ("capacity","infrastructure","data center","datacenter","deployment","expan")) else "hardware_announcement" if any(v in lower for v in ("blackwell","rubin","h200","b200","gpu","launch")) else "announcement"
                identifier=digest(url)[:24];key=identifier+":"+r["sha256"]
                events.setdefault(key,{"id":identifier,"url":url,"title":title,"published_at":published,"publication_verified":published is not None,"first_observed_at":r["retrieved_at"],"retrieved_at":r["retrieved_at"],"content_sha256":r["sha256"],"kind":kind,"extraction_version":"deterministic-title-classifier-v1","uncertainty":"Title-based announcement category; no verified operating-capacity amount or causal price coefficient","publication":"Metadata and derived counts only; source body private"})
            except Exception as e:errors.append({"source_url":url,"error_type":type(e).__name__,"scope":"news extraction"})
    except Exception as e:errors.append({"source_url":"https://api.exa.ai/search","error_type":type(e).__name__,"scope":"news discovery"})
    bls=None
    try:
        raw,r=fetch(p["signals"]["bls_url"],private);receipts.append(r);b=json.loads(raw)
        if b.get("status")!="REQUEST_SUCCEEDED":raise ValueError("BLS request refused")
        series=next(s for s in b["Results"]["series"] if s["seriesID"]==p["signals"]["bls_series"])
        observations=[{"period":row["year"]+"-"+row["period"][1:],"value":float(row["value"]),"footnotes":row.get("footnotes",[])} for row in series["data"] if re.fullmatch("M(0[1-9]|1[0-2])",row["period"])]
        observations.sort(key=lambda x:x["period"],reverse=True)
        if not observations:raise ValueError("BLS no monthly observations")
        period=observations[0]["period"];first=min([s["bls"]["period_first_observed_at"] for s in previous if (s.get("bls") or {}).get("latest_period")==period]+[r["retrieved_at"]])
        bls={"series_id":p["signals"]["bls_series"],"unit":"Producer price index; not USD/kWh","latest_period":period,"observations":observations[:2],"first_observed_at":r["retrieved_at"],"period_first_observed_at":first,"source_url":p["signals"]["bls_url"],"response_sha256":r["sha256"],"release_timestamp":None,"availability_rule":"Actual retrieval; no claimed historical release vintage"}
    except Exception as e:errors.append({"source_url":p["signals"]["bls_url"],"error_type":type(e).__name__,"scope":"BLS"})
    at=now();event_rows=list(events.values());features=feature_vector(event_rows,bls,at)
    return {"schema_version":6,"study_id":p["study_id"],"captured_at":at,"source_sha":os.environ.get("GITHUB_SHA"),"protocol_sha256":digest(p),"prices":prices,"events":event_rows,"bls":bls,"features":features,"receipts":receipts,"errors":errors,"protected_outcomes_loaded":False}
def publication(root,snapshots,commitments,scores):
    p=config();destination=Path("/public/signals-v6");destination.mkdir(parents=True,exist_ok=True);artifacts=destination/"artifacts";artifacts.mkdir(exist_ok=True)
    manifests=[]
    for kind,records in (("snapshot",snapshots),("commitment",commitments),("score",scores)):
        for record in records:
            identity=digest(record);path=artifacts/(identity+".json")
            if not path.exists():
                with path.open("xb") as out:out.write(encoded(record))
            manifests.append({"kind":kind,"sha256":identity,"bytes_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"path":"/api/signals-v6/artifacts/"+identity+".json"})
    current=max(snapshots,key=lambda s:s["captured_at"]) if snapshots else None
    cells=[c for score in scores for c in score["cells"]]
    contrasts=[paired(cells,"signals_111","signals_000"),paired(cells,"signals_111","drift")]
    ledger=[]
    for record in commitments:
        score=next((s for s in scores if s["commitment_sha256"]==digest(record)),None)
        ledger.append({"id":digest(record),"origin_date":record["origin_date"],"issued_at":record["issued_at"],"kind":record["kind"],"hypothesis":p["hypothesis"],"candidate":"signals_111","incumbent":"signals_000","status":record["status"],"rows":len(record["rows"]),"failures":len(record["failures"]),"target_dates":sorted({r["target_date"] for r in record["rows"]}),"score_status":score["status"] if score else "pending","decision":"incumbent_retained_pending_confirmatory_evidence","criticism":"Cold-start references are not evidence of signal value; await retained feature history and matured labels","artifact":"/api/signals-v6/artifacts/"+digest(record)+".json"})
    index={"schema_version":6,"study_id":p["study_id"],"updated_at":now(),"source_sha":os.environ.get("GITHUB_SHA"),"protocol":p,"protocol_sha256":digest(p),"registration":json.loads((root/"registration.json").read_bytes()),"latest_snapshot":current,"snapshot_count":len(snapshots),"cohort":current["prices"]["cohort"] if current else [],"readiness":readiness(snapshots),"ledger":ledger,"comparisons":contrasts,"primary_scored_cells":len([c for c in cells if c["cohort"]=="primary"]),"prospective_improvement_established":False,"claim":"The experiment is running; prospective improvement is not yet established.","artifacts":manifests,"schedule":{"status":"deployed_single_serial_tick","cron_utc":"30 17,18 * * *","external_work_ends":p["schedule_end"],"note":"After end date, scheduled invocations perform no collection/inference; removing the deployed schedule is a separate operator action."},"execution_failures":load_records(root,"failures")[-20:],"training":{"new_optimizer_updates":0,"status":"gated_pending_informative_tasks_and_checked_labels"}}
    from .public_results import private_guard
    private_guard(index)
    temp=destination/"index.pending";temp.write_bytes(encoded(index));temp.replace(destination/"index.json");public.commit();return index
@app.function(image=image,cpu=2,memory=4096,timeout=900,max_containers=1,schedule=modal.Cron("30 17,18 * * *"),secrets=[secret],volumes={"/data":data,"/public":public})
def tick(mode="auto"):
    begin=time.perf_counter();p=config()
    if datetime.now(timezone.utc)>=utc(p["schedule_end"]):return {"status":"scheduled_external_work_completed","external_requests":0}
    root=Path("/data/signals-v6");root.mkdir(parents=True,exist_ok=True);registration=root/"registration.json";engine_sha=hashlib.sha256(Path(__file__).with_name("signals_v6.py").read_bytes()).hexdigest()
    if registration.exists():
        reg=json.loads(registration.read_bytes())
        if reg["protocol_sha256"]!=digest(p) or reg["engine_sha256"]!=engine_sha:raise ValueError("Registered engine/protocol changed; create a successor study")
    else:
        reg={"registered_at":now(),"protocol_sha256":digest(p),"engine_sha256":engine_sha,"source_sha":os.environ.get("GITHUB_SHA"),"registration_commit":"https://github.com/howdymary/compute-forecasting/commit/"+os.environ.get("GITHUB_SHA","unknown")}
        with registration.open("xb") as out:out.write(encoded(reg))
    snapshots=load_records(root,"snapshots");day=datetime.now(timezone.utc).date().isoformat();errors=[]
    if len(snapshots)>=p["resources"]["max_snapshots"]:raise ValueError("Snapshot budget exhausted")
    today=[s for s in snapshots if s["prices"]["date"]==day]
    if not today and (mode=="initialize" or datetime.now(timezone.utc).hour==17):
        try:
            snapshot=capture(root,snapshots);retain(root,"snapshots",snapshot);snapshots.append(snapshot)
        except Exception as e:
            failure={"at":now(),"phase":"capture","error_type":type(e).__name__,"detail":str(e)[:500]};retain(root,"failures",failure);errors.append(failure)
    commitments=load_records(root,"commitments")
    if snapshots:
        initial=not any(r["kind"]=="cold_start_reference_pilot" for r in commitments)
        pilot=mode=="initialize" and initial
        primary=day in p["origins"] and utc(day+"T18:00:00+00:00")<=datetime.now(timezone.utc)<=utc(day+"T20:00:00+00:00")
        if pilot or primary:
            key=("pilot-" if pilot else "primary-")+day
            if not (root/"commitments"/(key+".json")).exists():
                try:
                    cutoff=now() if pilot else day+"T18:00:00+00:00"
                    references=native_references(asof_snapshots(snapshots,cutoff),day);record=issue(snapshots,day,now(),references,pilot=pilot)
                    record["runtime_seconds"]=time.perf_counter()-begin;retain(root,"commitments",record,key);commitments.append(record)
                except Exception as e:
                    failure={"at":now(),"phase":"issuance","error_type":type(e).__name__,"detail":str(e)[:1000]};retain(root,"failures",failure);errors.append(failure)
    # Re-evaluation adds a new immutable score vintage. Never rewrite an earlier report.
    scores=[]
    for record in commitments:
        score=evaluate(record,snapshots,now(),digest(record));retain(root,"evaluations",score);scores.append(score)
    data.commit();index=publication(root,snapshots,commitments,scores);index["execution_errors"]=errors;index["runtime_seconds"]=time.perf_counter()-begin
    return {"index":index,"registration":reg,"snapshots":snapshots[-1:],"commitments":commitments,"scores":scores,"errors":errors}
def main():
    with app.run():result=tick.remote("initialize")
    out=Path("artifacts/signals-v6");out.mkdir(parents=True,exist_ok=True)
    for name in ("index","registration"):(out/(name+".json")).write_bytes(encoded(result[name]))
    for kind in ("snapshots","commitments","scores"):
        for record in result[kind]:(out/(kind+"-"+digest(record)+".json")).write_bytes(encoded(record))
    (out/"execution-errors.json").write_bytes(encoded(result["errors"]))
    print("SIGNALS_V6_EXECUTION:"+json.dumps({"snapshot_count":result["index"]["snapshot_count"],"cohort":result["index"]["cohort"],"readiness":result["index"]["readiness"],"ledger":result["index"]["ledger"],"errors":result["errors"],"runtime_seconds":result["index"]["runtime_seconds"]}),flush=True)
if __name__=="__main__":main()
