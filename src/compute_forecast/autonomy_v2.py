"""Fresh, bounded numerical research with current Exa evidence and recorded criticism."""
from __future__ import annotations
import argparse,asyncio,hashlib,json,math,os,statistics,time,uuid
from pathlib import Path
import modal
from .campaign_v2 import app,evaluate_origin,volume,image,now,write,digest,MODEL,REGISTRY,BY_ID
from .policy_v2 import choose,criticism,INITIAL
public_volume=modal.Volume.from_name("compute-forecast-public",create_if_missing=False)
QUESTIONS={"calibration":"Can calibrated alternatives outperform persistence without excessively wide intervals?","composition":"Does removing price information reveal composition or coverage effects?"}
@app.function(image=image,cpu=.25,memory=512,timeout=120,volumes={"/data":volume,"/public":public_volume})
def publish(identifier,payload,private_response=None):
    write(Path("/data/campaign-v2/autonomy")/(identifier+".json"),{"public":payload,"private_response":private_response})
    write(Path("/public/experimental-v2/autonomy")/(identifier+".json"),payload)
    volume.commit();public_volume.commit()
    return {"public_digest":digest(payload),"run_id":identifier}
async def run(output,question="calibration",origin="2026-07-24",plan=None,policy_manifest=None):
    import httpx,tinker
    from tinker_cookbook import model_info,renderers
    if question not in QUESTIONS:raise ValueError("Unregistered research question")
    from .campaign_v2 import protocol
    from datetime import date,timedelta
    if origin not in protocol()["training_origins"]:raise ValueError("Only registered training-origin research")
    label_end=(date.fromisoformat(origin)+timedelta(days=7)).isoformat()
    run_id=uuid.uuid4().hex;out=Path(output);out.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    report={"schema_version":2,"run_id":run_id,"github_run_id":os.environ.get("GITHUB_RUN_ID"),"question_id":question,"question":QUESTIONS[question],"status":"running","started_at":now(),"code_sha":os.environ.get("GITHUB_SHA"),"origin":origin,"last_label_date":label_end,"scope":"current methodological research on training-period retrospective backtests","trial_budget":6,"events":[],"trials":[],"evidence":[],"cache_hits":0,"new_executions":0,"cost":None,"cost_status":"not yet available","model":MODEL,"historical_market_input":False}
    report["research_plan"]=json.loads(Path(plan).read_text()) if plan else None
    raw_responses=[]
    def flush():
        write(out/"autonomy.json",report);publish.remote(run_id,report,raw_responses)
    flush()
    service=tinker.ServiceClient(display_name="Compute Forecast v2 fresh autonomous research")
    if policy_manifest:
        selection=json.loads(Path(policy_manifest).read_text())
        from .policy_v2 import app as private_policy_app,load_private
        with private_policy_app.run():
            private=load_private.remote(selection["private_manifest_id"])
        if private["selected"]["checkpoint_id"]!=selection["checkpoint_id"]:raise ValueError("Checkpoint selection receipt mismatch")
        sampler=await service.create_sampling_client(model_path=private["selected"]["sampler_path"])
        report["decision_policy"]={k:v for k,v in selection.items() if k!="private_manifest_id"}
    else:
        sampler=await service.create_sampling_client(base_model=MODEL)
        report["decision_policy"]={"kind":"starting_policy","checkpoint_id":None}
    from tinker_cookbook.recipes.decisions import DecisionRenderer
    renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(MODEL),sampler.get_tokenizer()))
    task={"task_id":run_id,"origin":origin,"phase":"current_training_research","group":"eligible_A100_daily","scale":.01,"observation":{"measurement":"advertised daily rental offers","matured_labels_through":label_end},"validation":{}}
    revealed=[]
    memory_records=[];memory_calls=[];audience="cf-v2-"+run_id[:24]
    actors={r:"cf-v2-"+run_id+"-"+r for r in ("evidence_researcher","forecast_scientist","skeptic")}
    async with httpx.AsyncClient(timeout=60) as client:
        async def past(method,path,payload=None):
            r=await client.request(method,"https://api.past.dev/api/v1"+path,json=payload,headers={"Authorization":"Bearer "+os.environ["PAST_API_KEY"]})
            memory_calls.append({"service":"past.dev","method":method,"status_code":r.status_code,"at":now()});r.raise_for_status();return r.json()
        async def remember(role,kind,content,parents=()):
            source_id="cf-v2-"+run_id+"-"+str(len(memory_records))
            record={"record_id":source_id,"author":actors[role],"role":role,"kind":kind,"content":content,"parent_record_ids":list(parents),"created_at":now(),"historical_market_input":False}
            memory_records.append(record)
            if report.get("past_available"):
                try:
                    response=await past("POST","/ingest",{"id":source_id,"identity":actors[role],"audience":audience,"timestamp":record["created_at"],"label":"Compute Forecast v2 "+role,"content":json.dumps(record)})
                    ingestion=response["ingestionId"];record["ingestion_id"]=ingestion
                    for _ in range(60):
                        status=await past("GET","/ingest/"+ingestion)
                        if status.get("status")=="completed":record["ingestion_completed"]=True;break
                        if status.get("status")=="failed":raise RuntimeError("Memory ingestion failed")
                        await asyncio.sleep(2)
                except Exception as error:record["memory_error_type"]=type(error).__name__
            return source_id
        async def recall(role,required,query):
            entry={"event":"memory_read","role":role,"required_source_id":required,"scope":"current_method_research","created_at":now()}
            if report.get("past_available"):
                try:
                    for _ in range(5):
                        response=await past("POST","/recall",{"query":query,"identity":actors[role],"level":"medium"})
                        ids=sorted({s["sourceId"] for r in response.get("results",[]) for s in r.get("sources",[])})
                        if required in ids:
                            entry.update(returned_source_ids=ids,actual_cross_role_use=True);break
                        await asyncio.sleep(2)
                except Exception as error:entry["error_type"]=type(error).__name__
            report["events"].append(entry)
            # Input is the verified authored record. If recall succeeds, its source identity is recorded above.
            return next(r for r in memory_records if r["record_id"]==required)["content"]
        try:
            await past("PUT","/audiences/"+audience,{"kind":"fixed","name":"Compute Forecast v2 "+run_id,"identities":list(actors.values())});report["past_available"]=True
        except Exception as error:report.update(past_available=False,past_error_type=type(error).__name__)
        async def evidence(topic,uncertainty):
            query={"calibration":"prequential residual quantile prediction interval calibration time series official methodology","composition":"matched basket price index provider configuration composition Silicon Data SemiAnalysis methodology","missingness":"forecasting missing observations missingness indicators time series validation"}[topic]
            begin=time.perf_counter()
            r=await client.post("https://api.exa.ai/search",headers={"x-api-key":os.environ["EXA_API_KEY"]},json={"query":query,"type":"auto","numResults":3,"includeDomains":["scikit-learn.org","jmlr.org","proceedings.neurips.cc","silicondata.com","semianalysis.com"],"contents":{"highlights":True}})
            r.raise_for_status();body=r.json();raw_responses.append({"query":query,"response":body,"retrieved_at":now()})
            packet={"evidence_id":digest(body)[:20],"request_id":body.get("requestId"),"query":query,"triggering_uncertainty":uncertainty,"topic":topic,"retrieved_at":now(),"runtime_seconds":time.perf_counter()-begin,"sources":[{"url":x.get("url"),"title":x.get("title"),"published_at":x.get("publishedDate"),"content_sha256":digest({"text":x.get("text"),"highlights":x.get("highlights")})} for x in body.get("results",[])],"cost_dollars":body.get("costDollars"),"historical_market_input":False,"snapshot_requested":None,"historical_vintage":"current methods, never historical price input"}
            report["evidence"].append(packet)
            private_content={"metadata":packet,"permitted_private_method_context":[{"title":x.get("title"),"highlights":x.get("highlights")} for x in body.get("results",[])]}
            source=await remember("evidence_researcher","method_evidence",private_content)
            used=await recall("forecast_scientist",source,"Which methodological evidence addresses "+uncertainty+"?")
            return used,source
        async def execute(configs,hypothesis):
            event={"event":"experiment_requested","config_ids":configs,"hypothesis":hypothesis,"requested_at":now(),"status":"running","cache_hit":False,"new_numerical_execution":True}
            report["events"].append(event);flush();begin=time.perf_counter()
            result=await evaluate_origin.remote.aio(origin,config_ids=configs)
            if result["status"]!="completed" or result["cache_hit"] or not result["new_numerical_execution"]:raise ValueError("Expected fresh completed numerical execution")
            report["new_executions"]+=1
            for m in result["methods"]:
                row={"config_id":m["config_id"],"pinball":m["pinball"],"n_cells":m["n_cells"],"fallbacks":m["fallbacks"],"quantile_order_repairs":m["quantile_order_repairs"],"coverage":statistics.mean(c["covered"] for c in m["cases"]),"width":statistics.mean(c["width"] for c in m["cases"]),"run_id":result["run_id"],"modal_call_id":result["modal_call_id"],"runtime_seconds":result["runtime_seconds"],"cache_hit":False}
                report["trials"].append(row);revealed.append(m["config_id"]);task["validation"][m["config_id"]]={"loss":m["pinball"],"n_cells":m["n_cells"],"last_label_date":result["label_end"]}
            event.update(status="completed",completed_at=now(),execution_run_id=result["run_id"],modal_call_id=result["modal_call_id"],wall_seconds=time.perf_counter()-begin)
            flush()
        try:
            if report["research_plan"]:
                plan_record=await remember("skeptic","task_selection_objection",report["research_plan"]["skeptic_objection"])
                report["events"].append({"event":"plan_adapted","chosen_training_origin":origin,"selection":report["research_plan"],"used_critic":await recall("forecast_scientist",plan_record,"Why should this research cycle use a different training origin?")})
            packet,evidence_record=await evidence(question,QUESTIONS[question])
            await execute(INITIAL,"Establish the same two persistence references before choosing alternatives")
            task["scale"]=max(statistics.mean(t["pinball"] for t in report["trials"]),1e-6)
            for step in range(4):
                critic=criticism(task,revealed)
                latest=report["trials"][-1]
                if latest["fallbacks"]:critic["objection"]="The latest method used numerical fallbacks; compare an eligible family before interpreting its score"
                elif latest["coverage"]<.6:critic["objection"]="The latest interval covers fewer than 60% of this tiny training case; investigate calibration and compare persistence"
                elif min(t["pinball"] for t in report["trials"])<=1e-10:critic["objection"]="Persistence already has zero loss on this training case. No candidate can improve it; any further finding is a robustness diagnostic"
                critic["cutoff_check"]="All outcomes end "+label_end+" within the July31 training boundary"
                critic["sample_size_objection"]="One training origin cannot establish temporal generalization"
                result_record=await remember("forecast_scientist","measured_results",{"revealed_trials":report["trials"],"next_uncertainty":critic["objection"]},[evidence_record])
                skeptic_context=await recall("skeptic",result_record,"Which measured trials and limitations should the skeptic inspect?")
                critic_record=await remember("skeptic","criticism",{**critic,"used_result_record":result_record},[result_record])
                used_critic=await recall("forecast_scientist",critic_record,"What objection must guide the next experiment?")
                combined={"method_evidence":packet,"criticism":used_critic}
                selected,decisions=await choose(task,revealed,sampler,renderer,ablation="with_criticism",evidence=combined)
                counterfactual,_=await choose(task,revealed,sampler,renderer)
                blind,_=await choose(task,revealed,sampler,renderer,ablation="no_observation")
                report["events"].append({"event":"scientist_decision","step":step,"selected_config_id":selected,"without_evidence_or_criticism_config_id":counterfactual,"decision_changed_with_context":selected!=counterfactual,"without_results_config_id":blind,"results_changed_choice":counterfactual!=blind,"used_evidence_record_id":evidence_record,"used_critic_record_id":critic_record,"decisions":[{k:v for k,v in d.items() if k!="decision"} for d in decisions],"created_at":now()})
                await execute([selected],"Test "+selected+" in response to "+used_critic["objection"])
                if step==1:
                    packet,evidence_record=await evidence("missingness","Could missingness or coverage explain the measured differences?")
            winner=min(report["trials"],key=lambda r:r["pinball"])
            report.update(status="completed",completed_at=now(),selected_on_training_diagnostic=winner["config_id"],runtime_seconds=time.perf_counter()-started,actual_trials=len(revealed),memory_records=[{k:v for k,v in r.items() if k!="content"} for r in memory_records],memory_api_calls=memory_calls,actual_cross_role_reads=sum(e.get("actual_cross_role_use",False) for e in report["events"]),adaptation_changes=sum(e.get("decision_changed_with_context",False) for e in report["events"]),limitations=["Training-period retrospective demonstration; no generalization claim","Context counterfactual removes evidence and criticism jointly; it does not isolate their separate effects","Same numerical origin is repeatedly evaluated; executions are new but observations are not independent"])
            flush();print("V2_AUTONOMY:"+json.dumps(report),flush=True)
        except Exception as error:
            report.update(status="failed",error_type=type(error).__name__,failed_at=now(),runtime_seconds=time.perf_counter()-started);flush();raise
    return report
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--question",choices=list(QUESTIONS),default="calibration");parser.add_argument("--output",default="artifacts/v2-autonomy");parser.add_argument("--origin",default="2026-07-24");parser.add_argument("--plan");parser.add_argument("--policy-manifest")
    args=parser.parse_args()
    with app.run():asyncio.run(run(args.output,args.question,args.origin,args.plan,args.policy_manifest))
