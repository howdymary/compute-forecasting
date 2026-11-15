"""Renewed coordinated research calls; no model training or compute workers."""
import datetime as dt,hashlib,json,os,pathlib,re,sys,traceback,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"phase2"))
from providers import Providers,http,cli
from phase2.role import recalled
OUT=ROOT/"artifacts/phase3/research_002";OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2))
def main():
 spec=json.loads((ROOT/"phase3/renewal_001.json").read_text())
 spec["providers"]["past"]["balance_at_snapshot"]=http("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"])["balance"]["left"]
 # Read-only fresh provider account boundary checks before issuing billable requests.
 modal=json.loads(cli("modal","billing","summary","--json"));save("account_preflight.json",{"at":dt.datetime.now(dt.timezone.utc).isoformat(),
  "authenticated_dashboard_snapshot":spec["authenticated_preflight_at"],"modal_account":modal,"past_remaining":spec["providers"]["past"]["balance_at_snapshot"],
  "provider_caps_unchanged":True,"other_project_reserves_retained":True})
 (ROOT/"budget/shared-allocation.json").write_text(json.dumps(spec,indent=2))
 history=json.loads((ROOT/"phase3/carry_002.json").read_text())
 (ROOT/"budget/historical-usage.json").write_text(json.dumps(history,indent=2))
 events=[];p=None;status={"status":"running","source_sha":os.environ["GITHUB_SHA"],"started_at":dt.datetime.now(dt.timezone.utc).isoformat(),"history":history}
 def log(kind,value):
  events.append({"kind":kind,"value":value,"time":dt.datetime.now(dt.timezone.utc).isoformat()});save("provider_trace.json",events)
  if p:save("ledger_progress.json",p.ledger.summary())
 try:
  p=Providers(OUT,log);p.setup_memory()
  facts={"root_witness_sha256":"417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa","verified_best":226,
   "new_exact_native_finding":{"component_size":32,"neutral_exchange_radius":4,"all_states_no_strict_augmentation_remove_up_to":4,
    "source":"codegarden-bundle-004 artifacts/phase3/bundle_002/neutral4/report.json","scope":"Native enumeration with protected witness checks, independent enumeration audit pending"},
   "incomplete_root_radius5":{"nodes":1000000000,"cpu_seconds":20.1688,"improvement":False,"conclusion":"No improvement within node cap; neighborhood not exhausted"},
   "earlier_227_pair_penalty_search":"Best energy 2, invalid; over 4900 distinct near-states in one Modal worker, no valid 227",
   "hypothesis":"The 226 plateau is rigid under four-word exchanges; use deeper bundles or event-driven breakout rather than repeat exact radii 1-4.",
   "guard":"No global optimality and no record claimed. Every winner must pass both protected verifiers."}
  source=p.write("analyst","phase3_four_exchange_component",facts,"phase3-infeasible-probe")
  try:save("researcher_recall.json",recalled(p.read("researcher","Recall CodeGarden phase3_four_exchange_component about escaping the exact local barrier through infeasible 227-word states.",source),source))
  except Exception as e:save("researcher_recall_failure.json",{"error":str(e),"source":source,"used_as_evidence":False})
  queries=[
   "KaMIS iterated local search maximum independent set plateau escape large dense conflict graphs deletion codes",
   "binary two deletion correcting codes length 16 226 227 best known construction November 2026",
   "Morris breakout method dynamic weights local minima violated constraints adaptive penalty constraint satisfaction"]
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
  method={"searches":searches,"primary_reads":reads,"hypothesis":facts["hypothesis"],"borrowed_vs_new":"Tabu and adaptive-penalty ideas are literature methods. Their descendant-occupancy implementation here is our adaptation, not a faithful reproduction or a new mathematical theorem.",
   "record_claim":"No new global record inferred from search snippets; leading explicit witnesses and actual conventions must be verified.",
   "decision":"Test deeper blocker bundles, event-driven breakout, complete conflict endpoint repair and pinned KaMIS; do not rescan the exhausted radius-four component."}
  methodsource=p.write("researcher","phase3_deeper_method_research",method,"phase3-hypothesis-selection",[source])
  try:
   actual=recalled(p.read("strategist","Recall CodeGarden phase3_deeper_method_research with current record evidence and dynamic penalty alternatives for the next batch.",methodsource),methodsource)
   save("strategist_recall.json",actual)
  except Exception as e:save("strategist_recall_failure.json",{"error":str(e),"source":methodsource,"used_as_evidence":False})
  from phase2.model_policy import Policy
  policy=Policy(p.ledger);decisions=[]
  for context in [
   {"kind":"valid_plateau","size":226,"exact_closed_radius":4,"component_size":32,"radius5":"node-limited"},
   {"kind":"invalid_nearstate","distinct_words":227,"pair_energy":2,"fixed_interval_penalties":"stagnated"},
   {"kind":"valid_different_basin","size":225,"distance_outside_parent":22,"short_valid_polish":"no improvement"}]:
   state={"current":context,"scoped_findings":facts,"actual_recalled_memory":actual if "actual" in locals() else None,"budget":"Choose one 300-CPU-second strategy, no inner-loop model calls"}
   decision=policy.choose(state,["deep_bundle","morris_breakout","defect_closure","kamis_ils"])
   decisions.append({"context":context,"decision":decision});save("strategy_proposals.json",decisions)
  status.update({"status":"completed","queries":len(searches),"sources_reviewed":sum(len(s["sources"]) for s in searches),"source_ids":[source,methodsource],
   "role_execution":"Distinct memory author identities in one serialized software process; not independent LLM scientists."})
 except Exception as e:status.update({"status":"failed_or_partial","error":str(e)});traceback.print_exc()
 finally:
  status["budget"]=p.ledger.summary() if p else None;status["finished_at"]=dt.datetime.now(dt.timezone.utc).isoformat();save("status.json",status);print("PHASE3_RESEARCH "+json.dumps(status),flush=True)
if __name__=="__main__":main()
