"""Bounded actual Exa -> past.dev -> Tinker -> experiment -> verification loop."""
import importlib.util,json,os,pathlib,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from providers import Providers
from supervisor import verify
from training_cases import build,act,module,ACTIONS
from integrations.tinker_policy import Policy,train
from integrations.modal_workers import run_workers
from search import Incidence,canonical
def main():
    out=ROOT/"artifacts/live";out.mkdir(parents=True,exist_ok=True);events=[]
    def log(kind,value):
        events.append({"kind":kind,"value":value,"time":time.time()})
        (out/"trace.json").write_text(json.dumps(events,indent=2))
        print("CODEGARDEN_EVENT "+json.dumps({"kind":kind,"summary":{k:v for k,v in value.items() if k not in {"sources","words"}}}),flush=True)
    providers=Providers(out,log);status={"status":"running","scope":"codegarden","source_sha":os.getenv("GITHUB_SHA"),"events":events}
    sampler=None
    try:
        baseline=ROOT/"artifacts/best_code.txt";baseline_report=verify(baseline);words=baseline.read_text().splitlines()
        providers.setup_memory()
        finding=providers.write("analyst","scoped_negative",{
          "incumbent":baseline_report,"finding":"Twenty-one exact explicit-union repairs did not improve their better input; 6200 hosted local cycles retained 226.",
          "scope":"Only logged unions/neighborhoods; no global impossibility claim.","next_question":"Test larger sparse set-packing repairs rather than repeating exhausted small unions."},"negative-001")
        providers.read("researcher","What did the CodeGarden analyst learn about exhausted union repairs and the 226-word incumbent?",finding)
        cached=ROOT/"artifacts/live_attempt1/trace.json"
        old=json.loads(cached.read_text()) if cached.exists() else []
        prior=next((e["value"] for e in old if e["kind"]=="exa_search"),None)
        if prior:
            exa=prior;log("exa_reuse",{"source_run":"43671948159","request_id":prior["request_id"],
              "query":prior["query"],"influenced_experiment":"modal-repair-001"})
        else:
            exa=providers.exa("binary two deletion correcting codes length 16 maximum independent set variable neighborhood exact set packing CP-SAT","modal-repair-001")
        sampler=Policy(providers.ledger)
        decision=sampler.choose({"length":16,"verified_best":226,"scoped_failure":"21 explicit unions have no improvement",
           "evidence_sources":[{"title":s["title"],"url":s["url"]} for s in exa["sources"]],
           "question":"Choose a different bounded repair neighborhood after the analyst's recalled finding."})
        if not decision["valid_action"]:raise ValueError("Untrained strategist returned an invalid bounded action")
        selected=ACTIONS.index(decision["action"])
        log("tinker_strategy",{**decision,"used_memory_source":finding,"experiment_id":"modal-repair-001"})
        method=providers.write("researcher","source_backed_method",{"exa":exa,"hypothesis":"Larger structural/opportunity repairs may escape small union optima",
          "selected_action":decision["action"],"borrowed_method":"set packing / independent-set neighborhood search",
          "not_a_discovery":True},"modal-repair-001",[finding])
        providers.read("strategist","Which source-backed CodeGarden repair method followed the analyst's failure finding?",method)
        plan=providers.write("strategist","experiment_plan",{"action":decision["action"],"seeds":[1701,2901],"seconds_per_worker":60,
          "resources":"two independent CPU workers; independent exported-witness verification",
          "why":"Actual recalled researcher evidence and bounded Tinker action, rather than a repeated union search."},"modal-repair-001",[method])
        reports=run_workers(words,[1701,2901],60,providers.ledger,selected)
        for r in reports["workers"]:
            path=out/("modal_"+str(r["run_id"])+".txt");path.write_text("\n".join(r["words"])+"\n")
            r["fresh_external_verification"]=verify(path)
        (out/"modal_reports.json").write_text(json.dumps(reports,indent=2))
        providers.read("analyst","What experiment did the CodeGarden strategist schedule from the researcher's finding?",plan)
        result_id=providers.write("analyst","verified_result",{"best":max(r["best_size"] for r in reports["workers"]),
          "workers":[{"seed":seed,"verification":r["fresh_external_verification"]} for seed,r in zip([1701,2901],reports["workers"])],
          "conclusion":"Only a bounded empirical result, never a proof of exhausted global search."},"modal-repair-001",[plan])
        providers.read("researcher","What verified result did the analyst obtain from the strategist's repair experiment?",result_id)
        providers.exa("binary two deletion correcting code length 16 226 227 latest explicit construction","record-check-001")
        corpus=build();(out/"training_cases.json").write_text(json.dumps(corpus))
        held=[c for c in corpus["cases"] if c["split"]=="heldout"];training=[c for c in corpus["cases"] if c["split"]=="train"]
        instances={n:Incidence(n) for n in [10,11,12]}
        def evaluate(policy):
            rows=[]
            for c in held:
                d=policy.choose(c["state"])
                index=ACTIONS.index(d["action"]) if d["valid_action"] else None
                code=[int(w,2) for w in c["starting_words"]]
                if index is None:
                    rows.append({"case_id":c["case_id"],"valid_action":False,"final_cardinality":len(code)})
                else:
                    candidate,r=act(instances[c["length"]],code,index,c["seed"]*100+index)
                    rows.append({"case_id":c["case_id"],"valid_action":True,"decision":d,"final_cardinality":len(candidate),"verification":r})
            return rows
        before=evaluate(sampler)
        (out/"untrained_evaluation.json").write_text(json.dumps(before))
        trained=train(training,providers.ledger,updates=8)
        path=trained.pop("checkpoint");trained["checkpoint_sha256"]=__import__("hashlib").sha256(path.encode()).hexdigest()
        (out/"training.json").write_text(json.dumps(trained))
        after_policy=Policy(providers.ledger,sampler_path=path)
        after=evaluate(after_policy)
        evaluation={"scope":"n=10,11,12 heldout strategy calibration; not a length-16 improvement",
          "before":before,"after":after,"train_cases":32,"heldout_cases":8,"updates":8,
          "sum_before":sum(r["final_cardinality"] for r in before),"sum_after":sum(r["final_cardinality"] for r in after),
          "equal_action_budget":"One selected bounded repair per heldout case; identical starting codes/seeds and pool limits"}
        evaluation["improved"]=evaluation["sum_after"]>evaluation["sum_before"]
        (out/"tinker_evaluation.json").write_text(json.dumps(evaluation,indent=2))
        status.update({"status":"completed","modal_best":max(r["best_size"] for r in reports["workers"]),"tinker":evaluation})
    except Exception as e:
        status.update({"status":"failed_or_partial","error_type":type(e).__name__,"error":str(e)[:600]})
        print("CODEGARDEN_PARTIAL "+json.dumps({k:v for k,v in status.items() if k!="events"}),flush=True)
        traceback.print_exc()
    finally:
        status["budget"]=providers.ledger.summary()
        (out/"status.json").write_text(json.dumps(status,indent=2))
        print("CODEGARDEN_FINAL "+json.dumps({k:v for k,v in status.items() if k not in {"events","tinker"}}),flush=True)
    return 0 # partial results are intentionally retained, never advertised as success
if __name__=="__main__":sys.exit(main())
