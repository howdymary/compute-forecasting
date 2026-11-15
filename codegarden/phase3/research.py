"""Renewed coordinated research calls; no model training or compute workers."""
import datetime as dt,hashlib,json,os,pathlib,re,sys,traceback,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"phase2"))
from providers import Providers,http,cli
from phase2.role import recalled
OUT=ROOT/"artifacts/phase3/research_001";OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2))
def main():
 spec=json.loads((ROOT/"phase3/renewal_001.json").read_text())
 spec["providers"]["past"]["balance_at_snapshot"]=http("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"])["balance"]["left"]
 # Read-only fresh provider account boundary checks before issuing billable requests.
 modal=json.loads(cli("modal","billing","summary","--json"));save("account_preflight.json",{"at":dt.datetime.now(dt.timezone.utc).isoformat(),
  "authenticated_dashboard_snapshot":spec["authenticated_preflight_at"],"modal_account":modal,"past_remaining":spec["providers"]["past"]["balance_at_snapshot"],
  "provider_caps_unchanged":True,"other_project_reserves_retained":True})
 (ROOT/"budget/shared-allocation.json").write_text(json.dumps(spec,indent=2))
 previous=json.loads((ROOT/"budget/phase2-usage-summary.json").read_text())["cumulative_budget"]
 history={"source_run":"phase2-final-verified-closeout","conservative_totals":{p:v["reserved"]+v["provider_reported_or_estimated"] for p,v in previous.items()},
  "reason":"No previous unknown charge or reservation is released; new provider calls are serialized and cumulative."}
 (ROOT/"budget/historical-usage.json").write_text(json.dumps(history,indent=2))
 events=[];p=None;status={"status":"running","source_sha":os.environ["GITHUB_SHA"],"started_at":dt.datetime.now(dt.timezone.utc).isoformat(),"history":history}
 def log(kind,value):
  events.append({"kind":kind,"value":value,"time":dt.datetime.now(dt.timezone.utc).isoformat()});save("provider_trace.json",events)
  if p:save("ledger_progress.json",p.ledger.summary())
 try:
  p=Providers(OUT,log);p.setup_memory()
  facts={"root_witness_sha256":"417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa",
   "verified_best":226,"exact_root_remove_up_to":4,"neutral_one_for_one_component_size":2,
   "selected_larger_repair_pools_independently_checked":512,
   "scope":"All prior negatives are local. No global optimality or 227 code established.",
   "new_hypothesis":"Maintain 227 distinct words with conflicts, cross invalid states using tabu/breakout, and accept only a zero-energy proposal passing both protected verifiers."}
  source=p.write("analyst","phase3_barrier_hypothesis",facts,"phase3-infeasible-probe")
  try:save("researcher_recall.json",recalled(p.read("researcher","Recall CodeGarden phase3_barrier_hypothesis about escaping the exact local barrier through infeasible 227-word states.",source),source))
  except Exception as e:save("researcher_recall_failure.json",{"error":str(e),"source":source,"used_as_evidence":False})
  queries=[
   "Binary two-deletion-correcting codes length 16 largest known cardinality construction 226 227 November 2026",
   "research paper binary deletion correcting codes n=16 two deletion maximum size computational lower upper bounds",
   "Dynamic Local Search for Maximum Clique DLS-MC Pullan Hoos vertex penalties 2006",
   "The breakout method escaping local minima Morris 1993 constraint satisfaction local search adaptive weights"]
  searches=[];reads=[]
  for i,q in enumerate(queries):
   answer=p.exa(q,"phase3-record-audit" if i<2 else "phase3-penalty-methods");searches.append(answer);save("searches.json",searches)
   for s in answer["sources"][:2]:
    try:
     req=urllib.request.Request(s["url"],headers={"User-Agent":"CodeGarden research provenance"})
     with urllib.request.urlopen(req,timeout=20) as response:raw=response.read(700000)
     text=raw.decode("utf-8","replace");abstract=re.search(r'<blockquote[^>]*class=["\'][^"\']*abstract[^>]*>(.*?)</blockquote>',text,re.S|re.I)
     plain=re.sub("<[^>]+>"," ",abstract.group(1) if abstract else text);plain=" ".join(plain.split())
     match=next((m for term in ["penalt","breakout","Abstract","local search","two-deletion"] if (m:=re.search(re.escape(term),plain,re.I))),None)
     at=match.start() if match else 0
     reads.append({"url":s["url"],"response_sha256":hashlib.sha256(raw).hexdigest(),"bounded_excerpt":" ".join(plain[at:].split()[:15]),
      "limitation":"Excerpt is evidence for manual review, not an automatic record claim or a reproduced construction."})
    except Exception as e:reads.append({"url":s["url"],"error_type":type(e).__name__})
    save("primary_reads.json",reads)
  method={"searches":searches,"primary_reads":reads,"hypothesis":facts["new_hypothesis"],"borrowed_vs_new":"Tabu and adaptive-penalty ideas are literature methods. Their descendant-occupancy implementation here is our adaptation, not a faithful reproduction or a new mathematical theorem.",
   "record_claim":"No new global record inferred from search snippets; leading explicit witnesses and actual conventions must be verified.",
   "decision":"Compare unweighted tabu, constraint breakout penalties, noisy repair and hybrid perturbations; use durable verified results to choose follow-up."}
  methodsource=p.write("researcher","phase3_record_and_penalty_methods",method,"phase3-hypothesis-selection",[source])
  try:
   actual=recalled(p.read("strategist","Recall CodeGarden phase3_record_and_penalty_methods with current record evidence and dynamic penalty alternatives for the next batch.",methodsource),methodsource)
   save("strategist_recall.json",actual)
  except Exception as e:save("strategist_recall_failure.json",{"error":str(e),"source":methodsource,"used_as_evidence":False})
  status.update({"status":"completed","queries":len(searches),"sources_reviewed":sum(len(s["sources"]) for s in searches),"source_ids":[source,methodsource],
   "role_execution":"Distinct memory author identities in one serialized software process; not independent LLM scientists."})
 except Exception as e:status.update({"status":"failed_or_partial","error":str(e)});traceback.print_exc()
 finally:
  status["budget"]=p.ledger.summary() if p else None;status["finished_at"]=dt.datetime.now(dt.timezone.utc).isoformat();save("status.json",status);print("PHASE3_RESEARCH "+json.dumps(status),flush=True)
if __name__=="__main__":main()
