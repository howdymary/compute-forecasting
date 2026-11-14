"""Evaluate frozen policies on five held-out rolling origins; never train here."""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import math
import os
import random
import statistics
import time
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from .freeze_contract import validate_freeze,FINAL_ORIGINS,PACK_SHA
from .representation_study import app,evaluate_origin
from .search_policy import INITIAL,CANDIDATES,FIXED,family_choices,parameter_choices,family_question,parameter_question,forced_choice,finish,summarize


def dump(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")

def final_tasks(reports):
    indexed={r["origin"]:r for r in reports};tasks=[]
    for origin in FINAL_ORIGINS:
        folds=[(date.fromisoformat(origin)-timedelta(days=k)).isoformat() for k in (7,14,21)]
        for d in [*folds,origin]:
            r=indexed[d]
            if r["status"]!="completed" or r["is_synthetic"] or r["dataset_sha256"]!=PACK_SHA or r["final_period_opened"] is not True:
                raise ValueError("REFUSED: missing or ineligible frozen-final numerical case")
        if any(indexed[d]["label_end"]>origin for d in folds):raise ValueError("REFUSED: unmatured backtest revealed to final policy")
        lookup={d:{r["config_id"]:r for r in indexed[d]["results"]} for d in [*folds,origin]}
        validation={}
        for c in (*INITIAL,*CANDIDATES):
            cells=sum(lookup[d][c]["exact_metrics"]["n_cells"] for d in folds)
            validation[c]={"loss":sum(lookup[d][c]["exact_metrics"]["pinball"]*lookup[d][c]["exact_metrics"]["n_cells"] for d in folds)/cells,"n_cells":cells,"source_run_ids":[indexed[d]["run_id"] for d in folds],"last_label_date":max(indexed[d]["label_end"] for d in folds)}
        tasks.append({"task_id":hashlib.sha256(("frozen-final|"+origin).encode()).hexdigest()[:20],"origin":origin,"phase":"final","observation":indexed[origin]["observation"],"validation":validation,"future_evaluator_only":{c:{"loss":r["exact_metrics"]["pinball"],"n_cells":r["exact_metrics"]["n_cells"]} for c,r in lookup[origin].items()},"future_source_run_id":indexed[origin]["run_id"],"dataset_sha256":PACK_SHA})
    return tasks


def paired_block_interval(trained,starting):
    # Circular moving blocks preserve some adjacent-origin dependence.
    before={r["origin"]:r["future_pinball"] for r in starting["traces"]}
    differences=[r["future_pinball"]-before[r["origin"]] for r in sorted(trained["traces"],key=lambda r:r["origin"])]
    rng=random.Random(42);draws=[];n=len(differences)
    for _ in range(2000):
        sample=[]
        while len(sample)<n:
            start=rng.randrange(n);sample.extend(differences[(start+k)%n] for k in range(2))
        draws.append(statistics.mean(sample[:n]))
    draws.sort()
    return {"quantity":"Mean-origin trained minus starting pinball; negative favors trained","observed_mean_difference":statistics.mean(differences),"lower_percentile_2_5":draws[49],"upper_percentile_97_5":draws[1949],"temporal_origins":n,"block_length":2,"resamples":2000,"seed":42,"interpretation":"Exploratory percentile interval on five dependent origins, not a calibrated generalization guarantee."}


async def evaluate_saved(tasks,freeze,out):
    import tinker
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import Decision,DecisionRenderer,sample_decision
    service=tinker.ServiceClient(display_name="Compute Forecast: frozen final evaluation, no training")
    starting=await service.create_sampling_client(base_model=freeze["policy_model"])
    trained=await service.create_sampling_client(model_path=freeze["policy_checkpoint"])
    renderer=renderers.get_renderer(model_info.get_recommended_renderer_name(freeze["policy_model"]),trained.get_tokenizer())
    rendered=DecisionRenderer(renderer);semaphore=asyncio.Semaphore(4);calls=[];forced=[]
    async def evaluate(sampler,label):
        async def select(prompt,options,stage):
            started=time.perf_counter();mandatory=forced_choice(options)
            if mandatory is not None:
                forced.append({"policy":label,"stage":stage,"selected_action":mandatory})
                return mandatory,{mandatory:1.0},"forced_single_remaining",time.perf_counter()-started
            async with semaphore:distribution=await sample_decision(sampler,rendered.render(Decision(prompt,options)))
            if set(distribution)!={c for c,_ in options} or any(not math.isfinite(p) or p<0 for p in distribution.values()):raise ValueError("Invalid final policy distribution")
            selected=max((c for c,_ in options),key=lambda c:distribution[c]);elapsed=time.perf_counter()-started
            calls.append({"policy":label,"stage":stage,"runtime_seconds":elapsed,"options":len(options)})
            return selected,distribution,"model",elapsed
        async def one(task):
            revealed=list(INITIAL);trace=[]
            for step in range(4):
                family,fp,fmode,ft=await select(family_question(task,revealed),family_choices(task,revealed),"family")
                choice,cp,cmode,ct=await select(parameter_question(task,revealed,family),parameter_choices(task,revealed,family),"parameters")
                trace.append({"step":step,"selected_family_id":family,"family_probabilities":fp,"family_selection_mode":fmode,"selected_config_id":choice,"probabilities":cp,"parameter_selection_mode":cmode,"revealed_validation_result":task["validation"][choice],"runtime_seconds":ft+ct})
                revealed.append(choice)
            row=finish(task,revealed);row["decisions"]=trace;return row
        rows=await asyncio.gather(*(one(t) for t in tasks));summary=summarize(label,rows);dump(out/(label+"-final.json"),summary);return summary
    comparisons=[await evaluate(starting,"starting_policy"),await evaluate(trained,"frozen_trained_policy")]
    comparisons.append(summarize("fixed_search",[finish(t,[*INITIAL,*FIXED]) for t in tasks]))
    for seed in (42,43,44,45,46):
        rows=[]
        for t in tasks:
            rng=random.Random(seed+int(t["task_id"][:8],16));rows.append(finish(t,[*INITIAL,*rng.sample(list(CANDIDATES),4)]))
        comparisons.append(summarize("random_seed_"+str(seed),rows))
    references={c:sum(t["future_evaluator_only"][c]["loss"]*t["future_evaluator_only"][c]["n_cells"] for t in tasks)/sum(t["future_evaluator_only"][c]["n_cells"] for t in tasks) for c in ("last_value","last_value_empirical","drift","seasonal_naive")}
    baseline=references["last_value"]
    for row in comparisons:row["skill_vs_last_value"]=1-row["pooled_pinball"]/baseline if baseline>0 else None
    report={"schema_version":"1","study_kind":"frozen_final_six_trial_policy_evaluation","dataset_sha256":PACK_SHA,"final_origins":list(FINAL_ORIGINS),"temporal_origins":len(tasks),"trial_budget_per_task":6,"selected_checkpoint_label":freeze["policy_checkpoint_label"],"selected_checkpoint":freeze["policy_checkpoint"],"policy_model":freeze["policy_model"],"frozen_at":freeze["frozen_at"],"policy_training_run_id":freeze["policy_training_run_id"],"comparisons":[{k:v for k,v in r.items() if k!="traces"} for r in comparisons],"forecaster_references":references,"paired_block_bootstrap":paired_block_interval(comparisons[1],comparisons[0]),"completed_model_decisions":len(calls),"forced_single_option_actions":len(forced),"training_updates":0,"final_period_opened":True,"current_web_evidence_used_in_forecasts":False,"scope":"Official eligible afhubbard headline H100/A100 daily-statistics targets; targets unchanged","cost_status":"unavailable","cost_value":None,"created_at":datetime.now(timezone.utc).isoformat(),"code_sha":os.environ.get("GITHUB_SHA"),"limitations":["Five dependent rolling origins, not millions of independent cases","Later final decisions may read matured earlier outcomes; weights and selection procedure remain frozen","Retrospective frozen data vintage does not prove historical accessibility","Model pretraining knowledge cannot be completely excluded despite date/SKU masking","Exploratory bootstrap has very limited effective sample size"]}
    dump(out/"final-report.json",report);dump(out/"model-call-timing.json",calls);dump(out/"forced-actions.json",forced)
    for row in comparisons:dump(out/(row["policy"]+"-final.json"),row)
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
        f.write("# Actual frozen final evaluation\n\n")
        text=json.dumps(report,indent=2)
        for start in range(0,len(text),3000):f.write("~~~json\n"+text[start:start+3000]+"\n~~~\n\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--freeze",default="configs/release-freeze.json");parser.add_argument("--output",default="artifacts/final-evaluation")
    args=parser.parse_args();freeze=json.loads(Path(args.freeze).read_text());validate_freeze(freeze)
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    dump(out/"freeze-used.json",freeze)
    origins=sorted({(date.fromisoformat(t)-timedelta(days=k)).isoformat() for t in FINAL_ORIGINS for k in (0,7,14,21)})
    started=datetime.now(timezone.utc).isoformat();reports=[]
    with app.run():
        for report in evaluate_origin.map(origins,kwargs={"final_freeze":freeze},order_outputs=False):
            report["code_sha"]=os.environ.get("GITHUB_SHA");reports.append(report)
            dump(out/"final-numerical-grid.json",{"freeze_created_at":freeze["frozen_at"],"first_final_execution_started_at":started,"origins":reports,"final_period_opened":True})
    tasks=final_tasks(reports)
    asyncio.run(evaluate_saved(tasks,freeze,out))
