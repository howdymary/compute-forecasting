"""Real bounded research roles using Exa, Tinker and scoped past.dev memory.

This is CURRENT methodological research, never historical benchmark input.
No present-day page or memory is backdated to a market forecast origin.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import os
import time
import uuid
from datetime import datetime,timezone
from pathlib import Path

MODEL="Qwen/Qwen3.5-4B"
QUERIES={
 "normalization":"GPU rental price index methodology provider configuration normalization Silicon Data SemiAnalysis",
 "composition":"GPU rental pricing index methodology provider mix configuration composition advertised rates",
 "measurement":"GPU pricing index advertised rental offers versus transaction prices methodology"}
DIAGNOSTICS={
 "aggregation_audit":"Compare official pooled skill with mean, median and geometric per-series skill.",
 "coverage_audit":"Inspect empirical central-80-percent interval coverage by official starter method.",
 "horizon_audit":"Inspect pinball and pooled skill separately at horizons 1, 3 and 7 days."}
OBJECTIONS={
 "aggregation_risk":"Pooled and equally weighted series summaries answer different questions. Retain both; do not infer broad gains from a pooled improvement.",
 "small_sample":"One forecast origin is one temporal replication. Series and horizons are dependent, so this diagnostic cannot establish generalization.",
 "historical_availability":"These pages were retrieved now. Publication dates do not prove historical content availability; keep this evidence outside historical benchmark observations."}

def now():return datetime.now(timezone.utc).isoformat()
def public_evidence(value):
    if isinstance(value,list):return [public_evidence(v) for v in value]
    if not isinstance(value,dict):return value
    output={}
    for key,item in value.items():
        if key=="recall":
            output[key]={"asOf":item.get("asOf"),"results":[{"id":r.get("id"),"source_ids":[s["sourceId"] for s in r.get("sources",[])],"content_sha256":hashlib.sha256(r["content"].encode()).hexdigest(),"body":"Retained privately in past.dev; omitted from public artifact"} for r in item.get("results",[])]}
        elif key in ("highlights","excerpts"):
            output[key+"_sha256"]=hashlib.sha256(json.dumps(item,sort_keys=True).encode()).hexdigest()
        else:output[key]=public_evidence(item)
    return output

def save(path,value):path.write_text(json.dumps(public_evidence(value),indent=2,allow_nan=False)+"\n")

def numerical_diagnostic(name,report):
    if report["is_synthetic"] or report["cutoff"]!="2026-07-24" or not report["refusal_check_passed"]:
        raise ValueError("REFUSED: research diagnostic requires the verified training-origin source")
    output={"tool":name,"source_run_id":report["run_id"],"source_code_sha":report["code_sha"],"dataset_sha256":report["archive_sha256"],"forecast_origin":"2026-07-24","information_scope":"current_research_on_completed_training_experiments","calculated_at":now(),"methods":{}}
    for method in ("last_value","last_value_empirical","drift","seasonal_naive"):
        scored=report["reports"]["report_"+method+".json"]
        if name=="aggregation_audit":
            value={key:scored["overall"].get(key) for key in ("pinball","skill_pooled","skill_mean_of_series","skill_median_of_series","skill_geomean","n_cells")}
        elif name=="coverage_audit":
            value={"coverage":scored["overall"]["coverage"],"n_cells":scored["overall"]["n_cells"]}
        elif name=="horizon_audit":
            value={str(h):{key:scored["by_horizon"][str(h)].get(key) for key in ("pinball","baseline_pinball","skill_pooled","n_cells")} for h in (1,3,7)}
        else:raise ValueError("Unvalidated numerical tool")
        output["methods"][method]=value
    return output

def completed_forecast_experiment(config_id,grid):
    import csv,io,math,re
    import modal
    from .representation_study import CONFIGS,PACK_SHA256
    if config_id not in {c["id"] for c in CONFIGS} or grid["final_period_opened"] is not False:
        raise ValueError("REFUSED: unvalidated experiment or final-period data")
    run=next(r for r in grid["origins"] if r["origin"]=="2026-07-24")
    if run["status"]!="completed" or run["is_synthetic"] or run["dataset_sha256"]!=PACK_SHA256 or run["label_end"]!="2026-07-31" or not re.fullmatch(r"[0-9a-f]{32}",run["run_id"]):
        raise ValueError("REFUSED: invalid training-period experiment source")
    result=next(r for r in run["results"] if r["config_id"]==config_id)
    file="cells_"+config_id+".csv"
    digest=next(a["sha256"] for a in run["artifacts"] if a["path"]==file)
    volume=modal.Volume.from_name("compute-forecast-data",create_if_missing=False)
    raw=b"".join(volume.read_file("/representation/"+run["run_id"]+"/"+file))
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError("REFUSED: cached experiment artifact digest mismatch")
    losses=[]
    for row in csv.DictReader(io.StringIO(raw.decode())):
        try:value=float(row["loss"])
        except (ValueError,TypeError):continue
        if math.isfinite(value):losses.append(value)
    exact=sum(losses)/len(losses)
    if len(losses)!=result["exact_metrics"]["n_cells"] or abs(exact-result["exact_metrics"]["pinball"])>1e-12:
        raise ValueError("REFUSED: cached official loss could not be reproduced")
    references={r["config_id"]:r["exact_metrics"]["pinball"] for r in run["results"] if r["config_id"] in ("last_value","last_value_empirical","drift","seasonal_naive")}
    best_reference=min(references.values())
    return {"tool":"completed_forecast_experiment","config_id":config_id,"config":next(c for c in CONFIGS if c["id"]==config_id),"execution_mode":"reveal_completed_officially_scored_experiment","cache_hit":True,"new_numerical_execution":False,"source_run_id":run["run_id"],"source_code_sha":grid["code_sha"],"dataset_sha256":PACK_SHA256,"forecast_origin":"2026-07-24","last_label_date":"2026-07-31","information_scope":"current_research_on_training_period_only","retrieved_at":now(),"official_cell_file_sha256":digest,"pinball":exact,"n_cells":len(losses),"by_horizon":{str(h):result["by_horizon"][str(h)] for h in (1,3,7)},"fixed_baseline_losses":references,"loss_delta_vs_best_fixed_reference":exact-best_reference,"hypothesis_status":"supported_on_this_case" if exact<best_reference else "not_supported_on_this_case","limitation":"One completed training origin; this is not a new independent experiment or a generalization claim."}

async def run(source,output,grid=None):
    import httpx
    import tinker
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import Decision,DecisionRenderer,sample_decision
    run_id=uuid.uuid4().hex; audience="cf-methods-"+run_id[:24]
    actors={r:"cf-"+run_id+"-"+r for r in ("evidence_researcher","forecast_scientist","skeptic")}
    events=[];calls=[];out=Path(output);out.mkdir(parents=True,exist_ok=True)
    manifest={"schema_version":"1","run_id":run_id,"scope":"current_research","research_kind":"forecast_configuration_selection" if grid else "scoring_audit","github_run_id":os.environ.get("GITHUB_RUN_ID"),"phase":"training_diagnostic_only","market_cutoff":None,"created_at":now(),"code_sha":os.environ.get("GITHUB_SHA"),"model":MODEL,"audience":audience,"actors":actors,"events":events,"api_calls":calls,"historical_benchmark_input":False,"memory_performance_gain_claimed":False,"status":"running"}
    def flush():save(out/"research-loop.json",manifest)
    flush()
    service=tinker.ServiceClient(display_name="Compute Forecast: evidence scientist skeptic")
    sampler=await service.create_sampling_client(base_model=MODEL)
    tokenizer=sampler.get_tokenizer()
    renderer=renderers.get_renderer(model_info.get_recommended_renderer_name(MODEL),tokenizer)
    decisions=DecisionRenderer(renderer)
    async with httpx.AsyncClient(timeout=60) as client:
        async def request(method,path,payload=None):
            start=time.perf_counter()
            response=await client.request(method,"https://api.past.dev/api/v1"+path,json=payload,headers={"Authorization":"Bearer "+os.environ["PAST_API_KEY"]})
            calls.append({"service":"past.dev","method":method,"path":path,"status_code":response.status_code,"runtime_seconds":time.perf_counter()-start,"created_at":now()});flush()
            response.raise_for_status();return response.json()
        await request("PUT","/audiences/"+audience,{"kind":"fixed","name":"Compute Forecast current methodological research "+run_id,"identities":list(actors.values())})
        async def write(role,kind,content,parents=()):
            source_id="cf-"+run_id+"-"+str(len(events))+"-"+role
            record={"record_id":source_id,"author":actors[role],"role":role,"kind":kind,"scope":"current_research","audience":audience,"created_at":now(),"parent_record_ids":list(parents),"content":content,"historical_benchmark_input":False}
            encoded=json.dumps(record,sort_keys=True)
            response=await request("POST","/ingest",{"id":source_id,"identity":actors[role],"audience":audience,"timestamp":record["created_at"],"label":"Compute Forecast / "+role+" / "+kind,"content":encoded})
            ingestion=response.get("ingestionId");parsed=uuid.UUID(ingestion)
            if parsed.int==0:raise RuntimeError("Invalid ingestion ID")
            event={"event":"write","role":role,"source_id":source_id,"ingestion_id":ingestion,"record":record,"content_sha256":hashlib.sha256(encoded.encode()).hexdigest(),"created_at":now()};events.append(event);flush()
            for attempt in range(90):
                status=await request("GET","/ingest/"+ingestion)
                if status.get("status")=="completed":
                    event["ingestion_status"]="completed";event["completion_response"]=status;flush();return source_id
                if status.get("status")=="failed":raise RuntimeError("Memory ingestion failed")
                await asyncio.sleep(2)
            raise RuntimeError("Memory ingestion did not complete within 180 seconds")
        async def read(role,query,required_source):
            for attempt in range(5):
                response=await request("POST","/recall",{"query":query,"identity":actors[role],"level":"medium"})
                source_ids=sorted({s["sourceId"] for r in response.get("results",[]) for s in r.get("sources",[])})
                if required_source in source_ids:
                    event={"event":"read","role":role,"query":query,"required_source_id":required_source,"returned_source_ids":source_ids,"recall":response,"created_at":now()};events.append(event);flush();return event
                await asyncio.sleep(2)
            raise RuntimeError("Cross-agent source was not returned by actual recall")
        async def choose(role,question,options,read_events):
            context=[{"record_ids":e["returned_source_ids"],"documents":[r["content"] for r in e["recall"]["results"]]} for e in read_events]
            decision=Decision(question+"\nActual recalled research documents:\n"+json.dumps(context),list(options.items()))
            distribution=await sample_decision(sampler,decisions.render(decision))
            if set(distribution)!=set(options):raise RuntimeError("Unexpected bounded model action")
            selected=max(options,key=lambda key:distribution[key])
            event={"event":"decision","role":role,"model":MODEL,"selected_action":selected,"probabilities":distribution,"used_memory_source_ids":sorted({sid for e in read_events for sid in e["returned_source_ids"]}),"created_at":now()};events.append(event);flush();return selected,event
        async def choose_forecast(read_events,excluded=()):
            from .representation_study import CONFIGS
            available=[c for c in CONFIGS if c["id"] not in excluded]
            families={c["space"]+"__"+c["aux"]:"Ridge target "+c["space"]+"; auxiliary features "+c["aux"] for c in available}
            family,_=await choose("forecast_scientist","Choose the next model family to investigate using the recalled method evidence or criticism. Only completed training-period experiments will be revealed.",families,read_events)
            options={c["id"]:"Lookback "+str(c["days"])+" calendar days; alpha "+str(c["alpha"]) for c in available if c["space"]+"__"+c["aux"]==family}
            return await choose("forecast_scientist","Choose one untested configuration in family "+family+". This requests a cached, actual official-scored experiment; no unseen score is supplied.",options,read_events)
        try:
            question=await write("forecast_scientist","unresolved_question",{"hypothesis":"Representation and provider composition may change forecast conclusions. Choose a configuration to investigate, inspect its measured training-period result, then use criticism to choose a followup." if grid else "Representation and provider composition may change forecast conclusions. Inspect which measurement or scoring audit is most useful.","allowed_tools":"24 validated Ridge configurations across level/log targets, target-only/raw/fixed-basket features, 28/56-day windows and alpha 1/100" if grid else DIAGNOSTICS,"scope_note":"Current methods research only. No current market-price news may enter historical forecasts."})
            prior=await read("evidence_researcher","What unresolved Compute Forecast methodological question should I research, and which diagnostic tools are allowed?",question)
            query_id,query_decision=await choose("evidence_researcher","Select the most useful methodological search query. Search must not seek post-cutoff GPU prices.",QUERIES,[prior])
            started=time.perf_counter()
            response=await client.post("https://api.exa.ai/search",headers={"x-api-key":os.environ["EXA_API_KEY"]},json={"query":QUERIES[query_id],"type":"auto","numResults":4,"includeDomains":["silicondata.com","semianalysis.com"],"contents":{"highlights":True}})
            response.raise_for_status();exa=response.json()
            sources=[{"title":r.get("title"),"url":r["url"],"published_at":r.get("publishedDate"),"retrieved_at":now(),"highlights":[" ".join(h.split()[:18]) for h in r.get("highlights",[])[:1]],"historical_eligibility":False} for r in exa.get("results",[])]
            if not sources:raise RuntimeError("Exa returned no methodological evidence")
            exa_evidence={"query":QUERIES[query_id],"request_id":exa.get("requestId"),"response_sha256":hashlib.sha256(response.content).hexdigest(),"sources":sources,"cost_dollars":exa.get("costDollars"),"runtime_seconds":time.perf_counter()-started,"scope":"current_research","note":"Retrieved now, not historical benchmark features. Provider/configuration normalization has established precedents."}
            calls.append({"service":"Exa","status_code":response.status_code,"request_id":exa.get("requestId"),"cost_dollars":exa.get("costDollars"),"created_at":now()})
            evidence=await write("evidence_researcher","dated_methodological_evidence",exa_evidence,[question])
            recalled=await read("forecast_scientist","What methodological evidence and normalization precedents did the evidence researcher find for Compute Forecast?",evidence)
            if grid:
                action,decision=await choose_forecast([recalled])
                diagnostic=completed_forecast_experiment(action,grid)
            else:
                action,decision=await choose("forecast_scientist","Choose one deterministic numerical audit to run on the verified July training-origin reports. Current pages inform the methodological question, not numerical forecasts.",DIAGNOSTICS,[recalled])
                diagnostic=numerical_diagnostic(action,source)
            result=await write("forecast_scientist","completed_numerical_experiment",diagnostic,[evidence])
            criticism_input=await read("skeptic","What did the forecast scientist's completed numerical audit find, and which source run supplied its numbers?",result)
            objection,critic_decision=await choose("skeptic","Select the most consequential limitation to retain before the next experiment. Do not invent errors or performance gains.",OBJECTIONS,[criticism_input])
            criticism=await write("skeptic","criticism",{"objection_id":objection,"criticism":OBJECTIONS[objection],"result_record_id":result},[result])
            critic_memory=await read("forecast_scientist","What criticism did the skeptic write about my completed experiment, and how should it affect the next diagnostic?",criticism)
            if grid:
                followup,next_decision=await choose_forecast([recalled,critic_memory],excluded=[action])
                next_result=completed_forecast_experiment(followup,grid)
            else:
                remaining={key:value for key,value in DIAGNOSTICS.items() if key!=action}
                followup,next_decision=await choose("forecast_scientist","Choose the next untested diagnostic after reading the skeptic. Both audits are valid; make the decision from the recalled objection and evidence.",remaining,[recalled,critic_memory])
                next_result=numerical_diagnostic(followup,source)
            final=await write("forecast_scientist","criticism_informed_followup",{"selected_action":followup,"used_criticism_source_id":criticism,"numerical_result":next_result,"no_performance_gain_claimed":True},[criticism,result,evidence])
            writers={e["role"] for e in events if e["event"]=="write"};readers={e["role"] for e in events if e["event"]=="read"}
            used={sid for e in events if e["event"]=="decision" for sid in e["used_memory_source_ids"]}
            if len(writers)<2 or len(readers)<2 or criticism not in used or evidence not in used:
                raise RuntimeError("Memory sponsor evidence conditions were not met")
            manifest.update(status="completed",completed_at=now(),writers=sorted(writers),readers=sorted(readers),actual_cross_agent_use=True,final_record_id=final,exa_evidence=exa_evidence)
        except Exception as error:
            manifest.update(status="failed",error_type=type(error).__name__,completed_at=now());flush();raise
    flush()
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
        compact={key:manifest[key] for key in ("run_id","status","scope","model","audience","writers","readers","actual_cross_agent_use","final_record_id","historical_benchmark_input","memory_performance_gain_claimed")}
        compact["decisions"]=[{k:v for k,v in e.items() if k!="probabilities"} for e in events if e["event"]=="decision"]
        f.write("# Actual evidence → experiment → criticism → next decision\n\n")
        text=json.dumps(compact,indent=2)
        for start in range(0,len(text),3000):f.write("~~~json\n"+text[start:start+3000]+"\n~~~\n\n")

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--training-report",required=True);parser.add_argument("--grid-report");parser.add_argument("--output",default="artifacts/current-research")
    args=parser.parse_args();asyncio.run(run(json.loads(Path(args.training_report).read_text()),args.output,json.loads(Path(args.grid_report).read_text()) if args.grid_report else None))
