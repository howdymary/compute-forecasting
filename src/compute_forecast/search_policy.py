"""Train and compare a bounded six-trial research policy on completed experiments."""
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
from datetime import date,timedelta,datetime,timezone
from pathlib import Path
from .representation_study import CONFIGS,TRAIN_TASKS,DEV_TASKS,ORIGINS,PACK_SHA256

MODEL="Qwen/Qwen3.5-4B"
INITIAL=("last_value","last_value_empirical")
CANDIDATES=tuple(c["id"] for c in CONFIGS)
FIXED=("ridge_log_target_only_56_100","ridge_level_target_only_56_100","ridge_log_target_only_28_100","ridge_level_target_only_28_100")

def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
def loss(row):return row["exact_metrics"]["pinball"]

def make_tasks(grid,expected_sha):
    if grid["protocol"]!="representation-study-v2" or grid["code_sha"]!=expected_sha or grid["final_period_opened"] is not False:
        raise ValueError("REFUSED: grid provenance or phase mismatch")
    reports={r["origin"]:r for r in grid["origins"]}
    if set(reports)!=set(ORIGINS):raise ValueError("REFUSED: complete registered temporal grid is required")
    tasks=[];excluded=[]
    for phase,origins in (("training",TRAIN_TASKS),("development",DEV_TASKS)):
        for origin in origins:
            at=date.fromisoformat(origin)
            fold_dates=[(at-timedelta(days=k)).isoformat() for k in (7,14,21)]
            relevant=[reports[d] for d in fold_dates+[origin]]
            if any(r["status"]!="completed" for r in relevant):
                excluded.append({"origin":origin,"phase":phase,"reason":"At least one preregistered catalog fold is ineligible"});continue
            for r in relevant:
                if r["is_synthetic"] or r["dataset_sha256"]!=PACK_SHA256 or r["final_period_opened"] is not False:
                    raise ValueError("REFUSED: invalid numerical source")
            if any(reports[d]["label_end"]>origin for d in fold_dates):raise ValueError("REFUSED: validation outcomes are not mature")
            if phase=="training" and reports[origin]["label_end"]>"2026-07-31":raise ValueError("REFUSED: training crossed July 31")
            index={d:{r["config_id"]:r for r in reports[d]["results"]} for d in fold_dates+[origin]}
            validation={}
            for config in (*INITIAL,*CANDIDATES):
                rows=[index[d][config] for d in fold_dates]
                cells=sum(r["exact_metrics"]["n_cells"] for r in rows)
                if cells<=0:raise ValueError("No scored validation cells")
                validation[config]={"loss":sum(loss(r)*r["exact_metrics"]["n_cells"] for r in rows)/cells,"n_cells":cells,"source_run_ids":[reports[d]["run_id"] for d in fold_dates],"last_label_date":max(reports[d]["label_end"] for d in fold_dates)}
            identifier=hashlib.sha256(("six-trial-v3|"+origin).encode()).hexdigest()[:20]
            tasks.append({"task_id":identifier,"origin":origin,"phase":phase,"observation":reports[origin]["observation"],"validation":validation,"future_evaluator_only":{c:{"loss":loss(r),"n_cells":r["exact_metrics"]["n_cells"]} for c,r in index[origin].items()},"future_source_run_id":reports[origin]["run_id"],"dataset_sha256":PACK_SHA256})
    return tasks,excluded

def model_observation(task,revealed):
    if any(task["validation"][c]["last_label_date"]>task["origin"] for c in revealed):raise ValueError("REFUSED: nonmatured trial")
    scale=max(task["validation"][c]["loss"] for c in INITIAL)
    scale=max(scale,1e-8)
    return {"history_statistics":task["observation"],"trial_budget_total":6,"trials_used":len(revealed),"trials_remaining":6-len(revealed),"observed_trials":[{"config_id":c,"relative_validation_pinball":task["validation"][c]["loss"]/scale,"validation_cells":task["validation"][c]["n_cells"]} for c in revealed],"score_scale":"relative to strongest common-initial loss scale; lower is better"}

def question(task,revealed):
    return "Choose the next untested forecasting experiment. The goal is to find the lowest validation pinball loss under six total trials. Two common baseline trials are already complete. Only matured prior backtests are revealed; future forecast outcomes are unavailable. All candidate forecasts use the same official target and scorer.\n"+json.dumps(model_observation(task,revealed),sort_keys=True)

