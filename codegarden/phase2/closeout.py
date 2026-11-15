"""Bounded optional final record query and read-only account/arena closeout."""
import csv,datetime as dt,hashlib,io,json,os,pathlib,sys,urllib.request
from common import ROOT,OUT,save,before_cutoff
sys.path.insert(0,str(ROOT))
from providers import Providers,cli,http
from supervisor import verify
def get(url):
 with urllib.request.urlopen(url,timeout=45) as r:return r.read()
def main():
 # Serialize behind the completed model control and carry all cumulative holds.
 latest=OUT/"supplement/memory_recovery/status.json"
 control=json.loads((latest if latest.exists() else OUT/"supplement/status.json").read_text())
 assert control.get("finished_at"),"Supplement must be durably finished before closeout"
 totals={p:d["reserved"]+d["provider_reported_or_estimated"] for p,d in control["budget"].items()}
 (ROOT/"budget/historical-usage.json").write_text(json.dumps({"source_run":"phase2-supplement-"+control["source_sha"],
  "conservative_totals":totals,"reason":"All cumulative prior usage and unresolved reservations carried forward; no silent releases."},indent=2))
 events=[]
 def log(kind,value):events.append({"kind":kind,"value":value})
 p=Providers(OUT,log);result={"started_at":dt.datetime.now(dt.timezone.utc).isoformat(),"historical_holds_imported":totals}
 if before_cutoff() and os.environ.get("CODEGARDEN_FINAL_RECORD_QUERY")=="1":
  try:
   result["final_exa_record_check"]=p.exa("binary two deletion correcting codes length 16 largest known construction 226 227","phase2-final-record-check")
  except Exception as e:result["final_exa_record_check_error"]=str(e)[:300]
 else:result["final_exa_record_check"]="Skipped: paid-work cutoff reached; preserve earlier current research"
 problem_raw=get("https://einsteinarena.com/api/problems/two-deletion-code-16");problem=json.loads(problem_raw)
 result["official_verifier_matches_pinned"]=problem["verifier"].strip()==(ROOT/"artifacts/sources/official_verifier.py").read_text().strip()
 assert result["official_verifier_matches_pinned"]
 raw=get("https://einsteinarena.com/api/solutions/best?problem_id=34&limit=5");leaders=json.loads(raw);entries=[]
 for i,row in enumerate(leaders):
  path=OUT/("worker_closeout_arena_"+str(i)+".txt");path.write_text("\n".join(sorted(row["data"]["words"]))+"\n")
  entries.append({"id":row["id"],"author":row["agentName"],"listed_score":row["score"],"verification":verify(path)})
 result["arena"]={"checked_at":dt.datetime.now(dt.timezone.utc).isoformat(),"response_sha256":hashlib.sha256(raw).hexdigest(),"leaders":entries}
 result["past_remaining_credits"]=http("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"]).get("balance",{}).get("left")
 modal=json.loads(cli("modal","billing","summary","--json"))
 result["modal_account"]={k:modal.get(k) for k in ["metered_cost","billed_cost","adjustments"]}
 try:
  apps=json.loads(cli("modal","app","list","--json"))
  if isinstance(apps,dict):apps=apps.get("apps",[])
  result["own_modal_apps"]=[{k:v for k,v in a.items() if k in ["App ID","Description","State","Name","app_id","name","state","description"]} for a in apps if "codegarden" in json.dumps(a).lower()]
 except Exception as e:result["modal_app_inventory_error"]=type(e).__name__
 end=(dt.datetime.now(dt.timezone.utc).replace(minute=0,second=0,microsecond=0)+dt.timedelta(hours=1)).isoformat().replace("+00:00","Z")
 try:
  usage=cli("tinker","billing","usage","2026-11-14T00:00:00Z",end,"--csv","-")
  sessions=cli("tinker","billing","usage","2026-11-14T00:00:00Z",end,"--sessions-csv","-")
  rows=list(csv.DictReader(io.StringIO(usage)));ss=list(csv.DictReader(io.StringIO(sessions)))
  owned={s.get("session_id") for s in ss if "codegarden" in json.dumps(s).lower()}
  matched=[r for r in rows if r.get("session_id") in owned]
  result["tinker_usage"]={"account_rows":len(rows),"usage_schema":list(rows[0]) if rows else [],
   "session_metadata_rows":len(ss),"metadata_matched_codegarden_sessions":len(owned),
   "metadata_matched_rows":len(matched),"matched_estimated_gross_usd":sum(float(r.get("estimated_cost_usd") or 0) for r in matched),
   "account_estimated_gross_usd":sum(float(r.get("estimated_cost_usd") or 0) for r in rows),
   "usage_response_sha256":hashlib.sha256(usage.encode()).hexdigest(),
   "attribution_limit":"Metadata string matching is supporting evidence only. Hourly usage may lag; all unresolved holds remain."}
 except Exception as e:result["tinker_usage_error"]=str(e)[:200]
 receipts={}
 def collect(value):
  if isinstance(value,dict):
   if value.get("request_id") and isinstance(value.get("cost_dollars"),dict) and isinstance(value["cost_dollars"].get("total"),(int,float)):
    receipts[value["request_id"]]=value["cost_dollars"]["total"]
   for vv in value.values():collect(vv)
  elif isinstance(value,list):
   for vv in value:collect(vv)
 for file in list((ROOT/"artifacts").rglob("*.json"))+list((ROOT/"docs").rglob("*.json")):
  try:collect(json.loads(file.read_text()))
  except (ValueError,OSError):pass
 collect(result)
 result["deduplicated_exa_provider_receipts"]={"requests":len(receipts),"reported_gross_usd":sum(receipts.values()),
  "request_ids":sorted(receipts),"reconciliation":"Published provider receipts are deduplicated. No unresolved historical reservation is released without an exact reservation linkage."}
 result["cumulative_budget"]=p.ledger.summary()
 result["accounting_note"]="Cumulative conservative holds are not actual charges. The old mixed reported-or-estimated field remains explicitly mixed; account totals include other projects."
 result["finished_at"]=dt.datetime.now(dt.timezone.utc).isoformat();save("closeout.json",result);save("closeout_provider_trace.json",events)
 (ROOT/"budget/phase2-usage-summary.json").write_text(json.dumps(result,indent=2))
 print("CLOSEOUT "+json.dumps({"arena_best":max(e["verification"]["cardinality"] for e in entries),"budget":result["cumulative_budget"],"finished_at":result["finished_at"]}))
if __name__=="__main__":main()
