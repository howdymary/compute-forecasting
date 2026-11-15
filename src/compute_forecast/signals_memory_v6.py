"""Actual cross-role memory for prospective signal-readiness research."""
import asyncio,json,os,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from .review_v4 import digest,encoded
from .signals_v6 import utc
def now():return datetime.now(timezone.utc).isoformat()
def check(name,index):
    s=index["latest_snapshot"]
    if name=="audit_contract_freshness":return {"check":name,"current_quotes":sum(r["date"]==utc(r["fetched_at"]).date().isoformat() for r in s["prices"]["rows"]),"contracts":len(s["prices"]["cohort"]),"availability":"Advertised; rentable capacity unverified"}
    if name=="audit_revision_capture":return {"check":name,"latest_bls_period":s["bls"]["latest_period"] if s.get("bls") else None,"revision_warnings":[f for r in (s.get("bls") or {}).get("observations",[]) for f in r.get("footnotes",[]) if f.get("text")],"retained_vintages":index["snapshot_count"]}
    return {"check":name,"retained_days":index["readiness"]["retained_price_days"],"required_days":56,"required_matured_pairs":32,"prospective_primary_scores":index["primary_scored_cells"],"training":"gated"}
async def run(index):
    import httpx,tinker
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import Decision,DecisionRenderer,sample_decision
    identifier=uuid.uuid4().hex;actors={r:"cf-sig6-"+identifier[:16]+"-"+r for r in ("researcher","scientist","skeptic")};audience="cf-sig6-"+identifier[:16]
    report={"schema_version":6,"study_id":"signals-memory-v6","created_at":now(),"source_sha":os.environ.get("GITHUB_SHA"),"namespace":audience,"records":[],"reads":[],"decisions":[],"steps":[],"calls":[],"source_snapshot_sha256":digest(index["latest_snapshot"]),"protocol_sha256":index["protocol_sha256"],"new_optimizer_updates":0,"accuracy_improvement":None};contents={}
    async with httpx.AsyncClient(timeout=60) as http:
        async def past(method,path,value=None):
            r=await http.request(method,"https://api.past.dev/api/v1"+path,headers={"Authorization":"Bearer "+os.environ["PAST_API_KEY"]},json=value);report["calls"].append({"method":method,"kind":path.split("/")[1],"status":r.status_code,"at":now()});r.raise_for_status();return r.json()
        assert len(audience)<=40
        await past("PUT","/audiences/"+audience,{"kind":"fixed","name":"Prospective signal study readiness","identities":list(actors.values())})
        async def write(role,value):
            rid="cf-sig6-"+identifier+"-"+str(len(contents));contents[rid]=value
            r=await past("POST","/ingest",{"id":rid,"identity":actors[role],"audience":audience,"timestamp":now(),"label":"Signals readiness "+role,"content":json.dumps({"record_id":rid,"content":value})})
            done=False
            for _ in range(40):
                status=await past("GET","/ingest/"+r["ingestionId"])
                if status.get("status")=="completed":done=True;break
                if status.get("status")=="failed":raise RuntimeError("Memory ingestion failed")
                await asyncio.sleep(2)
            report["records"].append({"record_id":rid,"role":role,"author":actors[role],"content_sha256":digest(value),"ingestion_id":r["ingestionId"],"ingestion_completed":done});return rid
        async def read(role,rid):
            verified=False
            for _ in range(5):
                result=await past("POST","/recall",{"query":rid+" Retrieve this record for my next prospective research task.","identity":actors[role],"level":"medium"})
                ids={s["sourceId"] for item in result.get("results",[]) for s in item.get("sources",[])}
                if rid in ids:verified=True;break
                await asyncio.sleep(2)
            writer=next(r["role"] for r in report["records"] if r["record_id"]==rid)
            report["reads"].append({"reader":actors[role],"reader_role":role,"writer_role":writer,"required_source_id":rid,"returned_required_source_id":rid if verified else None,"verified_cross_role_use":verified and writer!=role,"canonical_fallback":not verified,"consumed_content_sha256":digest(contents[rid])})
            return contents[rid]
        client=tinker.ServiceClient(display_name="Compute Forecast signal-readiness research")
        sampler=await client.create_sampling_client(base_model="Qwen/Qwen3.5-4B")
        renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name("Qwen/Qwen3.5-4B"),sampler.get_tokenizer()))
        async def decide(role,question,value,choices,ids):
            prompt="You are the "+role+" in a registered prospective GPU signal study. Choose a bounded research check. You cannot change the frozen protocol, invent future outcomes or claim accuracy improvement. Use the supplied retained evidence.\n"+question+"\n"+json.dumps(value,sort_keys=True)
            distribution=await sample_decision(sampler,renderer.render(Decision(prompt,[(c,c.replace("_"," ")) for c in choices])));selected=max(distribution,key=distribution.get)
            report["decisions"].append({"role":role,"selected":selected,"distribution":distribution,"used_record_ids":ids,"context_sha256":digest(value),"at":now()});return selected
        facts={"price_source":index["latest_snapshot"]["prices"],"features":index["latest_snapshot"]["features"],"readiness":index["readiness"],"source_metadata":[{k:r.get(k) for k in ("url","sha256","retrieved_at")} for r in index["latest_snapshot"]["receipts"]],"hypothesis":index["protocol"]["hypothesis"]}
        focus=await decide("researcher","Which evidence gap should we inspect first?",facts,["quote_freshness","economic_release_vintages","informative_signal_history"],[])
        facts["focus"]=focus;rid=await write("researcher",facts)
        evidence=await read("scientist",rid);choices=["audit_contract_freshness","audit_revision_capture","audit_informative_variation"]
        draft=await decide("scientist","Choose a check that can be executed on the retained snapshot.",evidence,choices,[rid]);first=check(draft,index)
        sid=await write("scientist",{"proposed_check":draft,"actual_check_result":first,"candidate":"111 versus000, unchanged registered comparison"})
        critic_input={"experiment":await read("skeptic",sid),"evidence":await read("skeptic",rid)}
        objection=await decide("skeptic","Which limitation most restricts a forecasting-improvement claim?",critic_input,["insufficient_matured_labels","insufficient_monthly_release_variation","advertised_not_available_capacity"],[sid,rid])
        cid=await write("skeptic",{"objection":objection,"rule":"Retain incumbent; do not relax registration, maturity or training gates."})
        criticism=await read("scientist",cid)
        final=await decide("scientist","Choose the next executable check after criticism.",{"previous":first,"criticism":criticism},choices,[sid,cid]);second=check(final,index)
        fid=await write("scientist",{"next_check":final,"actual_check_result":second,"changed_after_criticism":draft!=final,"forecast_promotion":"pending; no prospective primary scores"})
        after=await read("researcher",fid);await write("researcher",{"next_task":after["next_check"],"required_evidence":"Continue real captures and wait for matured labels; no synthetic market observations"})
        report["steps"]=[{"role":"researcher","summary":"Selected evidence focus: "+focus,"record_id":rid},{"role":"scientist","summary":"Executed "+draft,"record_id":sid,"result":first},{"role":"skeptic","summary":"Identified "+objection,"record_id":cid},{"role":"scientist","summary":"Executed next check: "+final,"record_id":fid,"result":second}]
        report["changed_after_criticism"]=draft!=final
    writers={r["author"] for r in report["records"] if r["ingestion_completed"]};readers={r["reader"] for r in report["reads"] if r["verified_cross_role_use"]};uses=sum(r["verified_cross_role_use"] for r in report["reads"])
    report["eligibility"]={"writers":len(writers),"readers":len(readers),"cross_role_uses":uses,"requirements_met":len(writers)>1 and len(readers)>1 and uses>0}
    report["actual_tinker_decisions"]=len(report["decisions"]);report["status"]="verified" if report["eligibility"]["requirements_met"] else "memory_incomplete";report["completed_at"]=now();report["provider_cost_usd"]=None
    return report
