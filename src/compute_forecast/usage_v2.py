"""Read provider receipts; retain account details privately and publish attributed aggregates."""
from __future__ import annotations
import csv,io,json,math,os,subprocess,time,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.request import urlopen
import modal
from .campaign_v2 import now,write,digest
from .starter_probe import volume
app=modal.App("compute-forecast-v2-usage")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
@app.function(image=image,cpu=.25,memory=512,timeout=120,volumes={"/data":volume,"/public":public})
def retain(identifier,private,summary):
    write(Path("/data/campaign-v2/usage")/(identifier+".json"),private);volume.commit()
    volume.reload()
    exa_receipts=[]
    for r in private.get("exa_search_receipts",[]):
        exa_receipts.append({"kind":"search","cost":r.get("cost_dollars")})
    for p in Path("/data/campaign-v2/evidence").glob("*.json"):
        body=json.loads(p.read_text())
        for r in body.get("responses",[]):
            if r.get("kind")=="recovered_contents":exa_receipts.append({"kind":"contents","cost":r.get("response",{}).get("costDollars")})
    for p in Path("/data/campaign-v2/autonomy").glob("*.json"):
        body=json.loads(p.read_text())
        for r in body.get("private_response",[]):
            exa_receipts.append({"kind":"autonomy_search","cost":r.get("response",{}).get("costDollars")})
    if exa_receipts:
        known=[]
        for r in exa_receipts:
            value=r["cost"].get("total") if isinstance(r["cost"],dict) else r["cost"]
            if isinstance(value,(int,float)) and math.isfinite(value):known.append(value)
        summary["exa"]={"status":"retained_request_receipts","observed_requests":len(exa_receipts),"known_cost_receipts":len(known),"unreported_cost_receipts":len(exa_receipts)-len(known),"gross_reported_cost_usd":sum(known) if known else None,"request_kinds":{kind:sum(r["kind"]==kind for r in exa_receipts) for kind in ("search","contents","autonomy_search")},"scope":"Initial search metadata, retained contents retrieval and retained autonomy responses; not an account invoice or remaining balance"}
    public.reload();write(Path("/public/experimental-v2/usage.json"),summary);public.commit()
    return {"private_receipt_sha256":digest(private),"public_receipt_sha256":digest(summary)}
