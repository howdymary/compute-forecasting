"""A bounded research cycle with real recalled content in the proposer context.

Roles execute serially in one orchestrator. They are not separately spawned
assistant processes. Local artifacts, never memory entries, authorize scores.
"""
import hashlib,json,os,pathlib,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from providers import Providers
from integrations.tinker_policy import Policy,ACTIONS
from supervisor import verify
import search as S
def evidence(recall,required):
    chunks=[r for r in recall.get("results",[]) if any(s.get("sourceId")==required for s in r.get("sources",[]))]
    if not chunks:raise ValueError("Required cross-role source missing")
    contents=[{k:v for k,v in r.items() if k!="sources"} for r in chunks]
    raw=json.dumps(contents,sort_keys=True)
    return {"source_id":required,"retrieved_content":raw[:2200],
      "retrieved_content_sha256":hashlib.sha256(raw.encode()).hexdigest(),
      "truncated":len(raw)>2200}
def main():
    out=ROOT/"artifacts/feedback";out.mkdir(parents=True,exist_ok=True);events=[]
    def log(kind,value):
        events.append({"kind":kind,"value":value,"time":time.time()})
        (out/"trace.json").write_text(json.dumps(events,indent=2))
        print("FEEDBACK_EVENT "+json.dumps({"kind":kind,"summary":{k:v for k,v in value.items() if k not in {"sources","retrieved_content"}}}),flush=True)
    p=Providers(out,log);status={"status":"running","source_sha":os.getenv("GITHUB_SHA")}
    try:
        p.setup_memory()
        native=json.loads((ROOT/"artifacts/native/report.json").read_text());best=verify(ROOT/"artifacts/best_code.txt")
        fact={"incumbent":best,"iterations":sum(w["iterations"] for w in native["workers"]),
          "strict_improvements":0,"best_sizes":[w["fresh_host_verification"]["cardinality"] for w in native["workers"]],
          "observation":"Fixed and UCB-style switching both retained 226; zero best-improvement rewards give no evidence of learned exhaustion.",
          "next_question":"Use source-backed exact or ejection neighborhoods rather than equating switching with success."}
        analyst_id=p.write("analyst","native_plateau_analysis",fact,"feedback-002")
        recalled=evidence(p.read("researcher","Recall the analyst's native plateau analysis with 2295850 iterations and zero best improvements.",analyst_id),analyst_id)
        query="binary deletion correcting codes maximum independent set plateau exact large neighborhood ejection chain set packing"
        sources=p.exa(query,"feedback-repair-002")
        method={"analyst_evidence":recalled,"sources":sources,
          "analysis":"A conflict-graph or set-packing representation permits bounded exact and ejection repairs. Test one operator under a new fixed seed; no source guarantees improvement.",
          "attribution":"Representation borrowed/adapted from retrieved research; the proposed experiment is CodeGarden's hypothesis."}
        researcher_id=p.write("researcher","plateau_repair_method",method,"feedback-repair-002",[analyst_id])
        actual=evidence(p.read("strategist","Recall the researcher's plateau repair method and the analyst evidence it used.",researcher_id),researcher_id)
        state={"length":16,"verified_best":best["cardinality"],"stagnation_cycles":fact["iterations"],
          "recalled_researcher_evidence":actual,"evidence_sources":[{"title":s["title"],"url":s["url"]} for s in sources["sources"]],
          "budget":"30 CPU seconds for one selected operator, fresh seed 93017, fixed starting code"}
        (out/"decision_context.json").write_text(json.dumps(state,indent=2))
        decision=Policy(p.ledger).choose(state);selected=ACTIONS.index(decision["action"]) if decision["valid_action"] else 3
        decision.update({"used_action":ACTIONS[selected],"explicit_fallback":not decision["valid_action"],
          "memory_source":researcher_id,"context_path":"codegarden/artifacts/feedback/decision_context.json"})
        log("memory_informed_tinker_decision",decision)
        plan_id=p.write("strategist","feedback_experiment_plan",{"decision":decision,"seconds":30,"seed":93017,
          "incumbent_witness_sha256":best["reports"][0]["witness_sha256"]},"feedback-repair-002",[researcher_id])
        arm=S.ARMS[selected];others=[a for i,a in enumerate(S.ARMS) if i!=selected];S.ARMS=others[:1]+[arm]+others[1:]
        inc=S.Incidence(16);start=[int(w,2) for w in (ROOT/"artifacts/best_code.txt").read_text().splitlines()]
        result=S.run(inc,start,93017,seconds=30,max_cycles=100000,policy="fixed")
        words=[format(w,"016b") for w in result["best"]];path=out/"worker_feedback.txt"
        path.write_text("\n".join(sorted(words))+"\n");result["independent_verification"]=verify(path)
        result["selected_action"]=ACTIONS[selected];result["source_sha"]=os.getenv("GITHUB_SHA")
        (out/"experiment.json").write_text(json.dumps(result))
        actual_plan=evidence(p.read("analyst","Recall the strategist's feedback experiment plan, used action and 30-second limit.",plan_id),plan_id)
        result_id=p.write("analyst","feedback_verified_result",{"verification":result["independent_verification"],
          "selected_action":ACTIONS[selected],"experiment_path":"codegarden/artifacts/feedback/experiment.json",
          "recalled_plan":actual_plan,"conclusion":"No unsearched neighborhood is ruled out."},"feedback-repair-002",[plan_id])
        read_result=evidence(p.read("researcher","Recall the analyst's feedback verified result and selected action.",result_id),result_id)
        (out/"last_recalled_result.json").write_text(json.dumps(read_result,indent=2))
        status.update({"status":"completed","best_verified":result["independent_verification"]["cardinality"],
          "decision":decision,"memory_authors":["codegarden-analyst","codegarden-researcher","codegarden-strategist"],
          "execution_model":"Serialized logical roles, not independently spawned assistant agents."})
    except Exception as e:
        status.update({"status":"failed_or_partial","error_type":type(e).__name__,"error":str(e)[:500]});traceback.print_exc()
    finally:
        status["budget"]=p.ledger.summary();(out/"status.json").write_text(json.dumps(status,indent=2))
        print("FEEDBACK_FINAL "+json.dumps(status),flush=True)
if __name__=="__main__":main()
