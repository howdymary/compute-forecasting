"""One bounded, real service cycle. No BoundForge reserves; no billing queries."""
import datetime as dt, hashlib, importlib.util, json, os, pathlib, re, subprocess, sys, time, traceback, urllib.request, uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/side_research/services_001"; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
SOURCE=os.environ["SOURCE_SHA"]; BRANCH="codegarden-services-side-001"; HEAD=SOURCE
REPO="howdymary/compute-forecasting"; events=[]
def save(name,data):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2));return p
def github(path,data=None,method=None):
 req=urllib.request.Request("https://api.github.com/repos/"+REPO+"/"+path,
  data=None if data is None else json.dumps(data).encode(),method=method,
  headers={"Authorization":"Bearer "+os.environ["GH_TOKEN"],"Accept":"application/vnd.github+json","Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
def publish():
 global HEAD
 actual=github("git/ref/heads/"+BRANCH)["object"]["sha"]
 if actual!=HEAD:raise RuntimeError("Evidence branch lease changed; no new provider call is permitted")
 files=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in OUT.rglob("*") if p.is_file() and p.suffix in [".json",".jsonl",".txt",".md"]]
 if not files:return
 tree=github("git/trees",{"base_tree":github("git/commits/"+HEAD)["tree"]["sha"],"tree":files},"POST")["sha"]
 commit=github("git/commits",{"message":"Checkpoint bounded CodeGarden service research","tree":tree,"parents":[HEAD]},"POST")["sha"]
 github("git/refs/heads/"+BRANCH,{"sha":commit,"force":False},"PATCH");HEAD=commit
def log(kind,data):
 events.append({"time":dt.datetime.now(dt.timezone.utc).isoformat(),"kind":kind,"data":data})
 save("events.json",events);print(kind,json.dumps(data)[:1800],flush=True)
class Journal:
 caps={"exa":2,"tinker":1,"modal":1,"past":300}
 def __init__(self):
  self.rows=[{"id":"precommitted-exa-mcp","provider":"exa","reserved":1,"actual":None,"status":"unknown_actual_retained"}]
 def reserve(self,provider,project,amount):
  if provider=="past.dev":provider="past"
  used=sum(r["reserved"] if r["actual"] is None else r["actual"] for r in self.rows if r["provider"]==provider)
  if not 0<amount<=self.caps[provider]-used:raise RuntimeError("Bounded batch exhausted")
  rid=uuid.uuid4().hex;self.rows.append({"id":rid,"provider":provider,"reserved":amount,"actual":None,"status":"pending"})
  self.persist();publish();return rid
 def settle(self,rid,actual):
  if actual is None:return
  row=next(r for r in self.rows if r["id"]==rid)
  if not 0<=actual<=row["reserved"]:raise RuntimeError("Unexpected usage metadata; stop batch")
  row.update(actual=actual,status="reported");self.persist()
 def persist(self):save("service_journal.json",{"rows":self.rows,"caps":self.caps,"boundforge_coordination":False,"purchases":False,"billing_queries":False,"past_units":"credits","other_units":"USD"})
ledger=Journal()
def http(url,key,data=None,method=None,header="Authorization"):
 req=urllib.request.Request(url,data=None if data is None else json.dumps(data).encode(),method=method,
  headers={header:("Bearer " if header=="Authorization" else "")+key,"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
actors={r:"codegarden-side-"+r for r in ["analyst","researcher","strategist"]};audience="codegarden-side-services-v1"
def write_memory(role,kind,content,parents=()):
 sid="codegarden-side-"+os.environ["GITHUB_RUN_ID"]+"-"+role+"-"+uuid.uuid4().hex[:8]
 item={"id":sid,"identity":actors[role],"audience":audience,"timestamp":dt.datetime.now(dt.timezone.utc).isoformat(),
  "label":"CodeGarden side "+kind,"content":json.dumps({"project":"codegarden","author":actors[role],"kind":kind,"experiment_id":"services_001","parents":list(parents),"content":content})}
 ledger.reserve("past","codegarden",30)
 result=http("https://api.past.dev/api/v1/ingest",os.environ["PAST_API_KEY"],{**item,"idempotencyKey":sid})
 pending={"role":role,"source_id":sid,"ingestion_id":result["ingestionId"],"status":"accepted_pending","parent_source_ids":list(parents)}
 save("memory_pending/"+sid+".json",pending);log("past_ingest_handle",pending);publish()
 for _ in range(60):
  status=http("https://api.past.dev/api/v1/ingest/"+result["ingestionId"],os.environ["PAST_API_KEY"])
  if status["status"]=="completed":
   pending.update(status="completed",readiness=status.get("readiness"));save("memory_pending/"+sid+".json",pending)
   log("past_write",{"role":role,"source_id":sid,"parent_source_ids":list(parents)});publish();return sid
  if status["status"]=="failed":raise RuntimeError("Memory ingestion failed")
  time.sleep(1)
 pending.update(status="still_pending_after_observation_window");save("memory_pending/"+sid+".json",pending);publish()
 raise TimeoutError("Memory ingestion remains pending; resumable handle saved for "+sid)
def recall(role,query,required):
 for _ in range(4):
  ledger.reserve("past","codegarden",1)
  result=http("https://api.past.dev/api/v1/recall",os.environ["PAST_API_KEY"],{"identity":actors[role],"query":query,"maxTokens":1000})
  ids={s["sourceId"] for r in result.get("results",[]) for s in r.get("sources",[])}
  if required in ids:
   log("past_read",{"role":role,"required_source_id":required,"returned_codegarden_source_ids":sorted(s for s in ids if s.startswith("codegarden-"))});publish();return result
  time.sleep(1)
 raise RuntimeError("Required source absent from actual recall")
def exa_search(query):
 ledger.reserve("exa","codegarden",.1)
 result=http("https://api.exa.ai/search",os.environ["EXA_API_KEY"],{"query":query,"type":"auto","numResults":4,"contents":{"highlights":True}},header="x-api-key")
 safe=[{"url":r["url"],"title":r.get("title"),"excerpt":" ".join(" ".join(r.get("highlights",[])).split()[:10]),
  "highlights_sha256":hashlib.sha256(json.dumps(r.get("highlights",[])).encode()).hexdigest()} for r in result.get("results",[])]
 event={"query":query,"request_id":result.get("requestId"),"sources":safe,"influenced_experiment":"paired fixed degree ordering in exact repair"}
 log("exa_search",event);publish();return event
def tinker_choose(state):
 import tinker
 ledger.reserve("tinker","codegarden",.1)
 service=tinker.ServiceClient(display_name="CodeGarden side repair strategist")
 sampler=service.create_sampling_client(base_model="Qwen/Qwen3.5-4B")
 if hasattr(sampler,"result"):sampler=sampler.result()
 tok=sampler.get_tokenizer()
 messages=[{"role":"system","content":"Choose exactly one bounded search ordering: degree_desc or degree_asc. Return only the identifier. Never invent a result."},
  {"role":"user","content":json.dumps(state,sort_keys=True)}]
 tokens=tok.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,return_dict=False)
 if len(tokens)>8192:raise RuntimeError("Context boundary")
 result=sampler.sample(prompt=tinker.ModelInput.from_ints(tokens),sampling_params=tinker.types.SamplingParams(max_tokens=24,temperature=0),num_samples=1).result()
 reply=tok.decode(result.sequences[0].tokens,skip_special_tokens=True).strip()
 found={a for a in ["degree_desc","degree_asc"] if re.search(r"(?<![A-Za-z0-9_])"+a+r"(?![A-Za-z0-9_])",reply)}
 selected=next(iter(found)) if len(found)==1 else None
 report={"model":"Qwen/Qwen3.5-4B","action":selected,"valid_action":selected is not None,"strict_format":reply in ["degree_desc","degree_asc"],"prompt_tokens":len(tokens),"output_tokens":len(result.sequences[0].tokens),"reply_sha256":hashlib.sha256(reply.encode()).hexdigest(),"training":False}
 log("tinker_strategy",report);save("tinker_proposal.json",report);publish();return report
def main():
 import modal
 check_integrity()
 seed=(ROOT/"artifacts/best_code.txt").read_text()
 assert hashlib.sha256(seed.encode()).hexdigest()=="417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa"
 seed_report=verify(ROOT/"artifacts/best_code.txt");save("seed_verification.json",seed_report)
 definitions=json.loads((ROOT/"side_services/models.json").read_text())
 provenance=json.loads((ROOT/"side_services/exa_provenance.json").read_text())
 status={"status":"running","source_sha":SOURCE,"best_verified":226,"training_claim":False,"memory_actor_note":"Three software role identities in a single serialized controller; no independent assistant agents are claimed."}
 save("status.json",status);save("exa_mcp_provenance.json",provenance);ledger.persist();publish()
 analysis="Paired random versus blocker-closure-guided repair produced guided pools of 662 to 913 words for removal size32. All 12 initial guided trials timed out at .25s. Uint32 implementation closed the 662-word pivot-zero model after376301 nodes; the779-word pivot-one model timed out at5s. Best remains226; none of these facts proves global optimality. Full literal pool hashes and removed-index sets are attached to the experiment inputs."
 analyst=None;researcher=None
 try:
  http("https://api.past.dev/api/v1/audiences/"+audience,os.environ["PAST_API_KEY"],{"kind":"fixed","name":"CodeGarden side research","identities":list(actors.values())},method="PUT")
  analyst=write_memory("analyst","scoped_findings",analysis)
  recall("researcher","CodeGarden side services_001 blocker closure 662 779 timeout research bottleneck "+analyst,analyst)
  status["analyst_memory_reused_by_researcher"]=True
 except Exception as e:log("past_early_failure",{"error":str(e)[:500],"memory_reuse_claim":False})
 try:
  external=exa_search("Primary research on exact maximum clique bit parallel fixed maximum degree first ordering for medium density structured graphs, compared with coloring bounds, motivated by open779-vertex deletion-code repair model")
 except Exception as e:
  external={"sources":[]};log("exa_rest_failure",{"error":str(e)[:500]})
 method={"method":"Compare fixed maximum-degree-first and minimum-degree-first against original word order in exact bitset clique repair.","source":"https://arxiv.org/abs/1801.00202","scope":"Adaptation of ordering idea; original paper studies maximal clique enumeration, not this exact maximum-clique program.","root_evidence":analysis,"exa_rest_sources":external.get("sources",[])}
 try:
  researcher=write_memory("researcher","source_backed_method",method,[analyst] if analyst else [])
  recall("strategist","CodeGarden side services_001 fixed degree ordering method "+researcher,researcher)
  status["researcher_memory_reused_by_strategist"]=True
 except Exception as e:log("past_method_failure",{"error":str(e)[:500],"memory_reuse_claim":False})
 try:
  proposal=tinker_choose({"verified_incumbent":226,"target":227,"method":method,"actual_memory_source":researcher,"allowed":["degree_desc","degree_asc"],"control":"original word order","equal_seconds_per_model":30})
 except Exception as e:
  proposal={"action":None,"valid_action":False,"error":str(e)[:500],"training":False};save("tinker_proposal.json",proposal);log("tinker_failure",proposal)
 action=proposal.get("action") or "degree_desc";mode=1 if action=="degree_desc" else 2
 plan=[{"query":d,"ordering":o,"seconds":30,"role":"fixed_control" if o==0 else "tinker_selected" if proposal.get("valid_action") else "explicit_fallback"} for d in definitions for o in [0,mode]]
 save("plan.json",{"models":plan,"hypothesis":method,"source_sha":SOURCE,"initializations_identical_within_pairs":True,"trained_policy_comparison":False});publish()
 image=modal.Image.debian_slim(python_version="3.11").add_local_file(str(ROOT/".build/side_clique"),"/opt/codegarden/side_clique")
 for rel in ["supervisor.py","protected/verify_descendants.py","protected/verify_lcs.py","protected/manifest.json"]:
  image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
 app=modal.App("codegarden-side-repair-services-001")
 volume=modal.Volume.from_name("codegarden-side-services-20261115",create_if_missing=True)
 @app.function(serialized=True,image=image,cpu=1,memory=1024,timeout=90,max_containers=4,retries=0,scaledown_window=2,volumes={"/codegarden/checkpoints":volume})
 def worker(spec,seed,source):
  import hashlib,json,pathlib,subprocess,sys,time,uuid
  sys.path.insert(0,"/opt/codegarden")
  from supervisor import verify
  started=time.monotonic();q=spec["query"];base=[int(s,2) for s in seed.strip().splitlines()]
  fields=[str(len(base)),*map(str,base),str(len(q["removed_indices"])),*map(str,q["removed_indices"]),str(int(q["forced"],2)),str(spec["ordering"]),str(spec["seconds"])]
  p=subprocess.run(["/opt/codegarden/side_clique"],input=" ".join(fields),text=True,capture_output=True,timeout=75,check=True)
  native=json.loads(p.stdout)
  digest=hashlib.sha256(("".join(format(w,"016b")+"\n" for w in native["pool_words"])).encode()).hexdigest()
  if digest!=q["pool_sha256"]:raise RuntimeError("Independent native pool hash mismatch")
  code=[w for i,w in enumerate(base) if i not in set(q["removed_indices"])]
  if native["status"]=="FEASIBLE":code += [int(q["forced"],2)]+native["selected_words"]
  else:code=base
  folder=pathlib.Path("/codegarden/checkpoints")/uuid.uuid4().hex;folder.mkdir()
  path=folder/"witness.txt";path.write_text("".join(format(w,"016b")+"\n" for w in sorted(code)))
  checked=verify(path)
  result={"spec":spec,"source_sha":source,"pool_sha256":digest,"native":native,"verification":checked,"words":[format(w,"016b") for w in sorted(code)],"runtime_seconds":time.monotonic()-started,"durable_path":str(folder),"scope":"Only explicit fixed-outside mandatory-pivot neighborhood. Timeout is unresolved. No global optimality claim."}
  (folder/"result.json").write_text(json.dumps(result));volume.commit();return result
 ledger.reserve("modal","codegarden",1)
 rows=[];calls=[]
 try:
  with app.run():
   calls=[worker.spawn(spec,seed,SOURCE) for spec in plan]
   for i,call in enumerate(calls):
    result=call.get(timeout=180);path=OUT/("worker_"+str(i)+".txt");path.write_text("\n".join(result["words"])+"\n")
    result["host_verification"]=verify(path);save("workers/"+str(i)+".json",result);rows.append(result)
    status["best_verified"]=max(status["best_verified"],len(result["words"]))
    save("status.json",status);publish()
    if len(result["words"])>=227:
     (OUT/"candidate.txt").write_text(path.read_text())
     with open(os.environ["GITHUB_OUTPUT"],"a") as stream:stream.write("has_candidate=true\n")
     save("candidate_provenance.json",{"source_sha":SOURCE,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"worker":i,"fresh_isolated_acceptance_required":True})
     for other in calls[i+1:]:
      try:other.cancel()
      except Exception:pass
     break
 except Exception as e:
  log("modal_failure",{"error":str(e)[:1000]});status["modal_error"]=str(e)[:1000]
  for call in calls:
   try:call.cancel()
   except Exception:pass
 status.update(status="completed" if len(rows)==len(plan) else "candidate_pending_isolated_acceptance" if status["best_verified"]>=227 else "partial_or_failed",collected_workers=len(rows),model_statuses=[{"pivot":r["spec"]["query"]["pivot_id"],"removed":len(r["spec"]["query"]["removed_indices"]),"ordering":r["spec"]["ordering"],"status":r["native"]["status"],"nodes":r["native"]["nodes"],"seconds":r["native"]["seconds"]} for r in rows])
 try:
  final=write_memory("analyst","measured_results",{"best":status["best_verified"],"model_statuses":status["model_statuses"],"next_action":"Escalate only unresolved models or switch solver bounds; no timeout is a proof."},[researcher] if researcher else [])
  recall("researcher","CodeGarden side services_001 measured_results next_action "+final,final)
  status["final_analyst_memory_reused_by_researcher"]=True
 except Exception as e:log("past_final_failure",{"error":str(e)[:500]})
 save("summary.json",status);save("status.json",status);ledger.persist();publish()
 print("CODEGARDEN_SIDE_SERVICES_RESULT",json.dumps(status),flush=True)
if __name__=="__main__":
 try:main()
 except Exception as e:
  traceback.print_exc();save("fatal.json",{"error":str(e)[:1000],"source_sha":SOURCE})
  try:ledger.persist();publish()
  except Exception:traceback.print_exc()
  raise
