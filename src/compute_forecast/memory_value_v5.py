"""Three bounded model-driven roles using actual shared-memory records."""
from __future__ import annotations
import asyncio,json,os,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from .review_v4 import digest,encoded
from .capability_v5 import rental_pairs,benchmarks,analyze
MODEL="Qwen/Qwen3.5-4B"
def now():return datetime.now(timezone.utc).isoformat()
async def run(study,private_dir):
    import httpx,tinker
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import Decision,DecisionRenderer,sample_decision
    identifier=uuid.uuid4().hex;start=time.perf_counter();root=Path(private_dir);root.mkdir(parents=True,exist_ok=True)
    actors={r:"cf-v5-cur-"+identifier[:16]+"-"+r for r in ("researcher","scientist","skeptic")};audience="cf-v5-current-"+identifier[:16]
    report={"schema_version":5,"study_id":"market-memory-value-v5","run_id":identifier,"source_sha":os.environ.get("GITHUB_SHA"),"created_at":now(),"namespace":"current research; never benchmark-safe historical evidence","records":[],"reads":[],"steps":[],"decisions":[],"source_requests":[],"memory_calls":[],"analyses":[],"actual_tinker_decisions":0,"new_optimizer_updates":0,"provider_cost_usd":None}
    contents={};pairs=rental_pairs(study);options=benchmarks(study)
    if not pairs or len(options)<3:raise ValueError("No verified SXM80 rental/precision benchmark cohort")
    pair=pairs[0]
    async with httpx.AsyncClient(timeout=60) as http:
        async def past(method,path,payload=None):
            r=await http.request(method,"https://api.past.dev/api/v1"+path,headers={"Authorization":"Bearer "+os.environ["PAST_API_KEY"]},json=payload);report["memory_calls"].append({"method":method,"path_kind":path.split("/")[1],"status_code":r.status_code,"at":now()})
            if r.is_error:
                error_text=r.text[:500].replace(os.environ["PAST_API_KEY"],"[redacted]")
                (root/("past-error-"+str(len(report["memory_calls"]))+".json")).write_bytes(encoded({"status":r.status_code,"response":error_text}))
                report["last_memory_error"]={"status_code":r.status_code,"path_kind":path.split("/")[1],"detail":error_text if path.startswith("/audiences/") else "Response retained privately"}
            r.raise_for_status();return r.json()
        available=True
        try:await past("PUT","/audiences/"+audience,{"kind":"fixed","name":"Pacific GPU value current research","identities":list(actors.values())})
        except Exception as e:available=False;report["memory_setup_error"]=type(e).__name__
        async def write(role,value):
            rid="cf-value-v5-"+identifier+"-"+str(len(contents));contents[rid]=value;item={"record_id":rid,"author":actors[role],"role":role,"created_at":now(),"content_sha256":digest(value),"kind":"current_research"}
            if available:
                try:
                    x=await past("POST","/ingest",{"id":rid,"identity":actors[role],"audience":audience,"timestamp":item["created_at"],"label":"Pacific value "+role,"content":json.dumps({"record_id":rid,"content":value})})
                    item["ingestion_id"]=x["ingestionId"]
                    for _ in range(40):
                        status=await past("GET","/ingest/"+x["ingestionId"])
                        if status.get("status")=="completed":item["ingestion_completed"]=True;break
                        if status.get("status")=="failed":raise RuntimeError("Memory ingestion failed")
                        await asyncio.sleep(2)
                except Exception as e:item["error_type"]=type(e).__name__
            report["records"].append(item);return rid
        async def read(role,rid):
            item={"reader":actors[role],"reader_role":role,"required_source_id":rid,"writer_role":next(r["role"] for r in report["records"] if r["record_id"]==rid),"actual_cross_role_use":False}
            if available:
                try:
                    for _ in range(5):
                        x=await past("POST","/recall",{"query":rid+" Retrieve this record's specific facts and limitations for my next GPU-value task.","identity":actors[role],"level":"medium"})
                        ids=sorted({s["sourceId"] for r in x.get("results",[]) for s in r.get("sources",[])})
                        item["returned_source_ids"]=ids
                        if rid in ids:item["actual_cross_role_use"]=item["writer_role"]!=role;break
                        await asyncio.sleep(2)
                except Exception as e:item["error_type"]=type(e).__name__
            item["delivery"]="Verified past.dev recall; exact numeric payload resolved by returned record ID" if item["actual_cross_role_use"] else "Canonical-text fallback; not counted as successful memory recall"
            item["consumed_content_sha256"]=digest(contents[rid]);report["reads"].append(item);return contents[rid]
        service=tinker.ServiceClient(display_name="Pacific value v5 three-role research loop")
        sampler=await service.create_sampling_client(base_model=MODEL)
        renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(MODEL),sampler.get_tokenizer()))
        async def decide(role,question,context,choices,used):
            prompt="You are the "+role+" in a bounded GPU-value research study. Select a valid next research action from supplied choices. Use source evidence and explicit limitations. You cannot declare forecast accuracy, invent prices, or generalize MLPerf ratios to all workloads. Current retrieved evidence is not a historical benchmark feature.\n"+question+"\n"+json.dumps(context,sort_keys=True)
            distribution=await sample_decision(sampler,renderer.render(Decision(prompt,[(c,c.replace("_"," ")) for c in choices])))
            selected=max(distribution,key=distribution.get);row={"role":role,"question":question,"selected":selected,"distribution":distribution,"input_record_ids":used,"context_sha256":digest(context),"at":now()};report["decisions"].append(row);report["actual_tinker_decisions"]+=1;return selected
        prior={"observation":"Earlier frozen SFT evidence additions tied, and fixed criticism worsened loss on the reused A100 cohort.","consequence":"A memory read or changed interpretation is not a measured forecasting improvement.","validity":"Use exact SXM80 and precision-matched cohorts; separate current research from historical forecast inputs."}
        prior_id=await write("skeptic",prior);prior_read=await read("researcher",prior_id)
        query="Official NVIDIA MLCommons H100 A100 inference throughput varies with workload memory bandwidth precision system configuration"
        response=await http.post("https://api.exa.ai/search",headers={"x-api-key":os.environ["EXA_API_KEY"]},json={"query":query,"type":"auto","numResults":4,"includeDomains":["nvidia.com","mlcommons.org","epoch.ai"],"contents":{"highlights":True}})
        response.raise_for_status();raw=response.json();(root/"exa-primary.json").write_bytes(encoded(raw))
        sources=[{"url":r.get("url"),"title":r.get("title"),"retrieved_at":now(),"content_sha256":digest({"text":r.get("text"),"highlights":r.get("highlights")})} for r in raw.get("results",[])]
        report["source_requests"].append({"query":query,"request_id":raw.get("requestId"),"cost_dollars":raw.get("costDollars"),"source_metadata":sources,"response_sha256":digest(raw)})
        evidence={"question":"When does H100's throughput justify its hourly rental premium?","pair":pair,"benchmark_options":options,"external_sources":sources,"prior_limits":prior_read,"availability":"Evidence assembled now; retrospective description, not November6 model inputs"}
        evidence["retrieved_evidence"]=[{"url":r.get("url"),"highlights":r.get("highlights",[])[:2]} for r in raw.get("results",[])]
        focus=await decide("researcher","Which mechanism deserves the first economic check?",evidence,["workload_mix","provider_composition","energy_costs"],[prior_id])
        evidence["selected_focus"]=focus;evidence_id=await write("researcher",evidence)
        report["steps"].append({"role":"researcher","action":"hypothesis and sourced evidence","summary":"Research focus: "+focus.replace("_"," ")+". Verified same-collector SXM80 rates and workload-specific capability variants were written to shared memory.","record_id":evidence_id,"used_record_ids":[prior_id]})
        consumed=await read("scientist",evidence_id)
        chosen=await decide("scientist","Select one registered precision-matched benchmark context for the rental-premium diagnostic.",consumed,list(options),[evidence_id])
        result=analyze(study,pair["id"],chosen);report["analyses"].append(result)
        actions=["publish_workload_specific","add_sensitivity_range","withhold_economic_preference"]
        draft=await decide("scientist","Choose the draft publication action before criticism.",result,actions,[evidence_id])
        result_id=await write("scientist",{"result":result,"draft_action":draft})
        report["steps"].append({"role":"scientist","action":"deterministic experiment","summary":"Selected "+chosen.replace("_"," ")+". The tool computed rental-premium / throughput = "+format(result["h100_cost_per_matched_work_relative_to_a100"],".4f")+". Draft action: "+draft.replace("_"," ")+".","record_id":result_id,"used_record_ids":[evidence_id]})
        critic_result=await read("skeptic",result_id);critic_evidence=await read("skeptic",evidence_id)
        objection=await decide("skeptic","Which limitation is most consequential for interpreting this result?",{"experiment":critic_result,"evidence":critic_evidence},["provider_composition_not_matched","benchmark_not_universal","historical_not_future_accuracy"],[result_id,evidence_id])
        criticism={"selected_objection":objection,"constraints":["Provider populations are not pair-matched","A measured workload ratio is not universal","A descriptive cost ratio is not future rental/resale accuracy"],"about_record":result_id}
        critic_id=await write("skeptic",criticism)
        report["steps"].append({"role":"skeptic","action":"criticism","summary":"Primary objection: "+objection.replace("_"," ")+". The result must retain cohort, workload and retrospective limits.","record_id":critic_id,"used_record_ids":[result_id,evidence_id]})
        recalled=await read("scientist",critic_id)
        final=await decide("scientist","Reconsider the same publication actions using the critic's recalled record.",{"experiment":result,"criticism":recalled,"draft_action":draft},actions,[result_id,critic_id])
        sensitivity=[analyze(study,pair["id"],key) for key in options] if final=="add_sensitivity_range" else []
        final_value={"action":final,"draft_action":draft,"changed_after_criticism":final!=draft,"analysis":result,"sensitivity":sensitivity,"accuracy_improvement":None}
        final_id=await write("scientist",final_value)
        report["steps"].append({"role":"scientist","action":"next decision","summary":"Final action: "+final.replace("_"," ")+". "+("The action changed after criticism." if final!=draft else "The action did not change after criticism.")+" No forecasting improvement is inferred.","record_id":final_id,"used_record_ids":[critic_id,result_id]})
        after=await read("researcher",final_id)
        next_question=await decide("researcher","Which missing input should the next registered research cycle seek?",after,["matched_provider_quotes","workload_profile","verified_power_measurements"],[final_id])
        next_id=await write("researcher",{"next_question":next_question,"used_result":final_id})
        report["steps"].append({"role":"researcher","action":"next hypothesis","summary":"Next missing evidence: "+next_question.replace("_"," ")+".","record_id":next_id,"used_record_ids":[final_id]})
        report["verified_cross_role_reads"]=sum(r["actual_cross_role_use"] for r in report["reads"])
        writers={r["author"] for r in report["records"] if r.get("ingestion_completed")};readers={r["reader"] for r in report["reads"] if r["actual_cross_role_use"]}
        report["eligibility"]={"successful_writers":len(writers),"successful_readers":len(readers),"cross_role_use":report["verified_cross_role_reads"],"requirements_met":len(writers)>1 and len(readers)>1 and report["verified_cross_role_reads"]>0}
        report["interpretation"]="A researcher, scientist and skeptic use sourced records to choose, test and qualify a benchmark-specific GPU-value hypothesis."
        report["outcome_claim"]="Verified shared-memory use; no memory accuracy gain or new learned weights is established." if report["eligibility"]["requirements_met"] else "External memory requirements were not met; canonical fallback was used. No memory benefit is claimed."
        report["final"]=final_value;report["next_question"]=next_question
    report.update(status="completed_verified_memory" if report["eligibility"]["requirements_met"] else "completed_with_memory_failure",runtime_seconds=time.perf_counter()-start,completed_at=now(),memory_source_namespace=audience,study_artifact_sha256=digest(study),retrospective=True)
    from .public_results import private_guard
    private_guard(report);return report

