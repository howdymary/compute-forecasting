"""Bounded Exa method research and service probes, isolated from market observations."""
from __future__ import annotations
import argparse,asyncio,csv,hashlib,io,json,os,subprocess,time,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
import modal
from .starter_probe import volume
from .campaign_v2 import MODEL,now,write,digest

app=modal.App("compute-forecast-v2-evidence")
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
TOPICS={
 "calibration":"prequential residual quantile calibration prediction intervals time series",
 "missingness":"time series missing observations missingness indicators forecasting",
 "persistence":"intermittent unchanged time series persistence baseline forecast",
 "ensemble":"convex forecast combination validation ensemble quantile forecasts",
 "autoregression":"regularized autoregression direct multi horizon forecasting",
 "trees":"HistGradientBoostingRegressor quantile loss early stopping time series",
 "composition":"matched basket price index provider configuration composition methodology",
 "evaluation":"rolling origin forecast evaluation dependence pinball loss"}
SUFFIXES=("official documentation methodology","implementation temporal validation","limitations and failure modes","baseline ablation evidence","uncertainty calibration comparison")
DOMAINS=["scikit-learn.org","nixtlaverse.nixtla.io","jmlr.org","proceedings.neurips.cc","proceedings.iclr.cc","tinker-docs.thinkingmachines.ai","modal.com","silicondata.com","semianalysis.com"]
@app.function(image=image,cpu=.25,memory=512,timeout=120,volumes={"/data":volume})
def retain_private(run_id,payload):
    path=Path("/data/campaign-v2/evidence")/(run_id+".json")
    write(path,payload);volume.commit()
    return {"sha256":digest(payload),"private_storage":True}
