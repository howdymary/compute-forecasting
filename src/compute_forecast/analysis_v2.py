"""Additional training-selected control and paired descriptive sensitivity analyses."""
from __future__ import annotations
import itertools,json,os,statistics,uuid
from pathlib import Path
import modal
from .campaign_v2 import now,write,digest,REGISTRY
from .policy_v2 import make_tasks,finish,summary,INITIAL
app=modal.App("compute-forecast-v2-analysis")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
def select_static(training):
    import numpy as np
    if any(t["phase"]!="training" for t in training):raise ValueError("Static control may use training only")
    candidates=sorted(c["id"] for c in REGISTRY if c["id"] not in INITIAL)
    combos=np.asarray(list(itertools.combinations(range(len(candidates)),4)),dtype=np.int16)
    total=np.zeros(len(combos));weights=0
    for t in training:
        ids=INITIAL+candidates;val=np.array([t["validation"][c]["loss"] for c in ids]);future=np.array([t["future_evaluator_only"][c]["loss"] for c in ids]);n=t["future_evaluator_only"][ids[0]]["cells"]
        choices=np.concatenate((np.tile(np.arange(2),(len(combos),1)),combos+2),axis=1)
        winner=choices[np.arange(len(combos)),np.argmin(val[choices],axis=1)]
        total+=future[winner]*n;weights+=n
    best=int(np.argmin(total))
    return [candidates[int(i)] for i in combos[best]],{"portfolios_considered":len(combos),"training_objective_pinball":float(total[best]/weights),"selection_uses_evaluation":False,"criterion":"Exhaustive four-additional-config portfolio minimizes training subsequent forecast loss under the unchanged validation-based final chooser"}
def paired(a,b):
    origins=sorted({r["origin"] for r in a["traces"]})
    def score(rows):return sum(r["pinball"]*r["n_cells"] for r in rows)/sum(r["n_cells"] for r in rows)
    dates=[]
    for o in origins:
        aa=[r for r in a["traces"] if r["origin"]==o];bb=[r for r in b["traces"] if r["origin"]==o]
        dates.append({"origin":o,"candidate_pinball":score(aa),"starting_pinball":score(bb),"delta":score(aa)-score(bb)})
    leave=[]
    for o in origins:
        aa=[r for r in a["traces"] if r["origin"]!=o];bb=[r for r in b["traces"] if r["origin"]!=o]
        leave.append({"excluded_origin":o,"candidate_minus_starting":score(aa)-score(bb)})
    return {"by_origin":dates,"leave_one_origin_out":leave,"uncertainty_interpretation":"Descriptive sensitivity over three dependent dates, not a population confidence interval"}
@app.function(image=image,cpu=.25,memory=512,timeout=120,volumes={"/public":public})
def publish(result):
    public.reload();write(Path("/public/experimental-v2/analysis.json"),result);public.commit();return {"sha256":digest(result)}
