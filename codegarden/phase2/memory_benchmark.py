"""Small scoped-decision ablation: actual history, no memory, actual recalled memory."""
import json,time
from common import *
from role import recalled
def run(policy,providers,source_id,packet,manifest):
 root=json.loads((OUT/"root_sweeps.json").read_text());cp=json.loads((ROOT/"artifacts/cp_global.json").read_text())["experiments"][0]
 questions=[]
 for i in range(4):
  r=root[i%2];questions.append({"id":"matched-"+str(i),"query":{"incumbent_sha256":r["incumbent_sha256"],"k":r["k"],"candidate_universe_sha256":r["candidate_universe_sha256"],
   "question":"Should we rerun precisely this completed root exchange enumeration?"},"answer":"reuse_certificate"})
 for i in range(2):
  questions.append({"id":"changed-"+str(i),"query":{"incumbent_sha256":manifest["cases"][-1-i]["starting_sha256"],"k":1,"candidate_universe_sha256":root[0]["candidate_universe_sha256"],
   "question":"Can the recorded root exhaustion certificate be reused for this different incumbent?"},"answer":"run_new_search"})
 for i in range(2):questions.append({"id":"timeout-"+str(i),"query":{"incumbent_sha256":root[0]["incumbent_sha256"],"target":cp["target"],
  "candidate_pool_sha256":cp["candidate_pool_sha256"],"question":"Did the recorded full-universe CP-SAT timeout prove no improvement exists?"},"answer":"no_conclusion"})
 # All history consists of real prior experiment metadata; no synthetic padding.
 history={"scope_facts":packet,"prior_native":[{k:w[k] for k in ["seed","policy","iterations","seconds","best_size_unverified"]} for w in json.loads((ROOT/"artifacts/native/report.json").read_text())["workers"]],
  "prior_greedy":json.loads((ROOT/"demo/data.json").read_text())["greedy"],
  "exact_cp":[{k:e[k] for k in ["status","candidate_pool_sha256","candidate_pool_size","target","seconds_limit"]} for e in json.loads((ROOT/"artifacts/cp_bands.json").read_text())["experiments"]]}
 rows=[];allowed=["reuse_certificate","run_new_search","no_conclusion"]
 for q in questions:
  for mode in ["no_memory","full_history","past"]:
   started=time.perf_counter();context=None;retrieval=None
   if mode=="full_history":context=history
   if mode=="past":
    t=time.perf_counter();actual=providers.read("strategist",json.dumps(q["query"]),source_id)
    retrieval=time.perf_counter()-t;context=recalled(actual,source_id)
   decision=policy.choose({"task":"Scoped negative-result recall. An exhaustion result applies only to the exact incumbent, pool and restrictions. UNKNOWN is not infeasibility.",
    "question":q["query"],"available_evidence":context},allowed=allowed)
   rows.append({"question_id":q["id"],"mode":mode,"expected":q["answer"],"decision":decision,
     "correct":decision["action"]==q["answer"],"retrieval_seconds":retrieval,"total_seconds":time.perf_counter()-started})
   save("memory_benchmark_progress.json",{"rows":rows})
 summary={m:{"accuracy":sum(r["correct"] for r in rows if r["mode"]==m)/8,
  "total_seconds":sum(r["total_seconds"] for r in rows if r["mode"]==m),
  "prompt_tokens":sum(r["decision"]["prompt_tokens"] for r in rows if r["mode"]==m),
  "estimated_model_usd":sum(r["decision"]["estimated_gross_usd"] for r in rows if r["mode"]==m)} for m in ["no_memory","full_history","past"]}
 result={"questions":questions,"rows":rows,"summary":summary,
  "scope":"Eight queries from four matched-root paraphrases, two changed incumbents and two timeout paraphrases; not eight independent mathematical discoveries.",
  "cost_limit":"Model USD estimates and past.dev credits are separate; total combined USD cost is not inferred.",
  "evidence_equivalence":"Full history includes all relevant scope facts. Past uses actually recalled content; no-memory omits prior results by design."}
 save("memory_benchmark.json",result);return result