def main():
    index=json.loads(Path("results/signals-v6/runs/43763941660/index.json").read_bytes());report=asyncio.run(run(index))
    import modal
    from .signals_remote_v6 import image,public,data
    app=modal.App("compute-forecast-signals-memory-v6")
    @app.function(image=image,cpu=.25,memory=512,timeout=120,serialized=True,volumes={"/public":public,"/data":data})
    def retain_report(value):
        root=Path("/data/signals-v6/memory");root.mkdir(parents=True,exist_ok=True);identity=digest(value)
        (root/(identity+".json")).write_bytes(encoded(value));data.commit()
        path=Path("/public/signals-v6/memory.json");temp=path.with_suffix(".pending");temp.write_bytes(encoded(value));temp.replace(path);public.commit()
        return identity
    with app.run():identity=retain_report.remote(report)
    out=Path("artifacts/signals-memory-v6");out.mkdir(parents=True,exist_ok=True);(out/"memory.json").write_bytes(encoded(report))
    print("SIGNALS_V6_MEMORY:"+json.dumps({"status":report["status"],"eligibility":report["eligibility"],"changed_after_criticism":report["changed_after_criticism"],"decisions":report["actual_tinker_decisions"],"sha256":identity}),flush=True)
    assert report["eligibility"]["requirements_met"],"Memory requirement gate failed"
if __name__=="__main__":main()