def collect():
    run_id=uuid.uuid4().hex;private={"run_id":run_id,"collected_at":now()};result={"schema_version":2,"run_id":run_id,"collected_at":now(),"code_sha":os.environ["GITHUB_SHA"],"remaining_credits":None,"remaining_credits_status":"Not exposed by the verified usage APIs; no billing changes made","cost_basis":"provider-reported gross estimated charges before credits; data can lag; not an invoice"}
    try:
        import tinker
        from tinker.types import SessionSearchRequest,OwnSearchOwner
        client=tinker.RestClient();request=SessionSearchRequest(display_name="Compute Forecast v2",owner=OwnSearchOwner())
        sessions=[]
        for _ in range(10):
            page=client.search_sessions(request).result();sessions.extend(page.sessions)
            if page.next_cursor is None:break
            request=request.model_copy(update={"cursor":page.next_cursor})
        identifiers={s.session_id for s in sessions if str(s.display_name).startswith("Compute Forecast v2")}
        private["tinker_sessions"]=[s.model_dump(mode="json") for s in sessions]
        hour=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
        start="2026-11-15T01:00:00Z";end=(hour+timedelta(hours=1)).isoformat().replace("+00:00","Z")
        p=subprocess.run(["tinker","billing","usage",start,end,"--csv","-"],capture_output=True,text=True,timeout=90)
        if p.returncode:raise RuntimeError("Billing CLI refused usage request")
        rows=list(csv.DictReader(io.StringIO(p.stdout)));private["tinker_billing_rows"]=rows
        own=[r for r in rows if r.get("session_id") in identifiers]
        numeric=[float(r["estimated_cost_usd"]) for r in own if r.get("estimated_cost_usd") not in ("",None)]
        result["tinker"]={"status":"provider_receipt_partial" if numeric else "pending_or_no_attributed_usage_rows","attributed_sessions":len(identifiers),"billing_rows":len(own),"gross_reported_cost_usd":sum(numeric) if numeric else None,"reported_token_count":sum(int(float(r.get("token_count") or 0)) for r in own) if own else None,"period_start":start,"period_end":end,"data_lag":True}
    except Exception as error:result["tinker"]={"status":"unavailable","error_type":type(error).__name__,"gross_reported_cost_usd":None}
    def cli(args):
        p=subprocess.run(args,capture_output=True,text=True,timeout=90)
        if p.returncode:return {"available":False,"returncode":p.returncode},None
        body=json.loads(p.stdout);keys=list(body) if isinstance(body,dict) else list(body[0]) if isinstance(body,list) and body else []
        return {"available":True,"schema_fields":keys},body
    for key,args in (("modal_report",["modal","billing","report","--start","2026-11-15","--resolution","h","--json"]),("modal_summary",["modal","billing","summary","--json"]),("modal_rates",["modal","billing","rates","--json"])):
        try:
            meta,body=cli(args);private[key]=body;result[key]=meta
        except Exception as error:result[key]={"available":False,"error_type":type(error).__name__}
    result["modal"]={"status":"schema_requires_verified_attribution" if result["modal_report"].get("available") else "billing_report_unavailable","gross_reported_cost_usd":None}
    modal_rows=private.get("modal_report")
    if isinstance(modal_rows,list):
        own=[r for r in modal_rows if "compute-forecast-v2" in str(r.get("description",""))]
        costs={}
        for r in own:
            try:cost=float(r["cost"])
            except (ValueError,TypeError,KeyError):continue
            if math.isfinite(cost):costs[r["description"]]=costs.get(r["description"],0)+cost
        if costs:result["modal"]={"status":"provider_receipt_partial","gross_reported_cost_usd":sum(costs.values()),"by_app":[{"app":k,"gross_reported_cost_usd":v} for k,v in sorted(costs.items())],"billing_rows":len(own),"data_lag":True}
    evidence=list(Path("inputs").rglob("evidence.json"))
    if evidence:
        ev=json.loads(evidence[0].read_text());private["exa_search_receipts"]=ev["requests"]
        amounts=[]
        for r in ev["requests"]:
            c=r.get("cost_dollars");v=c.get("total") if isinstance(c,dict) else c
            if isinstance(v,(int,float)) and math.isfinite(v):amounts.append(v)
        result["exa"]={"status":"search_receipts_only","search_requests":len(ev["requests"]),"distinct_queries":len({r.get("query") for r in ev["requests"]}),"gross_reported_cost_usd":sum(amounts) if amounts else None,"costed_search_receipts":len(amounts),"additional_contents_and_autonomy_calls_excluded":True}
    receipt=retain.remote(run_id,private,result);result["receipt"]=receipt
    write(Path("artifacts/v2-usage/usage.json"),result);print("V2_USAGE:"+json.dumps(result),flush=True)
    try:
        live=json.loads(urlopen("https://howdymary--compute-forecast-observatory-web.us-east.modal.run/api/experimental",timeout=90).read())
        print("V2_LIVE:"+json.dumps({"source_sha":live.get("source_sha"),"policy_reports":[{"seed":p["seed"],"objective":p["objective"],"mode":p["mode"],"updates":p["actual_optimizer_updates"],"selected_update":p["selected_update"],"scores":[{"policy":c["policy"],"pinball":c["pinball"]} for c in p["comparisons"]]} for p in live.get("policy_reports",[])],"checkpoint_runs":live.get("checkpoint_runs",[]),"autonomy":[{"question":r["question_id"],"status":r["status"],"trials":len(r["trials"]),"new_executions":r["new_executions"],"memory_reads":r.get("actual_cross_role_reads"),"adaptation_changes":r.get("adaptation_changes")} for r in live.get("autonomy_runs",[])],"evaluation_forecasters":sorted([r for r in live.get("forecasting",{}).get("rows",[]) if r["phase"]=="evaluation"],key=lambda r:r["pinball"])[:8],"prospective":live.get("prospective")}),flush=True)
    except Exception as error:print("V2_LIVE_UNAVAILABLE:"+type(error).__name__,flush=True)
@app.local_entrypoint()
def main():collect()
