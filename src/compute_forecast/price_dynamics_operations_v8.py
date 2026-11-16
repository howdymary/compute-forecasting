"""Actual v8 evidence capture and cross-role memory receipts; no new optimization."""
import asyncio,json,os,time,uuid
from datetime import datetime,timezone
from pathlib import Path
import modal
from .price_dynamics_v8 import digest
from .price_dynamics_remote_v8 import image,data,public,encoded,put
from .news_measurement_v8 import capture
app=modal.App("compute-forecast-price-dynamics-operations-v8")
secret=modal.Secret.from_name("compute-forecast-signals-v6",required_keys=["EXA_API_KEY","PAST_API_KEY"])
def now():return datetime.now(timezone.utc).isoformat()
async def memory(study,news):
    import httpx
    ident=uuid.uuid4().hex[:16];aud="cf-v8-"+ident
    actors={r:aud+"-"+r for r in ("researcher","scientist","skeptic")}
    report={"schema_version":8,"study_id":"price-dynamics-v8-memory","namespace":aud,"created_at":now(),"roles":"Bounded deterministic research agents; no model-weight training or general research-intelligence claim","source_sha":os.environ.get("GITHUB_SHA"),"study_sha256":digest(study),"records":[],"reads":[],"calls":[],"decisions":[],"optimizer_updates":0};contents={}
    async with httpx.AsyncClient(timeout=45) as http:
        async def past(method,path,body=None):
            r=await http.request(method,"https://api.past.dev/api/v1"+path,headers={"Authorization":"Bearer "+os.environ["PAST_API_KEY"]},json=body)
            report["calls"].append({"method":method,"endpoint":path.split("/")[1],"status":r.status_code,"at":now()});r.raise_for_status();return r.json()
        await past("PUT","/audiences/"+aud,{"kind":"fixed","name":"V8 forecasting mechanism audit","identities":list(actors.values())})
        async def write(role,value):
            rid=aud+"-"+str(len(contents));contents[rid]=value
            result=await past("POST","/ingest",{"id":rid,"identity":actors[role],"audience":aud,"timestamp":now(),"label":"V8 "+role,"content":json.dumps({"record_id":rid,"content":value})})
            complete=False
            for _ in range(40):
                status=await past("GET","/ingest/"+result["ingestionId"])
                if status.get("status")=="completed":complete=True;break
                if status.get("status")=="failed":break
                await asyncio.sleep(2)
            report["records"].append({"record_id":rid,"role":role,"author":actors[role],"ingestion_id":result["ingestionId"],"ingestion_completed":complete,"content_sha256":digest(value),"content":value});return rid
        async def read(role,rid):
            returned=[];verified=False
            for _ in range(5):
                response=await past("POST","/recall",{"query":rid+" Retrieve this exact research audit record to decide my next task.","identity":actors[role],"level":"medium"})
                returned=sorted({s["sourceId"] for item in response.get("results",[]) for s in item.get("sources",[])})
                if rid in returned:verified=True;break
                await asyncio.sleep(2)
            author=next(r["role"] for r in report["records"] if r["record_id"]==rid)
            report["reads"].append({"reader":actors[role],"reader_role":role,"writer_role":author,"required_source_id":rid,"returned_source_ids":returned,"verified_cross_role_use":verified and author!=role,"canonical_fallback":not verified,"consumed_content_sha256":digest(contents[rid])})
            return contents[rid],verified
        facts={"hypothesis":"Collector composition and repricing may explain median changes, but stable-identity target reconstruction must precede replay","audit":study["target_audit"],"news_measurement":{"cap":news.get("discovery",{}).get("requested_cap"),"coverage":news.get("discovery",{}).get("collection_coverage")},"sources":["https://github.com/mahiuchun/gpu-price","https://github.com/ianalin123/gpu-value-scientist"],"information_class":"Current retrospective method audit, not a historical forecast feature"}
        r=await write("researcher",facts);fact,ok=await read("scientist",r)
        failed=[x["series_id"] for x in fact["audit"] if x["last_quote_basket_exact_days"]!=x["days"] or x["missing_identity_rows"] or x["same_timestamp_identity_collisions"]]
        decision={"decision":"keep_replay_gated_where_target_or_identity_fails" if failed else "allow_verified_same_membership_repricing_only","gated_series":failed,"used_record_id":r,"recall_verified":ok,"experiment":"Fixed six-arm study; no post-result retuning","paired_results":study["pairs"]}
        s=await write("scientist",decision);chosen,ok=await read("skeptic",s)
        criticism={"objection":"Reused historical origins cannot establish future accuracy; fallback equality is not evidence that replay's modeling mechanism works","observed_replay_gate":chosen["decision"],"decision":"Do not promote a retrospective winner; require fresh compatible aggregate commitments","used_record_id":s,"recall_verified":ok,"changes_to_frozen_studies":0}
        k=await write("skeptic",criticism);critic,ok=await read("scientist",k)
        final={"next_decision":critic["decision"],"changed":"Future promotion remains gated; target reconstruction is surfaced in the UI instead of labeling fallback equality a successful replay result","unchanged":"Six-arm configuration, official export, selectors, signals-v6 and evaluation gates","used_record_id":k,"recall_verified":ok}
        await write("scientist",final)
        await read("researcher",k)
        report["decisions"]=[decision,criticism,final];report["final_decision"]=final["next_decision"];report["accuracy_effect_established"]=False
    return report
@app.function(image=image,cpu=1,memory=1024,timeout=600,max_containers=1,volumes={"/data":data,"/public":public},secrets=[secret])
def run():
    root=Path("/public/price-dynamics-v8");public.reload()
    study=json.loads((root/"index.json").read_bytes())
    old=json.loads((root/"news.json").read_bytes()) if (root/"news.json").exists() else None
    previous=json.loads((root/"memory.json").read_bytes()) if (root/"memory.json").exists() else None
    news=old if old else capture(Path("/data/price-dynamics-v8/evidence"),old);data.commit()
    try:m=previous if previous and previous.get("study_sha256")==digest(study) else asyncio.run(memory(study,news))
    except Exception as e:m={"schema_version":8,"status":"failed","error":type(e).__name__,"detail":str(e)[:300],"reads":[],"final_decision":"No successful recall is claimed; use immutable audit artifacts"}
    for read in m.get("reads",[]):
        ids=read.get("returned_source_ids",[]);read["out_of_namespace_ids_not_published"]=sum(not x.startswith(m["namespace"]) for x in ids)
        read["returned_source_ids"]=[x for x in ids if x.startswith(m["namespace"])]
        read["delivery"]="Required source ID verified in past.dev response; exact numerical payload resolved from canonical record by that returned ID" if read.get("verified_cross_role_use") else "Explicit canonical fallback, not a successful recall"
    for name,value in (("news",news),("memory",m)):
        put(root/(name+"-artifacts")/(digest(value)+".json"),value);tmp=root/(name+".pending");tmp.write_bytes(encoded(value));tmp.replace(root/(name+".json"))
    public.commit();return {"news":news,"memory":m}
def main():
    with app.run():result=run.remote()
    out=Path("artifacts/price-dynamics-v8-operations");out.mkdir(parents=True,exist_ok=True)
    for name,value in result.items():put(out/(name+".json"),value)
    print("V8_OPERATIONS:"+json.dumps(result),flush=True)
if __name__=="__main__":main()