@app.local_entrypoint()
def main(inputs:str="inputs"):
    from scipy.stats import spearmanr
    root=Path(inputs);grid=json.loads(next(root.rglob("grid.json")).read_text());tasks,excluded=make_tasks(grid)
    training=[t for t in tasks if t["phase"]=="training"];evaluation=[t for t in tasks if t["phase"]=="evaluation"]
    portfolio,selection=select_static(training)
    control=summary("training_outcome_selected_static",[finish(t,INITIAL+portfolio) for t in evaluation])
    alignment=[]
    for t in training:
        ids=[c["id"] for c in REGISTRY];x=[t["validation"][c]["loss"] for c in ids];y=[t["future_evaluator_only"][c]["loss"] for c in ids]
        correlation=float(spearmanr(x,y).statistic) if len(set(x))>1 and len(set(y))>1 else None
        winner=min(ids,key=lambda c:t["validation"][c]["loss"])
        alignment.append({"task_id":t["task_id"],"origin":t["origin"],"validation_future_rank_correlation":correlation,"validation_oracle_future_loss":t["future_evaluator_only"][winner]["loss"],"starting_reference_future_loss":t["future_evaluator_only"][INITIAL[0]]["loss"]})
    policies=[]
    for path in root.rglob("policy-report.json"):
        report=json.loads(path.read_text());folder=path.parent;a=json.loads((folder/"trained-evaluation.json").read_text());b=json.loads((folder/"starting-evaluation.json").read_text())
        parent_file=folder/"sft-parent-evaluation.json"
        reference=json.loads(parent_file.read_text()) if report["mode"]=="rl" and parent_file.is_file() else b
        ablations=[]
        for name,filename in (("no_observation","no-observation.json"),("with_criticism","with-criticism.json"),("with_evidence","with-evidence.json")):
            file=folder/filename
            if not file.is_file():continue
            variant=json.loads(file.read_text());indexed={t["task_id"]:t for t in variant["traces"]}
            pairs=[(t,indexed[t["task_id"]]) for t in a["traces"] if t["task_id"] in indexed]
            ablations.append({"condition":name,"pinball":variant["pinball"],"delta_vs_primary_condition":variant["pinball"]-a["pinball"],"tasks":len(pairs),"tasks_with_changed_action_sequence":sum(x["revealed"]!=y["revealed"] for x,y in pairs),"tasks_with_changed_selected_forecaster":sum(x["selected_config_id"]!=y["selected_config_id"] for x,y in pairs),"interpretation":"Descriptive action and outcome changes on the same small retrospective cases"})
        policies.append({"run_id":report["run_id"],"seed":report["seed"],"objective":report["objective"],"mode":report["mode"],"actual_optimizer_updates":report["actual_optimizer_updates"],"selected_update":report["selected_update"],"paired":paired(a,reference),"reference_policy":"sft_parent" if report["mode"]=="rl" and parent_file.is_file() else "starting_policy","reference_pinball":reference["pinball"],"candidate_pinball":a["pinball"],"starting_pinball":b["pinball"],"delta":a["pinball"]-reference["pinball"],"delta_vs_starting":a["pinball"]-b["pinball"],"relative_delta":a["pinball"]/reference["pinball"]-1 if reference["pinball"] else None,"checkpoints":report["checkpoints"],"rl_gate":report.get("rl_gate"),"ablations":ablations})

    grouped=[]
    for kind,objective in sorted({(p["mode"],p["objective"]) for p in policies}):
        ps=[p for p in policies if p["mode"]==kind and p["objective"]==objective];d=[p["delta"] for p in ps]
        grouped.append({"mode":kind,"objective":objective,"reference_policy":ps[0]["reference_policy"],"seeds":[p["seed"] for p in ps],"mean_candidate_pinball":statistics.mean(p["candidate_pinball"] for p in ps),"mean_paired_delta":statistics.mean(d),"min_paired_delta":min(d),"max_paired_delta":max(d),"interpretation":"Training-seed variation on the same market dates; not additional independent forecast cases"})
    result={"schema_version":2,"created_at":now(),"code_sha":os.environ["GITHUB_SHA"],"grid_sha":grid["code_sha"],"static_portfolio":portfolio,"static_selection":selection,"stronger_static_control":control,"teacher_alignment_training_only":alignment,"policies":policies,"seed_summaries":grouped,"evaluation_temporal_origins":sorted({t["origin"] for t in evaluation}),"evaluation_tasks":len(evaluation),"excluded_tasks":excluded,"limitations":["Retrospective reused data","Three dependent evaluation dates","No confidence interval for a market population is justified by these dates","Exhaustive static control is an additional training-only comparison, not a replacement official submission"]}
    write(Path("artifacts/v2-analysis/analysis.json"),result);result["receipt"]=publish.remote(result)
    print("V2_ANALYSIS:"+json.dumps({k:v for k,v in result.items() if k not in ("stronger_static_control","teacher_alignment_training_only")}),flush=True)
