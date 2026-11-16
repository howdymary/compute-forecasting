"""Actual cross-role memory over the registered matched-study evidence."""
import asyncio,json,os,pathlib,time,uuid
from datetime import datetime,timezone
from compute_forecast.direct_forecast_v12 import digest
def now():return datetime.now(timezone.utc).isoformat()
async def run():
    import httpx,tinker
    from tinker_cookbook.renderers import get_renderer
    from tinker_cookbook.recipes.decisions import Decision,DecisionRenderer,sample_decision
    root=pathlib.Path("inputs/evidence-v14");audit=json.loads((root/"audit.json").read_text());data=json.loads((root/"dataset.json").read_text());sources=json.loads((root/"bls-vintages.json").read_text())
    identity=uuid.uuid4().hex[:16];audience="cf-e14-"+identity;actors={r:"cf-e14-"+identity+"-"+r for r in ("researcher","scientist","skeptic")}
    report={"study_id":"direct-evidence-v14-memory","created_at":now(),"namespace":audience,"classification":"Current research planning about retained historical evidence; not historical benchmark memory","protocol_sha256":audit["protocol_sha256"],"source_sha":os.environ["GITHUB_SHA"],"source_manifest_sha256":digest(sources),"records":[],"reads":[],"decisions":[],"calls":[],"new_optimizer_updates":0,"accuracy_improvement":None,"provider_cost_usd":None};contents={}
    client=tinker.ServiceClient(display_name="Compute Forecast v14 evidence researcher scientist skeptic");sampler=await client.create_sampling_client(base_model="Qwen/Qwen3.5-4B");renderer=DecisionRenderer(get_renderer("qwen3_5_disable_thinking",sampler.get_tokenizer()))
    async with httpx.AsyncClient(timeout=45) as http:
        async def past(method,path,payload=None):
            r=await http.request(method,"https://api.past.dev/api/v1"+path,headers={"Authorization":"Bearer "+os.environ["PAST_API_KEY"]},json=payload);report["calls"].append({"method":method,"kind":path.split("/")[1],"status":r.status_code,"at":now()});r.raise_for_status();return r.json()
        await past("PUT","/audiences/"+audience,{"kind":"fixed","name":"Matched direct price and BLS study","identities":list(actors.values())})
        async def write(role,value):
            rid="cf-e14-"+identity+"-"+str(len(contents));contents[rid]=value;created=now()
            response=await past("POST","/ingest",{"id":rid,"identity":actors[role],"audience":audience,"timestamp":created,"label":"Matched forecast "+role,"content":json.dumps({"record_id":rid,"content":value})})
            complete=False
            for _ in range(30):
                status=await past("GET","/ingest/"+response["ingestionId"])
                if status.get("status")=="completed":complete=True;break
                if status.get("status")=="failed":break
                await asyncio.sleep(2)
            report["records"].append({"record_id":rid,"author":actors[role],"role":role,"created_at":created,"content_sha256":digest(value),"ingestion_id":response["ingestionId"],"ingestion_completed":complete});return rid
        async def read(role,rid):
            ids=set()
            for _ in range(5):
                value=await past("POST","/recall",{"query":rid+" Retrieve this record's exact source limitations for the next matched GPU forecast analysis.","identity":actors[role],"level":"medium"})
                ids={s["sourceId"] for item in value.get("results",[]) for s in item.get("sources",[])}
                if rid in ids:break
                await asyncio.sleep(2)
            writer=next(r["role"] for r in report["records"] if r["record_id"]==rid);verified=rid in ids and writer!=role
            report["reads"].append({"reader":actors[role],"reader_role":role,"writer_role":writer,"required_source_id":rid,"returned_source_ids":sorted(ids),"verified_cross_role_use":verified,"canonical_fallback":not verified,"consumed_content_sha256":digest(contents[rid]),"resolution":"Exact numeric payload resolved by returned source ID" if verified else "Canonical fallback; not counted as successful recall"})
            return contents[rid]
        async def decide(role,question,context,choices,records):
            prompt="You are the "+role+" in a frozen paired direct-forecasting study. Choose a useful bounded diagnostic. You cannot modify the training protocol, invent outcomes, claim news value, or infer causal energy effects. Current memory is not backdated into historical inputs.\n"+question+"\n"+json.dumps(context,sort_keys=True)
            probabilities=await sample_decision(sampler,renderer.render(Decision(prompt,[(c,c.replace("_"," ")) for c in choices])))
            choice=max(probabilities,key=probabilities.get);report["decisions"].append({"role":role,"question":question,"choice":choice,"distribution":probabilities,"used_record_ids":records,"context_sha256":digest(context),"at":now()});return choice
        facts={"hypothesis":"Archived electricity-distribution PPI features may lower7-day quantile pinball versus the matched price-only model","training_by_family":audit["training_by_family"],"training_tasks":audit["phase_tasks"]["training"],"evidence_readiness":audit["evidence_readiness"],"training_releases":audit["training_monthly_releases"],"source_records":[{"url":r["source_url"],"content_sha256":r["content_sha256"],"row_sha256":r["values"]["source_row_sha256"],"available_at":r["available_at"],"first_observed_at":r["first_observed_at"],"exa_request_id":r.get("exa_request_id")} for r in sources["records"]],"news_included":False,"limitations":["PPI is an index, not a tariff","Monthly features repeat across overlapping daily windows","Only3 dependent retrospective evaluation origins"]}
        focus=await decide("researcher","Which evidence qualification is most consequential?",facts,["original_release_vintage","exact_electricity_series","monthly_signal_variation"],[])
        rid=await write("researcher",{**facts,"selected_focus":focus})
        consumed=await read("scientist",rid)
        choices=["breakdown_by_monthly_vintage","breakdown_by_gpu_family","breakdown_by_price_change"]
        first=await decide("scientist","Choose the first diagnostic to retain with the matched study.",consumed,choices,[rid])
        def execute(kind):
            tasks=data["groups"]["training"]
            if kind=="breakdown_by_monthly_vintage":key=lambda t:t["bls"]["reference_period"]
            elif kind=="breakdown_by_gpu_family":key=lambda t:"H100" if t["metadata"]["gpu_model"].startswith("H100") else "A100"
            else:key=lambda t:"changed" if any(y!=t["anchor"] for y in t["outcomes"]) else "unchanged"
            from collections import Counter
            return {"diagnostic":kind,"training_counts":dict(Counter(key(t) for t in tasks)),"classification":"Input-readiness diagnostic, not forecast improvement"}
        sid=await write("scientist",{"registered_candidate":"price_evidence versus price_only","selected_diagnostic":first,"actual_result":execute(first)})
        result=await read("skeptic",sid);evidence=await read("skeptic",rid)
        criticism=await decide("skeptic","Which limitation most restricts interpretation?",{"evidence":evidence,"result":result},["monthly_releases_are_not_independent_daily_cases","small_h100_training_cohort","ppi_is_not_a_provider_tariff"],[rid,sid])
        cid=await write("skeptic",{"criticism":criticism,"fixed_requirements":["Report matched loss, coverage, width and failures","Keep final dates retrospective","Do not generalize to news or future accuracy"]})
        objection=await read("scientist",cid)
        final=await decide("scientist","Choose the next useful diagnostic after the recalled criticism.",{"previous":result,"criticism":objection},choices,[sid,cid])
        final_id=await write("scientist",{"next_diagnostic":final,"actual_result":execute(final),"changed_after_criticism":first!=final,"protocol_changed":False,"performance_improvement":None})
        await read("researcher",final_id)
        await write("researcher",{"next_research_requirement":"Advance commitments and subsequent compatible market outcomes; do not recycle retrospective dates","used_record":final_id})
        report["changed_after_criticism"]=first!=final;report["actual_diagnostics"]=[execute(first),execute(final)]
    writers={r["author"] for r in report["records"] if r["ingestion_completed"]};readers={r["reader"] for r in report["reads"] if r["verified_cross_role_use"]};uses=sum(r["verified_cross_role_use"] for r in report["reads"])
    report["eligibility"]={"writers":len(writers),"readers":len(readers),"cross_role_uses":uses,"requirements_met":len(writers)>1 and len(readers)>1 and uses>0}
    report["status"]="verified" if report["eligibility"]["requirements_met"] else "memory_incomplete";report["completed_at"]=now()
    out=pathlib.Path("artifacts/evidence-v14-audit");out.mkdir(parents=True,exist_ok=True);(out/"memory.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"eligibility":report["eligibility"],"changed_after_criticism":report["changed_after_criticism"],"decisions":len(report["decisions"])}),flush=True)
if __name__=="__main__":asyncio.run(run())
