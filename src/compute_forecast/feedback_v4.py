"""Registered retrospective feedback/evidence interventions on frozen samplers."""
from __future__ import annotations
import asyncio,hashlib,json,os,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from .review_v4 import digest,encoded,read_archive,one
def stamp():return datetime.now(timezone.utc).isoformat()
def padded(value,n=900):return str(value)[:n].ljust(n)
def metrics(traces):
    cases=[c for t in traces for c in t["cases"]]
    return {"pinball":sum(c["loss"] for c in cases)/len(cases),"coverage":sum(c["covered"] for c in cases)/len(cases),"mean_width":sum(c["width"] for c in cases)/len(cases),"n_cells":len(cases),"n_tasks":len(traces),"n_origins":len({t["origin"] for t in traces})}
async def evidence_and_memory(private_dir):
    import httpx
    root=Path(private_dir);root.mkdir(parents=True,exist_ok=True);run=uuid.uuid4().hex
    actors={r:"cf-v4-"+run+"-"+r for r in ("researcher","scientist","skeptic")};audience="cf-v4-"+run
    contents={}
    report={"run_id":run,"sources":[],"requests":[],"memory_records":[],"memory_reads":[],"memory_calls":[]};texts={}
    async with httpx.AsyncClient(timeout=60) as client:
        for kind,query,domains in [
            ("relevant","Primary research explaining rolling-origin validation and calibration versus sharpness for selecting probabilistic forecasting methods",["otexts.com","scikit-learn.org","academic.oup.com","proceedings.neurips.cc"]),
            ("irrelevant","Official documentation about HTTP connection pooling and caching static assets to reduce web application latency",["www.python-httpx.org","modal.com"])]:
            started=time.perf_counter();response=await client.post("https://api.exa.ai/search",headers={"x-api-key":os.environ["EXA_API_KEY"]},json={"query":query,"type":"auto","numResults":3,"includeDomains":domains,"contents":{"highlights":True}})
            response.raise_for_status();body=response.json();raw=encoded(body);(root/(kind+"-exa.json")).write_bytes(raw)
            texts[kind]="\n".join(x.get("title","")+"\n"+"\n".join(x.get("highlights",[])) for x in body.get("results",[]))
            if not texts[kind].strip():raise ValueError("Empty evidence condition")
            ids=[]
            for x in body.get("results",[]):
                sid=digest({"url":x.get("url"),"highlights":x.get("highlights")})[:20];ids.append(sid);report["sources"].append({"source_id":sid,"condition":kind,"url":x.get("url"),"title":x.get("title"),"retrieved_at":stamp(),"content_sha256":digest({"text":x.get("text"),"highlights":x.get("highlights")})})
            report["requests"].append({"kind":kind,"query":query,"request_id":body.get("requestId"),"response_sha256":hashlib.sha256(raw).hexdigest(),"source_ids":ids,"runtime_seconds":time.perf_counter()-started,"cost_dollars":body.get("costDollars"),"historical_market_input":False})
        async def past(method,path,payload=None):
            response=await client.request(method,"https://api.past.dev/api/v1"+path,headers={"Authorization":"Bearer "+os.environ["PAST_API_KEY"]},json=payload)
            report["memory_calls"].append({"method":method,"path_kind":path.split("/")[1],"status_code":response.status_code,"at":stamp()});response.raise_for_status();return response.json()
        available=True
        try:await past("PUT","/audiences/"+audience,{"kind":"fixed","name":"Compute Forecast v4 interventions","identities":list(actors.values())})
        except Exception as e:available=False;report["memory_setup_error"]=type(e).__name__
        async def write(role,content):
            identifier="cf-v4-"+run+"-"+str(len(report["memory_records"]));record={"record_id":identifier,"author":actors[role],"role":role,"created_at":stamp(),"content_sha256":digest(content),"historical_market_input":False}
            (root/(identifier+".json")).write_bytes(encoded({"record":record,"content":content}))
            if available:
                try:
                    response=await past("POST","/ingest",{"id":identifier,"identity":actors[role],"audience":audience,"timestamp":record["created_at"],"label":"Compute Forecast v4 "+role,"content":json.dumps({"record_id":identifier,"role":role,"content":content})})
                    record["ingestion_id"]=response["ingestionId"]
                    for _ in range(40):
                        result=await past("GET","/ingest/"+record["ingestion_id"])
                        if result.get("status")=="completed":record["ingestion_completed"]=True;break
                        if result.get("status")=="failed":raise RuntimeError("Memory ingestion failed")
                        await asyncio.sleep(2)
                except Exception as e:record["error_type"]=type(e).__name__
            contents[identifier]=content;report["memory_records"].append(record);return identifier
        async def read(role,required,question):
            item={"reader":actors[role],"required_source_id":required,"actual_cross_role_use":False}
            if available:
                try:
                    for _ in range(5):
                        response=await past("POST","/recall",{"query":required+" "+question,"identity":actors[role],"level":"medium"})
                        ids=sorted({s["sourceId"] for r in response.get("results",[]) for s in r.get("sources",[])})
                        item["returned_source_ids"]=ids
                        if required in ids:item["actual_cross_role_use"]=True;break
                        await asyncio.sleep(2)
                except Exception as e:item["error_type"]=type(e).__name__
            item["fallback"]="Verified canonical authored text used if required recall absent" if not item["actual_cross_role_use"] else None
            report["memory_reads"].append(item)
            return contents[required]
        researcher=await write("researcher",{"relevant":texts["relevant"],"sources":report["sources"]});skeptic_context=await read("skeptic",researcher,"What evidence and limitations should the skeptic inspect?")
        objection="A validation improvement may not transfer. Compare method families, preserve persistence, examine interval width with coverage, and do not select using later outcomes."
        skeptic=await write("skeptic",{"objection":objection,"used_source":researcher,"inspected_source_ids":[s["source_id"] for s in skeptic_context["sources"]]});critic_context=await read("scientist",skeptic,"What criticism should influence selection?")
        scientist_context=await read("scientist",researcher,"Which methodological evidence should enter the registered relevant condition?")
        texts["relevant"]=scientist_context["relevant"];texts["criticism"]=critic_context["objection"]
        scientist=await write("scientist",{"decision":"Use the registered six-condition comparison without changing the fixed candidate pool or chooser","used_sources":[researcher,skeptic]})
        await read("researcher",scientist,"Which registered comparison will use the methodological evidence?")
        report["actual_cross_role_reads"]=sum(r["actual_cross_role_use"] for r in report["memory_reads"]);report["memory_available"]=available
    return texts,report
