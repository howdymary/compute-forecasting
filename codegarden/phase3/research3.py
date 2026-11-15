"""Real source research and cross-role memory inform one bounded native follow-up."""
import base64,datetime as dt,hashlib,json,os,pathlib,re,subprocess,sys,time,traceback,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"phase2"))
from providers import Providers,http,cli
from phase2.role import recalled
from phase2.model_policy import Policy
from supervisor import verify
OUT=ROOT/"artifacts/phase3/research_003";OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2));return p
def read(path,ref):
 p=subprocess.run(["gh","api","repos/"+os.environ["GITHUB_REPOSITORY"]+"/contents/"+path+"?ref="+ref],capture_output=True,text=True,check=True)
 return json.loads(base64.b64decode(json.loads(p.stdout)["content"]))
def main():
 previous=read("codegarden/artifacts/phase3/component6_001/status.json","codegarden-modal-006");assert previous["status"]=="completed"
 history={"source_run":"component6-complete-"+previous["source_sha"],"conservative_totals":{p:v["reserved"]+v["provider_reported_or_estimated"] for p,v in previous["budget"].items()},"reason":"All prior completed/unknown holds retained, including all 36 worker time bounds."}
 (ROOT/"budget/historical-usage.json").write_text(json.dumps(history,indent=2));spec=json.loads((ROOT/"budget/shared-allocation.json").read_text());spec["providers"]["past"]["balance_at_snapshot"]=http("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"])["balance"]["left"];(ROOT/"budget/shared-allocation.json").write_text(json.dumps(spec,indent=2))
 events=[];p=None;status={"status":"running","source_sha":os.environ["GITHUB_SHA"],"started_at":dt.datetime.now(dt.timezone.utc).isoformat(),"history":history}
 def log(kind,value):
  safe=json.loads(json.dumps(value))
  if kind=="exa_search":
   for source in safe.get("sources",[]):source.pop("excerpt",None)
  events.append({"kind":kind,"value":safe,"at":dt.datetime.now(dt.timezone.utc).isoformat()});save("provider_trace.json",events)
  if p:save("ledger_progress.json",p.ledger.summary())
 try:
  p=Providers(OUT,log);p.setup_memory();eight=read("codegarden/artifacts/phase3/connected_002/ordered8/report.json","codegarden-connected-004")
  assert eight["complete"] and not eight["found"]
  facts={"best_independently_verified":226,"target":227,"closed_root_radius":8,"root_hash":"417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa",
   "connected_search":{"k6_cpu_seconds":.833256,"k7_cpu_seconds":6.38014,"k8_cpu_seconds":eight["cpu_seconds"],"k8_source_sha":eight["source_sha"]},
   "proof_scope":"Native exhaustive restricted exchanges, no formal external certificate and no global bound.",
   "next_bottleneck":"A 227-word code must escape the reproduced root's small exchange region; compare deeper connected exchanges and primitive neutral bridges on a different 225-word lineage.",
   "negative_findings":"Dense/feedback tempering had no valid 227 and no new 226 orbits in independent projection. Feasible-hint CP-LNS exported only 225.",
   "training_gate":"No new fine-tuning: no adequate verified conditional primary improvement data."}
  analyst=p.write("analyst","connected_barrier_eight",facts,"phase3-connected-exchanges")
  actual=recalled(p.read("researcher","Recall the CodeGarden analyst's connected_barrier_eight, exact closed root radius and remaining mathematical target.",analyst),analyst);save("researcher_recall.json",actual)
  text=json.dumps(actual["actual_content"]);gate="closed_root_radius" in text and "connected_search" in text
  queries=[
   "minimal improving exchanges set packing connected components bounded pathwidth color coding Cygan",
   "Avis Fukuda reverse search enumeration connected subgraphs canonical parent non articulation vertices",
   "Feedback optimized parallel tempering Monte Carlo Katzgraber Trebst Huse Troyer bottlenecks"]
  if not gate:queries[0]="binary two deletion correcting codes length 16 226 227 current explicit construction 2026"
  sources=[]
  for query in queries:
   result=p.exa(query,"phase3-next-connected-strategy")
   for source in result["sources"]:source.pop("excerpt",None)
   sources.append(result);save("searches.json",sources)
  method={"actual_recalled_analyst":actual,"memory_changed_first_query":gate,"searches":sources,
   "extracted_method":"Canonical reverse search and connected local-improvement neighborhoods are established algorithm families. CodeGarden's blocker-connected completeness argument and its implementation are an adaptation; no new global coding theorem is claimed.",
   "next_hypotheses":["Deeper connected strict exchange on the distinct arena-225 lineage","Primitive neutral bridge followed by strict connected augmentation"],
   "record_audit":"Search results alone do not establish a global record. Leading explicit witness remains independently reproduced 226."}
  researcher=p.write("researcher","connected_reverse_search_context",method,"phase3-connected-followup",[analyst])
  strategy_evidence=recalled(p.read("strategist","Recall connected_reverse_search_context and its proposed deeper exchange or primitive bridge experiments.",researcher),researcher);save("strategist_recall.json",strategy_evidence)
  policy=Policy(p.ledger);decision=policy.choose({"target":227,"actual_other_role_memory":strategy_evidence,"budget":"at most two 45-CPU-second native requests; valid exports only",
   "definitions":{"connected_deep":"Strict radius-eight exchanges on the distinct arena-225 code, then repeat on an improvement","primitive_bridge":"Primitive radius-five neutral move on that code, then strict radius-eight augmentation"}},["connected_deep","primitive_bridge"])
  save("strategy_decision.json",decision);assert decision["valid_action"]
  plan=p.write("strategist","selected_bounded_connected_followup",{"decision":decision,"actual_memory":strategy_evidence,"source_program":os.environ["GITHUB_SHA"]},"phase3-connected-followup",[researcher])
  baseline=next((ROOT/"artifacts/baselines").glob("arena_225_*.txt"));words=baseline.read_text().splitlines();verify(baseline);trials=[];best=225
  for step in range(2):
   bridge=step==0 and decision["action"]=="primitive_bridge";k=5 if bridge else 8;cap=64 if bridge else 0
   binary=ROOT/".build"/("primitive" if bridge else "connected")
   result=subprocess.run([str(binary),"16",str(k),"45","1000000000000",str(cap)],input="\n".join(words)+"\n",capture_output=True,text=True,check=True,timeout=120,
    env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="0" if bridge else "1"));r=json.loads(result.stdout)
   pool=r.pop("candidate_pool");neighbors=r.pop("neighbors");r["candidate_order_sha256"]=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in pool)).hexdigest();r["starting_words"]=words
   candidate=None
   if r["found"]:
    C={int(w,2) for w in words};candidate=sorted(C-set(r["removed"])|set(r["added"]))
   elif bridge and neighbors:
    parent={int(w,2) for w in words};candidate=max(neighbors,key=lambda C:len(set(C)-parent))
   if candidate:
    q=OUT/("candidate_"+str(step)+".txt");q.write_text("\n".join(format(w,"016b") for w in candidate)+"\n");r["independent_verification"]=verify(q);best=max(best,len(candidate));words=q.read_text().splitlines()
   trials.append(r);save("experiment.json",{"actual_tinker_action":decision,"trials":trials,"best_exported":best,"global_retained_best":max(226,best),"scope":"This bounded follow-up is a real use of the selected proposal, not a causal model-quality comparison."})
   if best>=227 or candidate is None:break
  status.update(status="completed",memory_query_gate=gate,source_ids=[analyst,researcher,plan],decision=decision,best_exported=best,best_independently_verified=max(226,best),
   role_execution="Three named software role identities in one serialized process; not independent assistant subagents",new_training=False)
 except Exception as e:status.update(status="failed_or_partial",error=str(e)[:1000]);traceback.print_exc()
 finally:
  status.update(budget=p.ledger.summary() if p else None,finished_at=dt.datetime.now(dt.timezone.utc).isoformat());save("status.json",status);print("RESEARCH3_FINAL",json.dumps(status),flush=True)
if __name__=="__main__":main()
