"""Read-only provider accounting. No searches, inference, training or Modal workers."""
import datetime as dt,hashlib,json,os,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from providers import http,cli
from supervisor import check_integrity
check_integrity();out=ROOT/"artifacts/phase3/budget_inspect_001";out.mkdir(parents=True,exist_ok=True);now=dt.datetime.now(dt.timezone.utc);r={"observed_at":now.isoformat(),"source_sha":os.environ["GITHUB_SHA"],"billable_work_started":False,"historical_holds_unchanged":True,"allocation_renewed":False,"credit_purchases_or_setting_changes":False,"desktop_balance_refresh":"Unavailable: native surface reported locked Mac.","providers":{}}
try:
 raw=cli("modal","billing","summary","--json");a=json.loads(raw);r["providers"]["modal"]={"financial_scalars":{k:v for k,v in a.items() if isinstance(v,(int,float,bool)) and any(s in k.lower() for s in ["cost","credit","spend","balance","limit","charge"])},"response_sha256":hashlib.sha256(raw.encode()).hexdigest(),"scope":"Account-wide gross usage, not attributed CodeGarden spend. No release of unresolved holds or new worker."}
except Exception as e:r["providers"]["modal"]={"read_error":type(e).__name__,"balance_unknown":True}
try:
 a=http("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"]);r["providers"]["past"]={"balance_left":a["balance"]["left"],"source":"Authenticated GET /api/v1/usage; no recall/ingest request."}
except Exception as e:r["providers"]["past"]={"read_error":type(e).__name__,"balance_unknown":True}
try:
 import tinker
 client=tinker.RestClient();end=now.replace(minute=0,second=0,microsecond=0);begin=end.replace(hour=0)
 usage=client.get_billing_usage(starting_on=begin,ending_before=end).result().model_dump(mode="json");events=usage.get("events",[])
 costs=[x.get("estimated_cost_usd") for x in events if isinstance(x,dict)]
 storage=client.get_current_checkpoint_storage_usage().result().model_dump(mode="json")
 r["providers"]["tinker"]={"begin":begin.isoformat(),"ending_before":end.isoformat(),"event_rows":len(events),"estimated_gross_cost_usd":sum(x for x in costs if isinstance(x,(int,float))),"unpriced_rows":sum(x is None for x in costs),"cost_data_through":usage.get("cost_data_through"),"storage_financial_scalars":{k:v for k,v in storage.items() if isinstance(v,(int,float,bool))},"usage_response_sha256":hashlib.sha256(json.dumps(usage,sort_keys=True).encode()).hexdigest(),"balance_unknown":True,"scope":"Read-only RestClient billing/storage metadata; no ServiceClient, sampler, training client or checkpoint creation. Usage can lag hours and is not prepaid balance."}
except Exception as e:r["providers"]["tinker"]={"read_error":type(e).__name__,"balance_unknown":True}
r["providers"]["exa"]={"balance_unknown":True,"read_status":"No documented regular-key prepaid-balance endpoint available; separate admin service credentials not assumed. No billable search started."}
r["official_docs"]=["https://modal.com/docs/guide/billing","https://modal.com/docs/sdk/py/releases","https://tinker-docs.thinkingmachines.ai/tinker/api-reference/restclient/","https://tinker-docs.thinkingmachines.ai/tinker/cli/billing/"]
(out/"report.json").write_text(json.dumps(r,indent=2));print("READ_ONLY_BUDGET_INSPECT",json.dumps(r),flush=True)
