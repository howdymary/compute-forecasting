"""Current market-source context and bounded, source-grounded research planning."""
from __future__ import annotations
import asyncio,hashlib,json,os,time,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
from .review_v4 import digest,encoded
def now():return datetime.now(timezone.utc).isoformat()
def before(value,bound):
    if len(value)==10:return datetime.fromisoformat(value).date()<=bound.date()
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("Evidence timestamp requires timezone")
    return t<=bound
async def run(private_dir,output):
    import httpx,tinker
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import Decision,DecisionRenderer,sample_decision
    from .policy_v2 import MODEL
    config=json.loads(Path("configs/market-context-v4.json").read_bytes());run_id=uuid.uuid4().hex;start=time.perf_counter();root=Path(private_dir);root.mkdir(parents=True,exist_ok=True)
    report={"schema_version":4,"study_id":config["study_id"],"run_id":run_id,"source_sha":os.environ.get("GITHUB_SHA"),"available_at":now(),"classification":config["classification"],"sources":[],"discovery":[],"memory_records":[],"memory_reads":[],"service_calls":[],"plans":[],"historical_benchmark_inputs_changed":False,"forecast_accuracy_result":None}
    actors={role:"cf-market-v4-"+run_id+"-"+role for role in ("researcher","scientist","skeptic")};audience="cf-market-v4-"+run_id[:24];contents={}
    async with httpx.AsyncClient(timeout=60) as client:
        response=await client.post("https://api.exa.ai/contents",headers={"x-api-key":os.environ["EXA_API_KEY"]},json={"ids":[s["url"] for s in config["sources"]],"text":{"maxCharacters":12000}})
        response.raise_for_status();body=response.json();(root/"market-contents.json").write_bytes(encoded(body));report["service_calls"].append({"service":"exa","kind":"contents","request_id":body.get("requestId"),"cost_dollars":body.get("costDollars"),"at":now()})
        canonical=lambda x:str(x).rstrip("/")
        found={canonical(x.get("url") or x.get("id")):x for x in body.get("results",[])}
        for source in config["sources"]:
            result=found.get(canonical(source["url"]));published=source.get("published_date")
            if published and published>datetime.now(timezone.utc).date().isoformat():continue
            if not result or not (result.get("text") or result.get("highlights")):
                report["sources"].append({**source,"status":"retrieval_unavailable","retrieved_at":now()});continue
            report["sources"].append({**source,"status":"retrieved_primary_source","retrieved_at":now(),"available_at":now(),"content_sha256":digest({"text":result.get("text"),"highlights":result.get("highlights")}),"publication_scope":"Metadata, links and authored summary only; raw content private","historical_availability_established":False})
        query="Official GPU cloud infrastructure capacity announcements, new regions and GPU supply constraints; explain delivery timing, configuration and availability, excluding rental price history"
        response=await client.post("https://api.exa.ai/search",headers={"x-api-key":os.environ["EXA_API_KEY"]},json={"query":query,"type":"auto","numResults":5,"includeDomains":["nvidianews.nvidia.com","investor.nvidia.com","aws.amazon.com","press.aboutamazon.com","cloud.google.com","coreweave.com","lambda.ai"],"startPublishedDate":(datetime.now(timezone.utc)-timedelta(days=30)).isoformat(),"endPublishedDate":now(),"contents":{"highlights":True}})
        response.raise_for_status();news=response.json();(root/"market-discovery.json").write_bytes(encoded(news));report["service_calls"].append({"service":"exa","kind":"search","request_id":news.get("requestId"),"query":query,"cost_dollars":news.get("costDollars"),"at":now()})
        for item in news.get("results",[]):
            published=item.get("publishedDate")
            if published and not before(published,datetime.now(timezone.utc)):continue
            report["discovery"].append({"url":item.get("url"),"title":item.get("title"),"published_at":published,"retrieved_at":now(),"content_sha256":digest({"text":item.get("text"),"highlights":item.get("highlights")}),"status":"discovered_metadata; quantitative claims require verification"})
        async def past(method,path,payload=None):
            response=await client.request(method,"https://api.past.dev/api/v1"+path,headers={"Authorization":"Bearer "+os.environ["PAST_API_KEY"]},json=payload)
            report["service_calls"].append({"service":"past.dev","method":method,"status_code":response.status_code,"at":now()});response.raise_for_status();return response.json()
        available=True
        try:await past("PUT","/audiences/"+audience,{"kind":"fixed","name":"Forward market context v4","identities":list(actors.values())})
        except Exception as e:available=False;report["memory_setup_error"]=type(e).__name__
        async def write(role,value):
            identifier="cf-market-v4-"+run_id+"-"+str(len(contents));contents[identifier]=value
            receipt={"record_id":identifier,"author":actors[role],"role":role,"content_sha256":digest(value),"created_at":now()}
            if available:
                try:
                    r=await past("POST","/ingest",{"id":identifier,"identity":actors[role],"audience":audience,"timestamp":receipt["created_at"],"label":"Forward market research "+role,"content":json.dumps({"record_id":identifier,"content":value})})
                    receipt["ingestion_id"]=r["ingestionId"]
                    for _ in range(40):
                        s=await past("GET","/ingest/"+r["ingestionId"])
                        if s.get("status")=="completed":receipt["ingestion_completed"]=True;break
                        if s.get("status")=="failed":raise RuntimeError("Memory ingestion failed")
                        await asyncio.sleep(2)
                except Exception as e:receipt["error_type"]=type(e).__name__
            report["memory_records"].append(receipt);return identifier
        async def read(role,identifier):
            receipt={"reader":actors[role],"required_source_id":identifier,"actual_cross_role_use":False}
            if available:
                try:
                    for _ in range(5):
                        result=await past("POST","/recall",{"query":identifier+" Which sourced context and caveats must guide the next research question?","identity":actors[role],"level":"medium"})
                        ids=sorted({s["sourceId"] for r in result.get("results",[]) for s in r.get("sources",[])})
                        receipt["returned_source_ids"]=ids
                        if identifier in ids:receipt["actual_cross_role_use"]=True;break
                        await asyncio.sleep(2)
                except Exception as e:receipt["error_type"]=type(e).__name__
            receipt["canonical_fallback"]=not receipt["actual_cross_role_use"];report["memory_reads"].append(receipt);return contents[identifier]
        source_record=await write("researcher",{"sources":[s for s in report["sources"] if s["status"]=="retrieved_primary_source"],"new_discovery":report["discovery"]})
        context=await read("scientist",source_record)
        service=tinker.ServiceClient(display_name="Compute Forecast current market research planning")
        sampler=await service.create_sampling_client(base_model=MODEL)
        renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(MODEL),sampler.get_tokenizer()))
        choices=[(x,x.replace("_"," ")) for x in config["bounded_plans"]]
        async def plan(criticism=None):
            text="Choose the next bounded research question using current verified source context. This is research planning, not a numerical price forecast. Announcements are not delivered capacity; the archived price snapshot ends November6. Do not modify historical benchmark inputs.\n"+json.dumps({"source_context":context,"criticism":criticism},sort_keys=True)
            distribution=await sample_decision(sampler,renderer.render(Decision(text,choices)))
            choice=max(distribution,key=distribution.get)
            row={"selected_question":choice,"distribution":distribution,"used_memory_records":[source_record]+([critic_record] if criticism else []),"source_ids":[s["id"] for s in context["sources"]],"created_at":now(),"numerical_execution_status":"pending_registered_data_and_test"}
            report["plans"].append(row);return row
        first=await plan();plan_record=await write("scientist",first);skeptic_context=await read("skeptic",plan_record)
        objection={"about_plan":skeptic_context["selected_question"],"objection":"Separate announced from delivered capacity and hardware throughput from rental rates. Current price vintages must be verified before a short-horizon numerical claim. Power and manufacturing changes can act over years, not necessarily1/3/7days.","source_record":source_record}
        critic_record=await write("skeptic",objection);criticism=await read("scientist",critic_record);second=await plan(criticism)
        final_record=await write("scientist",second);await read("researcher",final_record)
        report["actual_cross_role_reads"]=sum(r["actual_cross_role_use"] for r in report["memory_reads"])
    report.update(status="completed_source_grounded_planning",completed_at=now(),runtime_seconds=time.perf_counter()-start,actual_tinker_decisions=len(report["plans"]),decision_changed=report["plans"][0]["selected_question"]!=report["plans"][-1]["selected_question"],cost_usd=None,limitations=["Current retrieved sources are unavailable to old historical forecast origins","Vendor plans and performance claims are attributed, not verified realized capacity","Changed planning choices do not establish improved forecasting accuracy","This uses starting model weights for a separate planning task, not evidence of trained selector transfer"])
    from .public_results import private_guard
    private_guard(report);Path(output).write_bytes(encoded(report));return report
def load_for_issue(root,issued_at):
    bound=datetime.fromisoformat(issued_at.replace("Z","+00:00"));candidates=[]
    for p in Path(root).glob("*.json"):
        value=json.loads(p.read_bytes())
        if value.get("study_id")=="market-context-v4" and before(value["completed_at"],bound):candidates.append(value)
    if not candidates:return None
    selected=max(candidates,key=lambda v:v["completed_at"])
    if bound-datetime.fromisoformat(selected["completed_at"])>timedelta(days=7):return None
    return {"available_at":selected["completed_at"],"source_sha256":digest(selected),"classification":"Separate exploratory current-market-context treatment","sources":[{k:s[k] for k in ("id","url","summary","caveat","retrieved_at","content_sha256")} for s in selected["sources"] if s["status"]=="retrieved_primary_source"]}