async def choose_condition(task,revealed,sampler,renderer,condition,texts):
    from .policy_v2 import REGISTRY,menu,options_for,observation,criticism
    from tinker_cookbook.recipes.decisions import Decision,sample_decision
    remaining=[c["id"] for c in REGISTRY if c["id"] not in revealed];prefix=();records=[]
    while True:
        prefix,groups=menu(remaining,prefix)
        if len(groups)==1 and len(groups[0][1])==1:return groups[0][1][0],records
        visible=observation(task,revealed)
        if condition=="feedback_hidden":visible["observed_trials"]=[{k:v for k,v in x.items() if k!="relative_validation_pinball"} for x in visible["observed_trials"]]
        prompt="Choose the next untested forecast experiment under six total trials. Only supplied past information is available. Some conditions omit scores. The final chooser uses true matured validation; future outcomes are hidden.\n"+json.dumps({"state":visible,"menu_path":list(prefix)},sort_keys=True)
        packet=None
        if condition=="relevant_evidence":packet=texts["relevant"]
        elif condition=="irrelevant_evidence":packet=texts["irrelevant"]
        elif condition=="relevant_criticism":packet=texts["criticism"]+"\n"+json.dumps(criticism(task,revealed),sort_keys=True)
        elif condition=="neutral_text":packet="Formatting control. This passage provides no recommendation about forecast methods, numerical scores or selection."
        if packet is not None:prompt+="\n"+json.dumps({"method_note":padded(packet)})
        decision=Decision(prompt,options_for(groups));started=time.perf_counter();distribution=await sample_decision(sampler,renderer.render(decision))
        if set(distribution)!={g[0] for g in groups} or abs(sum(distribution.values())-1)>1e-6:raise ValueError("Invalid action distribution")
        chosen=max(distribution,key=distribution.get)
        records.append({"stage":list(prefix),"distribution":distribution,"selected":chosen,"runtime_seconds":time.perf_counter()-started,"packet_sha256":digest(padded(packet)) if packet is not None else None,"packet_characters":900 if packet is not None else 0,"prompt_characters":len(prompt)})
        ids=dict(groups)[chosen]
        if len(ids)==1:return ids[0],records
        prefix=(*prefix,chosen)
