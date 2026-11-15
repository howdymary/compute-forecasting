"""Recover existing ingestion handles and recall source-backed method. Never resubmit."""
import importlib.util,json,os,pathlib,time,urllib.parse
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("codegarden_side_cycle",ROOT/"side_services/cycle.py")
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
C.BRANCH="codegarden-side-memory-recovery-001";C.OUT=ROOT/"artifacts/side_research/memory_recovery_001";C.OUT.mkdir(parents=True,exist_ok=True)
key=os.environ["PAST_API_KEY"];prefix="codegarden-side-43748900357-"
query=urllib.parse.urlencode({"search":prefix,"endpoint":"/api/v1/ingest","first":20,"from":"2026-11-15T18:49:00Z"})
page=C.http("https://api.past.dev/api/v1/requests?"+query,key)
rows=[]
for row in page["requests"]:
 if not row.get("ingestionId"):continue
 detail=C.http("https://api.past.dev/api/v1/requests/"+urllib.parse.quote(row["requestId"],safe=""),key)
 item=(detail.get("payload") or {}).get("request",{})
 if isinstance(item,str):
  try:item=json.loads(item)
  except ValueError:continue
 sid=item.get("id","")
 if not sid.startswith(prefix):continue
 rows.append({"source_id":sid,"identity":item.get("identity"),"request_id":row["requestId"],"ingestion_id":row["ingestionId"],"received_at":row["receivedAt"],"phase_at_request_log":row.get("phase")})
C.save("recovered_handles.json",{"handles":rows,"resubmitted":False,"billing_queries":False,"scope":"Only source IDs from research run43748900357; no other project records persisted."});C.publish()
deadline=time.monotonic()+30
while True:
 for row in rows:
  status=C.http("https://api.past.dev/api/v1/ingest/"+row["ingestion_id"],key)
  row["observed_status"]=status
 C.save("status.json",{"handles":rows,"resubmitted":False});C.publish()
 if all(r["observed_status"]["status"] in ["completed","failed"] for r in rows) or time.monotonic()>=deadline:break
 time.sleep(3)
for row in rows:
 if row["observed_status"]["status"]!="completed":
  try:
   explain=C.http("https://api.past.dev/api/v1/ingest/"+row["ingestion_id"]+"/explain",key)
   C.save("explanations/"+row["source_id"]+".json",explain)
  except Exception as e:C.save("explanations/"+row["source_id"]+".json",{"unavailable":str(e)[:300]})
method=next((r for r in rows if r["identity"]=="codegarden-side-researcher"),None)
reuse={"source_id":None,"reused":False,"independent_assistant_agents":False,"role_note":"Software strategist reads another software role's finding; not a claim of multiple independent assistant agents."}
if method:
 for _ in range(3):
  recalled=C.http("https://api.past.dev/api/v1/recall",key,{"identity":"codegarden-side-strategist","query":"CodeGarden side services_001 source_backed_method fixed degree ordering "+method["source_id"],"maxTokens":1500})
  ids={s["sourceId"] for r in recalled.get("results",[]) for s in r.get("sources",[])}
  if method["source_id"] in ids:
   reuse.update(source_id=method["source_id"],reused=True,returned_codegarden_source_ids=sorted(s for s in ids if s.startswith("codegarden-side-")),retrieved_response_sha256=__import__("hashlib").sha256(json.dumps(recalled,sort_keys=True).encode()).hexdigest())
   break
  time.sleep(2)
C.save("strategist_reuse.json",reuse)
result_path=ROOT/"artifacts/side_research/services_001/summary.json"
summary=json.loads(result_path.read_text())
queue={"based_on_memory_source_id":reuse["source_id"],"memory_reuse_verified":reuse["reused"],"best_verified_cardinality":summary["best_verified"],"retired_literal_models":[{"pivot_id":r["pivot"],"removed_count":r["removed"],"ordering":r["ordering"],"reason":"Exact solver completed the explicitly encoded model without a feasible227; no global inference."} for r in summary["model_statuses"] if r["status"]=="INFEASIBLE_ENCODED_NEIGHBORHOOD"],"open_models":[r for r in summary["model_statuses"] if r["status"]=="TIMEOUT" and r["removed"]==64],"next_hypothesis":"Stronger bounds or a different repair neighborhood are needed for the3151-candidate model; fixed degree ordering alone did not finish it in30seconds.","new_global_record_claim":False,"training_improvement_claim":False}
C.save("next_research_queue.json",queue)
C.save("summary.json",{"handles_recovered":len(rows),"states":[{"source_id":r["source_id"],"status":r["observed_status"]["status"],"blocked":r["observed_status"]["blocked"],"settled":r["observed_status"]["settled"]} for r in rows],"strategist_reused_researcher":reuse["reused"],"ingestions_restarted":False,"best_verified":226});C.publish()
print("CODEGARDEN_MEMORY_RECOVERY",json.dumps({"handles":len(rows),"reuse":reuse["reused"],"best":226}),flush=True)