async def collect(output,max_queries=40,resume=None):
    import httpx,tinker
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    run_id=uuid.uuid4().hex;private={"run_id":run_id,"created_at":now(),"scope":"current_method_research","historical_market_input":False,"responses":[]}
    sources={};requests=[];started=time.perf_counter()
    prior=json.loads(Path(resume).read_text()) if resume and Path(resume).is_file() else None
    if prior:
        sources={s["source_id"]:s for s in prior["sources"]};requests=list(prior["requests"])
        private["prior_search_bodies_status"]="Earlier retention failed; original metadata retained; contents re-retrieved below"
    async with httpx.AsyncClient(timeout=60) as client:
        async def search(query,topic,snapshot=None):
            payload={"query":query,"type":"auto","numResults":3,"includeDomains":DOMAINS,"contents":{"highlights":True}}
            if snapshot:payload["contents"]["snapshotAsOf"]=snapshot
            begin=time.perf_counter()
            for attempt in range(4):
                response=await client.post("https://api.exa.ai/search",headers={"x-api-key":os.environ["EXA_API_KEY"]},json=payload)
                if response.status_code in (429,500,502,503,504) and attempt<3:
                    await asyncio.sleep(min(20,2**attempt));continue
                break
            if response.status_code!=200:
                row={"topic":topic,"query":query,"status_code":response.status_code,"snapshot_requested":snapshot,"status":"unavailable","runtime_seconds":time.perf_counter()-begin}
                requests.append(row);return
            data=response.json();private["responses"].append({"request":payload,"response":data,"retrieved_at":now()})
            ids=[]
            for r in data.get("results",[]):
                url=r.get("url")
                if not url:continue
                identifier=hashlib.sha256(url.encode()).hexdigest()[:16];ids.append(identifier)
                text=json.dumps({"text":r.get("text"),"highlights":r.get("highlights")},sort_keys=True)
                item={"source_id":identifier,"url":url,"title":r.get("title"),"published_at":r.get("publishedDate"),"retrieved_at":now(),"content_sha256":hashlib.sha256(text.encode()).hexdigest(),"topic":topic,"historical_market_input":False,"snapshot_requested":snapshot}
                sources.setdefault(identifier,item)
            requests.append({"topic":topic,"query":query,"request_id":data.get("requestId"),"source_ids":ids,"status":"completed","runtime_seconds":time.perf_counter()-begin,"cost_dollars":data.get("costDollars"),"snapshot_requested":snapshot})
        # Capability request is methodological content, never a competition outcome.
        if not prior:await search("quantile regression time series official documentation","snapshot_capability","2026-07-01T00:00:00Z")
        queries=[] if prior else [(topic,text+" "+suffix) for topic,text in TOPICS.items() for suffix in SUFFIXES][:max_queries]
        if prior:
            urls=[s["url"] for s in sources.values()]
            for start in range(0,len(urls),5):
                response=await client.post("https://api.exa.ai/contents",headers={"x-api-key":os.environ["EXA_API_KEY"]},json={"ids":urls[start:start+5],"highlights":True})
                if response.status_code==200:
                    body=response.json();private["responses"].append({"kind":"recovered_contents","retrieved_at":now(),"response":body})
                    for item in body.get("results",[]):
                        sid=hashlib.sha256(item.get("url","").encode()).hexdigest()[:16]
                        if sid in sources:sources[sid].update(content_sha256=digest(item),retrieved_at=now(),content_recovered=True)
                else:private["responses"].append({"kind":"contents_failure","status_code":response.status_code})
        # Two requests at a time; preserve each raw response privately and metadata publicly.
        for start in range(0,len(queries),2):
            await asyncio.gather(*(search(query,topic) for topic,query in queries[start:start+2]))
            write(out/"evidence.json",{"schema_version":2,"run_id":run_id,"scope":"current_method_research","historical_market_input":False,"requests":requests,"sources":list(sources.values()),"status":"collecting"})
    service=tinker.ServiceClient(display_name="Compute Forecast v2 capability audit")
    cap=await service.get_server_capabilities_async()
    supported=[getattr(m,"model_name",str(m)) for m in cap.supported_models]
    capability={"model":MODEL,"supported":MODEL in supported,"supported_model_count":len(supported)}
    start_hour=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
    billing=subprocess.run(["tinker","billing","usage",(start_hour-timedelta(hours=4)).isoformat().replace("+00:00","Z"),(start_hour+timedelta(hours=1)).isoformat().replace("+00:00","Z"),"--csv","-"],capture_output=True,text=True,timeout=90)
    billing_info={"available":billing.returncode==0,"data_lag":"Provider usage can lag by hours; gross estimates are not invoices or remaining credits"}
    if billing.returncode==0:
        parsed=list(csv.DictReader(io.StringIO(billing.stdout)));private["billing_probe"]=parsed
        billing_info.update(rows=len(parsed),columns=list(parsed[0]) if parsed else [])
    else:billing_info["reason"]="Billing CLI unsupported or billing-view permission unavailable; no cost invented"
    receipt=retain_private.remote(run_id,private)
    result={"schema_version":2,"run_id":run_id,"status":"completed","created_at":now(),"scope":"current_method_research","historical_market_input":False,
        "requests":requests,"sources":list(sources.values()),"request_count":len(requests),"unique_sources":len(sources),"tinker_capability":capability,
        "snapshot_status":"Request acceptance is recorded; page vintage and plan entitlement require further validation before historical use",
        "billing_probe":billing_info,"private_retention":receipt,"runtime_seconds":time.perf_counter()-started,
        "code_sha":os.environ.get("GITHUB_SHA"),"credit_balance_status":"Not exposed by these API probes; no topups performed"}
    write(out/"evidence.json",result)
    print("V2_EVIDENCE:"+json.dumps({k:v for k,v in result.items() if k not in ("requests","sources")}))
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
        f.write("# Current-method Exa research and capability probe\n\n")
        f.write("Historical market input: false. Full response bodies retained privately.\n\n~~~json\n"+json.dumps({k:v for k,v in result.items() if k not in ("requests","sources")},indent=2)+"\n~~~\n")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",default="artifacts/v2-evidence");p.add_argument("--max-queries",type=int,default=40);p.add_argument("--resume");a=p.parse_args()
    if not 1<=a.max_queries<=60:raise ValueError("Unbounded research request")
    with app.run():asyncio.run(collect(a.output,a.max_queries,a.resume))
