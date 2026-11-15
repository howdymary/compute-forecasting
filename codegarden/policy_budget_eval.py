"""Post-hoc matched CPU-budget replay of frozen, actual model action choices.

No model calls or training occur here. This is an ablation of the six previously
held-out decisions, not a fresh model-generalization test.
"""
import json,pathlib,sys,time,random
ROOT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from training_cases import act,ACTIONS
from search import Incidence
def main():
    out=ROOT/"artifacts/live";evaluation=json.loads((out/"tinker_evaluation.json").read_text())
    corpus=json.loads((out/"training_cases.json").read_text());cases={c["case_id"]:c for c in corpus["cases"]}
    instances={n:Incidence(n) for n in [10,11,12]};rows=[];limit=.2
    for i,pre in enumerate(evaluation["before"]):
        post=evaluation["after"][i];assert pre["case_id"]==post["case_id"];case=cases[pre["case_id"]]
        assert case["split"]=="heldout"
        paired={"case_id":case["case_id"],"length":case["length"],"results":{}}
        # Alternate which arm runs first to reduce systematic order effects.
        phases=[("before",pre),("after",post)] if i%2==0 else [("after",post),("before",pre)]
        for phase,decision in phases:
            best=[int(w,2) for w in case["starting_words"]];trials=0;best_verification=None
            chosen=decision.get("decision",{}).get("action")
            start=time.process_time()
            if decision["valid_action"]:
                index=ACTIONS.index(chosen)
                while time.process_time()-start<limit:
                    candidate,report=act(instances[case["length"]],[int(w,2) for w in case["starting_words"]],
                      index,case["seed"]*10000+trials)
                    trials+=1
                    if len(candidate)>=len(best):best=candidate;best_verification=report
            paired["results"][phase]={"action":chosen,"valid_action":decision["valid_action"],
              "best_cardinality":len(best),"actual_search_cpu_seconds":time.process_time()-start,
              "completed_trials":trials,"best_words":[format(w,"0%db"%case["length"]) for w in sorted(best)],
              "verification":best_verification}
        rows.append(paired)
    result={"scope":"Post-hoc matched search-CPU replay of six frozen model decisions; no new model calls or adaptation",
      "cpu_budget_per_case_per_policy":limit,"timing":"Stop before starting the next bounded action; report completion overshoot",
      "rows":rows,"sum_before":sum(r["results"]["before"]["best_cardinality"] for r in rows),
      "sum_after":sum(r["results"]["after"]["best_cardinality"] for r in rows)}
    (out/"fixed_budget_evaluation.json").write_text(json.dumps(result,indent=2))
    print("FROZEN_BUDGET_EVAL "+json.dumps({k:v for k,v in result.items() if k!="rows"}))
if __name__=="__main__":main()
