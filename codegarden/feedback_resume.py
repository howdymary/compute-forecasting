"""Resume the captured, paid strategy decision without another model/Exa call."""
import hashlib,json,os,pathlib,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from providers import Providers
from supervisor import verify
from integrations.tinker_policy import ACTIONS,prompt
from feedback_cycle import evidence
import search as S
def main():
    out=ROOT/"artifacts/feedback";old=json.loads((out/"status.json").read_text())
    if old["status"]=="completed":
        print("FEEDBACK_RESUME already completed; no calls made");return
    original=json.loads((out/"trace.json").read_text())
    saved=next(e["value"] for e in original if e["kind"]=="memory_informed_tinker_decision")
    state=json.loads((out/"decision_context.json").read_text())
    assert saved["state_sha256"]==hashlib.sha256(prompt(state).encode()).hexdigest()
    assert saved["used_action"] in ACTIONS
    events=[]
    def log(kind,value):
        events.append({"kind":kind,"value":value,"time":time.time()})
        (out/"trace_resume.json").write_text(json.dumps(events,indent=2))
        print("RESUME_EVENT "+json.dumps({"kind":kind}),flush=True)
    p=Providers(out,log);status={"status":"running","source_sha":os.getenv("GITHUB_SHA"),
      "resumed_from_source":old["source_sha"],"saved_decision":saved,"extra_model_calls":0,"extra_exa_calls":0}
    try:
        p.setup_memory();baseline=verify(ROOT/"artifacts/best_code.txt")
        recalled=evidence(p.read("strategist","Recall the researcher's plateau repair method and zero strict improvements.",saved["memory_source"]),saved["memory_source"])
        plan_id=p.write("strategist","resumed_feedback_plan",{"decision":saved,"recalled_method":recalled,"seconds":30,"seed":93017,
          "incumbent_witness_sha256":baseline["reports"][0]["witness_sha256"]},"feedback-repair-002",[saved["memory_source"]])
        selected=ACTIONS.index(saved["used_action"]);arm=S.ARMS[selected]
        others=[a for i,a in enumerate(S.ARMS) if i!=selected];S.ARMS=others[:1]+[arm]+others[1:]
        inc=S.Incidence(16);start=[int(w,2) for w in (ROOT/"artifacts/best_code.txt").read_text().splitlines()]
        result=S.run(inc,start,93017,seconds=30,max_cycles=100000,policy="fixed")
        path=out/"worker_feedback.txt";path.write_text("\n".join(sorted(format(w,"016b") for w in result["best"]))+"\n")
        verified=verify(path);result.update({"independent_verification":verified,"selected_action":saved["used_action"],
          "source_sha":os.getenv("GITHUB_SHA"),"saved_strategy_context_sha256":saved["state_sha256"]})
        (out/"experiment.json").write_text(json.dumps(result))
        plan=evidence(p.read("analyst","Recall the strategist's resumed feedback plan with 30 seconds and seed 93017.",plan_id),plan_id)
        result_id=p.write("analyst","resumed_feedback_result",{"verification":verified,"selected_action":saved["used_action"],
          "recalled_plan":plan,"experiment":"codegarden/artifacts/feedback/experiment.json",
          "scope":"A bounded trajectory, not an impossibility proof."},"feedback-repair-002",[plan_id])
        research=evidence(p.read("researcher","Recall the analyst's resumed feedback result and verified cardinality.",result_id),result_id)
        (out/"last_recalled_result.json").write_text(json.dumps(research,indent=2))
        status.update({"status":"completed","best_verified":verified["cardinality"],
          "execution_model":"Serialized logical roles with actual recalled content; no separately spawned assistant agents."})
    except Exception as e:
        status.update({"status":"failed_or_partial","error_type":type(e).__name__,"error":str(e)[:500]});traceback.print_exc()
    finally:
        status["budget"]=p.ledger.summary();(out/"status.json").write_text(json.dumps(status,indent=2))
        print("FEEDBACK_RESUME_FINAL "+json.dumps({k:v for k,v in status.items() if k!="saved_decision"}))
if __name__=="__main__":main()