def choices(task,revealed):
    remaining=[c for c in CANDIDATES if c not in revealed]
    seed=int(hashlib.sha256((task["task_id"]+"|"+"|".join(revealed)).encode()).hexdigest()[:16],16)
    random.Random(seed).shuffle(remaining)
    descriptions={c["id"]:f"Ridge; target representation {c['space']}; auxiliary features {c['aux']}; rolling window {c['days']} calendar days; alpha {c['alpha']}" for c in CONFIGS}
    return [(c,descriptions[c]) for c in remaining]

def finish(task,revealed):
    if len(revealed)!=6 or len(set(revealed))!=6:raise ValueError("Unequal trial budget")
    selected=min(revealed,key=lambda c:task["validation"][c]["loss"])
    measured=task["future_evaluator_only"][selected]
    return {"task_id":task["task_id"],"origin":task["origin"],"selected_config_id":selected,"revealed_configs":revealed,"validation_loss":task["validation"][selected]["loss"],"future_pinball":measured["loss"],"future_cells":measured["n_cells"],"future_source_run_id":task["future_source_run_id"],"trials":6}

def summarize(label,rows):
    cells=sum(r["future_cells"] for r in rows)
    return {"policy":label,"temporal_origins":len(rows),"future_cells":cells,"pooled_pinball":sum(r["future_pinball"]*r["future_cells"] for r in rows)/cells,"mean_origin_pinball":statistics.mean(r["future_pinball"] for r in rows),"trial_budget_per_task":6,"traces":rows}

def demonstrations(tasks):
    examples=[]
    for task in tasks:
        if task["phase"]!="training":raise ValueError("REFUSED: only training tasks produce demonstrations")
        for repeat in range(8):
            order=list(CANDIDATES);random.Random(int(task["task_id"][:8],16)+repeat).shuffle(order)
            for step in range(4):
                revealed=[*INITIAL,*order[:step]]
                best=min((c for c in CANDIDATES if c not in revealed),key=lambda c:(task["validation"][c]["loss"],c))
                examples.append({"task_id":task["task_id"],"phase":"training","origin":task["origin"],"prefix_seed":repeat,"step":step,"revealed":revealed,"model_observation":model_observation(task,revealed),"chosen_config_id":best,"teacher_source_run_ids":task["validation"][best]["source_run_ids"],"teacher_last_label_date":task["validation"][best]["last_label_date"],"dataset_sha256":PACK_SHA256})
    return examples

