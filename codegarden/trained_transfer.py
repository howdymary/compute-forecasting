"""Hash-identify the existing private sampler checkpoint and test n=16 transfer.

Only one bounded sampling call is reserved. The baseline is the captured untrained
decision, with identical context, start code, seed and search-time cap.
"""
import hashlib,json,os,pathlib,sys,traceback
ROOT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from providers import Ledger
from supervisor import verify
from integrations.tinker_policy import Policy,ACTIONS
import search as S
def main():
    import tinker
    out=ROOT/"artifacts/transfer";out.mkdir(parents=True,exist_ok=True);ledger=Ledger(out)
    report={"status":"running","source_sha":os.getenv("GITHUB_SHA"),"model_calls":0}
    try:
        expected=json.loads((ROOT/"artifacts/live/training.json").read_text())["checkpoint_sha256"]
        service=tinker.ServiceClient(display_name="CodeGarden checkpoint lookup, read only")
        rest=service.create_rest_client();path=None
        for offset in [0,100]:
            runs=rest.list_training_runs(limit=100,offset=offset).result().training_runs
            for run in runs:
                checkpoint=run.last_sampler_checkpoint
                if checkpoint and hashlib.sha256(checkpoint.tinker_path.encode()).hexdigest()==expected:
                    path=checkpoint.tinker_path;break
            if path or len(runs)<100:break
        if not path:raise ValueError("Existing private checkpoint hash not found; no training or fallback model is allowed")
        state=json.loads((ROOT/"artifacts/feedback/decision_context.json").read_text())
        decision=Policy(ledger,sampler_path=path).choose(state);report["model_calls"]=1
        report["decision"]=decision;report["checkpoint_sha256"]=expected
        original=json.loads((ROOT/"artifacts/feedback/trace.json").read_text())
        before=next(e["value"] for e in original if e["kind"]=="memory_informed_tinker_decision")
        assert decision["state_sha256"]==before["state_sha256"]
        report["identical_context_sha256"]=decision["state_sha256"]
        selected=ACTIONS.index(decision["action"]) if decision["valid_action"] else ACTIONS.index(before["used_action"])
        arm=S.ARMS[selected];others=[a for i,a in enumerate(S.ARMS) if i!=selected];S.ARMS=others[:1]+[arm]+others[1:]
        inc=S.Incidence(16);start=[int(w,2) for w in (ROOT/"artifacts/best_code.txt").read_text().splitlines()]
        result=S.run(inc,start,93017,seconds=30,max_cycles=100000,policy="fixed")
        witness=out/"worker_trained.txt";witness.write_text("\n".join(sorted(format(w,"016b") for w in result["best"]))+"\n")
        result["independent_verification"]=verify(witness);result["used_action"]=ACTIONS[selected]
        (out/"experiment.json").write_text(json.dumps(result))
        baseline=json.loads((ROOT/"artifacts/feedback/experiment.json").read_text())
        report.update({"status":"completed","before":baseline["independent_verification"],
          "after":result["independent_verification"],"before_action":before["used_action"],
          "after_action":ACTIONS[selected],"explicit_fallback":not decision["valid_action"],
          "search_seconds_cap_per_policy":30,"same_seed":93017,
          "comparison":"Same runner job, unchanged search source, same starting code/context/seed and 30-second wall-time caps; stopping-iteration counts can differ.",
          "improved":result["independent_verification"]["cardinality"]>baseline["independent_verification"]["cardinality"]})
    except Exception as e:
        report.update({"status":"failed_or_partial","error_type":type(e).__name__,"error":str(e)[:500]});traceback.print_exc()
    finally:
        report["budget"]=ledger.summary();(out/"status.json").write_text(json.dumps(report,indent=2))
        print("TRANSFER_FINAL "+json.dumps(report),flush=True)
if __name__=="__main__":main()
