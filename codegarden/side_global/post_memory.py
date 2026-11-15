"""Persist the verified global batch and source-backed next hypothesis."""
import importlib.util,json,os,pathlib,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location("cg_global_post",ROOT/"side_services/cycle.py");C=importlib.util.module_from_spec(sp);sp.loader.exec_module(C)
C.OUT=ROOT/"artifacts/side_research/global_memory_001";C.OUT.mkdir(parents=True,exist_ok=True);C.BRANCH="codegarden-side-global-memory-001";C.ledger.rows=[]
summary=json.loads((ROOT/"artifacts/side_research/global_001/summary.json").read_text())
queue=json.loads((ROOT/"artifacts/side_research/global_001/next_hypothesis.json").read_text())
sid="codegarden-global-43753466573-analyst"
item={"id":sid,"identity":"codegarden-side-analyst","audience":"codegarden-side-services-v1","timestamp":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),"label":"CodeGarden verified global batch and startup bottleneck","content":json.dumps({"project":"codegarden","experiment_id":"global_001","author":"codegarden-side-analyst","summary":summary,"next_hypothesis":queue,"source_commit":"07cb2bcb3f74f91567294ac323507eec3fd1b2c8","global_record_claim":False})}
C.ledger.reserve("past","codegarden",30);record={"source_id":sid,"state":"prepared","idempotency_key":sid};C.save("memory_handle.json",record);C.publish()
r=C.http("https://api.past.dev/api/v1/ingest",os.environ["PAST_API_KEY"],{**item,"idempotencyKey":sid});record.update(ingestion_id=r["ingestionId"],state="accepted");C.save("memory_handle.json",record);C.publish()
deadline=time.monotonic()+15
while True:
 status=C.http("https://api.past.dev/api/v1/ingest/"+record["ingestion_id"],os.environ["PAST_API_KEY"]);record.update(state=status["status"],readiness=status.get("readiness"));C.save("memory_handle.json",record)
 if status["status"] in ["completed","failed"] or time.monotonic()>=deadline:break
 time.sleep(2)
if record["state"]=="completed":
 try:C.recall("researcher","CodeGarden global_001 portable whole universe warm tied226 cold separator pool timeout next initialization "+sid,sid);record["researcher_recalled"]=True
 except Exception as e:record.update(researcher_recalled=False,recall_note=str(e)[:400])
C.save("memory_handle.json",record);C.ledger.persist();C.publish();print("GLOBAL_MEMORY_POST",json.dumps(record),flush=True)