async def train(tasks,excluded,out,epochs=5):
    import tinker
    from tinker import types
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import Decision,DecisionRenderer,decision_choice_datums,sample_decision
    training=[t for t in tasks if t["phase"]=="training"];development=[t for t in tasks if t["phase"]=="development"]
    if len(training)<4 or len(development)<2:raise ValueError("Insufficient eligible temporal tasks for the main comparison")
    examples=demonstrations(training);write(out/"training-examples.json",examples)
    write(out/"eligibility.json",{"training_origins":[t["origin"] for t in training],"development_origins":[t["origin"] for t in development],"excluded":excluded,"final_period_opened":False})
    service=tinker.ServiceClient(display_name="Compute Forecast: equal-budget experiment selection")
    trainer=await service.create_lora_training_client(base_model=MODEL,rank=16,seed=42)
    tokenizer=trainer.get_tokenizer();renderer=renderers.get_renderer(model_info.get_recommended_renderer_name(MODEL),tokenizer);decision_renderer=DecisionRenderer(renderer)
    indexed={t["task_id"]:t for t in training}
    pairs=[(Decision(question(indexed[e["task_id"]],e["revealed"]),choices(indexed[e["task_id"]],e["revealed"])),e["chosen_config_id"]) for e in examples]
    datums=list(decision_choice_datums(decision_renderer,pairs));comparisons=[];updates=[];checkpoints=[];semaphore=asyncio.Semaphore(4)
    async def evaluate(sampler,label):
        async def episode(task):
            revealed=list(INITIAL);decisions=[]
            for step in range(4):
                observation=model_observation(task,revealed);options=choices(task,revealed)
                started=time.perf_counter()
                async with semaphore:distribution=await sample_decision(sampler,decision_renderer.render(Decision(question(task,revealed),options)))
                if set(distribution)!={c for c,_ in options} or any(not math.isfinite(p) or p<0 for p in distribution.values()):raise ValueError("Invalid bounded action probabilities")
                selected=max((c for c,_ in options),key=lambda c:distribution[c])
                decisions.append({"step":step,"observation":observation,"selected_config_id":selected,"probabilities":distribution,"revealed_validation_result":task["validation"][selected],"runtime_seconds":time.perf_counter()-started})
                revealed.append(selected)
            row=finish(task,revealed);row["decisions"]=decisions;return row
        rows=await asyncio.gather(*(episode(t) for t in development));summary=summarize(label,rows)
        write(out/(label+"-development.json"),summary);comparisons.append(summary);return summary
    base=await service.create_sampling_client(base_model=MODEL);await evaluate(base,"starting_policy")
    for epoch in range(1,epochs+1):
        order=list(range(len(datums)));random.Random(42+epoch).shuffle(order)
        for start in range(0,len(order),32):
            batch=[datums[i] for i in order[start:start+32]]
            forward=trainer.forward_backward(batch,loss_fn="cross_entropy");optim=trainer.optim_step(types.AdamParams(learning_rate=1e-4))
            result=await forward;await optim
            updates.append({"epoch":epoch,"batch_examples":len(batch),"metrics":result.metrics});write(out/"training-updates.json",updates)
        state=await trainer.save_state("search_sft_epoch_"+str(epoch));weights=await trainer.save_weights_for_sampler("search_sft_epoch_"+str(epoch))
        checkpoints.append({"epoch":epoch,"state_path":state.path,"sampler_path":weights.path});write(out/"checkpoints.json",checkpoints)
        sampler=await service.create_sampling_client(model_path=weights.path);await evaluate(sampler,"sft_epoch_"+str(epoch))
    fixed=summarize("fixed_search",[finish(t,[*INITIAL,*FIXED]) for t in development]);comparisons.append(fixed)
    for seed in (42,43,44,45,46):
        rows=[]
        for t in development:
            rng=random.Random(seed+int(t["task_id"][:8],16));rows.append(finish(t,[*INITIAL,*rng.sample(list(CANDIDATES),4)]))
        comparisons.append(summarize("random_seed_"+str(seed),rows))
    references={method:sum(t["future_evaluator_only"][method]["loss"]*t["future_evaluator_only"][method]["n_cells"] for t in development)/sum(t["future_evaluator_only"][method]["n_cells"] for t in development) for method in ("last_value","last_value_empirical","drift","seasonal_naive")}
    selected=min((r for r in comparisons if r["policy"].startswith("sft_")),key=lambda r:r["pooled_pinball"])["policy"]
    report={"schema_version":"1","study_kind":"six_trial_experiment_selection","model":MODEL,"lora_rank":16,"learning_rate":1e-4,"epochs":epochs,"training_examples":len(examples),"training_temporal_origins":len(training),"development_temporal_origins":len(development),"actual_training_updates":len(updates),"trial_budget_per_task":6,"common_initial_trials":INITIAL,"teacher":"Minimum validation loss among untested candidates; only matured training-period experiments","selected_checkpoint_on_development":selected,"selection_is_development_tuning":True,"metric_provenance":"Exact unrounded per-cell losses emitted by the official Pacific scorer","fixed_forecaster_references":references,"comparisons":[{k:v for k,v in r.items() if k!="traces"} for r in comparisons],"checkpoints":checkpoints,"excluded_tasks":excluded,"final_period_opened":False,"training_cost_status":"unavailable","training_cost_value":None,"created_at":datetime.now(timezone.utc).isoformat(),"code_sha":os.environ.get("GITHUB_SHA"),"limitations":["Small and temporally dependent chronological sample","Only eligible afhubbard headline A100/H100 daily-statistics targets","Eight prefixes do not increase independent temporal sample size","Grid is retrospective frozen-vintage data, not proof of historical accessibility","No improvement is assumed; negative results and regressions retained"]}
    write(out/"search-report.json",report)
    for r in comparisons:write(out/(r["policy"]+"-development.json"),r)
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
        f.write("# Genuine six-trial Tinker experiment-selection study\n\n")
        text=json.dumps(report,indent=2)
        for start in range(0,len(text),3000):f.write("~~~json\n"+text[start:start+3000]+"\n~~~\n\n")

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--grid",required=True);parser.add_argument("--expected-source-sha",required=True);parser.add_argument("--output",default="artifacts/search-policy");parser.add_argument("--epochs",type=int,default=5)
    args=parser.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    tasks,excluded=make_tasks(json.loads(Path(args.grid).read_text()),args.expected_source_sha)
    asyncio.run(train(tasks,excluded,out,args.epochs))