from .pacific_value_v5 import app,image,data,public
import modal
@app.function(image=image,cpu=.25,memory=1024,timeout=120,volumes={"/data":data,"/public":public})
def retain(report,private_files):
    root=Path("/data/value-v5/memory")/report["run_id"];root.mkdir(parents=True)
    for name,raw in private_files.items():
        if Path(name).name!=name:raise ValueError("Private evidence filename")
        (root/name).write_bytes(raw)
    (root/"report.json").write_bytes(encoded(report));data.commit()
    destination=Path("/public/value-v5");destination.mkdir(exist_ok=True)
    version=destination/("memory-"+report["run_id"]+".json");version.write_bytes(encoded(report))
    temp=destination/"memory.pending";temp.write_bytes(encoded(report));temp.replace(destination/"memory.json");public.commit()
    return {"artifact":version.name,"sha256":digest(report)}
def main():
    study=json.loads(Path(os.environ["V5_STUDY_FILE"]).read_bytes())
    private=Path("inputs/value-v5-private");private.mkdir(parents=True,exist_ok=True)
    report=asyncio.run(run(study,private))
    with app.run():receipt=retain.remote(report,{p.name:p.read_bytes() for p in private.glob("*.json")})
    out=Path("artifacts/value-memory-v5");out.mkdir(parents=True,exist_ok=True)
    (out/"memory.json").write_bytes(encoded(report));(out/"publication.json").write_bytes(encoded(receipt))
    print("VALUE_MEMORY_V5:"+json.dumps({"status":report["status"],"eligibility":report["eligibility"],"decisions":report["decisions"],"final":report["final"],"next_question":report["next_question"],"runtime":report["runtime_seconds"]}),flush=True)
if __name__=="__main__":main()