async def run(raw_archive,private_dir,output):
    from .policy_v2 import make_tasks,finish
    from .prospective_panel_v4 import policy_clients
    config=json.loads(Path("configs/review-v4-experiments.json").read_bytes())["evidence"]
    archive,_=read_archive(raw_archive);_,grid=one(archive,"/grid.json");tasks,_=make_tasks(grid);tasks=[t for t in tasks if t["phase"]=="evaluation"]
    if len(tasks)!=4:raise ValueError("Retrospective intervention cohort changed")
    texts,provenance=await evidence_and_memory(private_dir);samplers,renderer=await policy_clients();started=time.perf_counter();semaphore=asyncio.Semaphore(3)
    async def one_episode(policy,condition,task):
        async with semaphore:
            revealed=["last_value","last_value_empirical"];steps=[]
            for _ in range(4):
                c,records=await choose_condition(task,revealed,samplers[policy],renderer,condition,texts);revealed.append(c);steps.extend(records)
            result=finish(task,revealed);return {"policy":policy,"condition":condition,"task_id":task["task_id"],"trace":result,"decisions":steps}
    jobs=[one_episode(policy,condition,t) for policy in config["policies"] for condition in config["conditions"] for t in tasks]
    outputs=await asyncio.wait_for(asyncio.gather(*jobs),timeout=config["wall_seconds"])
    calls=sum(len(o["decisions"]) for o in outputs)
    if calls>config["max_inferences"]:raise ValueError("Registered inference ceiling exceeded")
    results=[]
    for policy in config["policies"]:
        primary={o["task_id"]:o for o in outputs if o["policy"]==policy and o["condition"]=="feedback_only"}
        for condition in config["conditions"]:
            variants=[o for o in outputs if o["policy"]==policy and o["condition"]==condition];traces=[o["trace"] for o in variants];m=metrics(traces)
            results.append({"policy":policy,"condition":condition,**m,"changed_action_sequences":sum(o["trace"]["revealed"]!=primary[o["task_id"]]["trace"]["revealed"] for o in variants),"changed_reveal_sets":sum(set(o["trace"]["revealed"])!=set(primary[o["task_id"]]["trace"]["revealed"]) for o in variants),"changed_terminal_choices":sum(o["trace"]["selected_config_id"]!=primary[o["task_id"]]["trace"]["selected_config_id"] for o in variants),"delta_vs_feedback_only":m["pinball"]-metrics([o["trace"] for o in primary.values()])["pinball"]})
    public={"schema_version":4,"study_id":"feedback-factorial-v4","status":"completed","classification":"Additional retrospective interventions on three previously inspected dates; not independent forecasting validation","registered_config_sha256":digest(config),"source_sha":os.environ.get("GITHUB_SHA"),"created_at":stamp(),"provenance":provenance,"results":results,"traces":outputs,"actual_sampler_calls":calls,"new_optimizer_updates":0,"fresh_numerical_executions":0,"cached_result_reveals":len(outputs)*6,"runtime_seconds":time.perf_counter()-started,"cost_usd":None,"limitations":["Four dependent tasks; prompt interventions are descriptive on this reused cohort","Packet characters are controlled; token counts can differ","Current methodological evidence never becomes a historical market feature","New sampler/package behavior can differ from archived inference; original results remain frozen"]}
    from .public_results import private_guard
    private_guard(public);Path(output).write_bytes(encoded(public));return public
