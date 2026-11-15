"""Hard/soft categorical training and outcome-reward policy gradients for v2."""
from __future__ import annotations
import argparse,asyncio,hashlib,json,math,os,random,statistics,time,uuid
from datetime import date,timedelta
from pathlib import Path
import modal
from .starter_probe import volume,PACK_SHA256
from .campaign_v2 import MODEL,REGISTRY,BY_ID,REFS,protocol,now,write,digest

app=modal.App("compute-forecast-v2-policy")
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
INITIAL=list(REFS[:2])
@app.function(image=image,cpu=.25,memory=512,timeout=90,volumes={"/data":volume})
def retain_private(identifier,payload):
    write(Path("/data/campaign-v2/policies")/(identifier+".json"),payload);volume.commit()
    return {"manifest_id":identifier,"sha256":digest(payload),"private":True}
@app.function(image=image,cpu=.25,memory=512,timeout=90,volumes={"/data":volume})
def load_private(identifier):
    if len(identifier)!=32 or any(c not in "0123456789abcdef" for c in identifier):raise ValueError("Invalid private manifest")
    return json.loads((Path("/data/campaign-v2/policies")/(identifier+".json")).read_text())

def path_for(c):
    family=c["family"]
    if family=="reference":return ("reference",c["id"])
    if family=="ridge":return ("linear","ridge_"+c["space"],c["aux"],c["id"])
    if family=="ar":return ("linear","autoregression",c["id"])
    return ({"ewma":"smoothing","tree":"trees","ensemble":"ensembles","coverage":"diagnostics"}[family],c["id"])
def menu(remaining,prefix=()):
    groups={}
    for identifier in remaining:
        path=path_for(BY_ID[identifier])
        if path[:len(prefix)]==prefix and len(path)>len(prefix):groups.setdefault(path[len(prefix)],[]).append(identifier)
    if not groups:raise ValueError("Empty action menu")
    if len(groups)==1 and len(next(iter(groups.values())))>1:return menu(remaining,(*prefix,next(iter(groups))))
    if len(groups)>6:raise ValueError("Choice count exceeds validated six-token menu")
    return prefix,[(label,ids) for label,ids in sorted(groups.items())]
def aggregate(report,identifier,sids):
    rows=[r for r in next(m for m in report["methods"] if m["config_id"]==identifier)["cases"] if r["series_id"] in sids]
    if not rows:return None
    return {"loss":sum(r["loss"] for r in rows)/len(rows),"cells":len(rows),"cases":rows}
def make_tasks(grid):
    if grid["schema_version"]!=2 or grid["protocol"]!=protocol():raise ValueError("Wrong registered grid")
    reports={r["origin"]:r for r in grid["origins"]};p=protocol();tasks=[];excluded=[]
    for phase,key in (("training","training_origins"),("development","development_origins"),("evaluation","evaluation_origins")):
        for origin in p[key]:
            folds=[(date.fromisoformat(origin)-timedelta(days=k)).isoformat() for k in p["validation_lags_days"]]
            if any(o not in reports or reports[o]["status"]!="completed" for o in [*folds,origin]):
                excluded.append({"origin":origin,"reason":"ineligible official catalog fold"});continue
            if any(reports[o]["label_end"]>origin for o in folds):raise ValueError("Nonmature validation labels")
            if phase=="training" and reports[origin]["label_end"]>p["train_last_label"]:raise ValueError("Training crossed reward boundary")
            groups={}
            for s in reports[origin]["catalog"]:
                group="|".join(s[k] for k in ("source_id","instrument_class","gpu_model","pricing_tier"))
                groups.setdefault(group,set()).add(s["series_id"])
            for group,sids in sorted(groups.items()):
                sids=sids.intersection(*(set(s["series_id"] for s in reports[o]["catalog"]) for o in folds))
                if not sids:continue
                validation={};future={};valid=True
                for c in REGISTRY:
                    identifier=c["id"];parts=[aggregate(reports[o],identifier,sids) for o in folds];f=aggregate(reports[origin],identifier,sids)
                    if f is None or any(v is None for v in parts):valid=False;break
                    n=sum(v["cells"] for v in parts)
                    validation[identifier]={"loss":sum(v["loss"]*v["cells"] for v in parts)/n,"n_cells":n,"last_label_date":max(reports[o]["label_end"] for o in folds)}
                    future[identifier]=f
                if not valid:continue
                audits=[a for a in reports[origin]["series_audit"] if a["series_id"] in sids]
                obs={"n_series":len(sids),"mean_history_observations":statistics.mean(a["observations"] for a in audits),"mean_price_changes":statistics.mean(a["price_changes"] for a in audits),"mean_missing_calendar_days":statistics.mean(a["missing_calendar_days"] or 0 for a in audits),"measurement":"advertised offers; retrospective frozen vintage"}
                task_id=hashlib.sha256((origin+"|"+group).encode()).hexdigest()[:20]
                tasks.append({"task_id":task_id,"origin":origin,"group":group,"phase":phase,"series_ids":sorted(sids),"observation":obs,"validation":validation,"future_evaluator_only":future,"reward_label_end":reports[origin]["label_end"]})
    training=[t for t in tasks if t["phase"]=="training"]
    positive=[v["loss"] for t in training for v in t["future_evaluator_only"].values() if v["loss"]>0]
    scale=statistics.median(positive) if positive else 1.0
    for t in tasks:t["scale"]=max(scale,1e-6)
    return tasks,excluded
def criticism(task,revealed):
    losses=[task["validation"][c]["loss"] for c in revealed]
    winner=min(revealed,key=lambda c:task["validation"][c]["loss"])
    return {"critic_id":digest({"task":task["task_id"],"revealed":revealed})[:16],"author":"bounded_skeptic","objection":"Validation results are tied; try a different numerical family" if max(losses)-min(losses)<1e-8 else "A lower inner-validation loss does not establish later forecast improvement; compare a different family","current_validation_winner":winner,"information_scope":"revealed matured validation only"}
def observation(task,revealed,ablation=None):
    visible={"history_statistics":task["observation"],"trial_budget":6,"trials_used":len(revealed),"trials_remaining":6-len(revealed),"observed_trials":[{"config_id":c,"relative_validation_pinball":task["validation"][c]["loss"]/task["scale"],"n_cells":task["validation"][c]["n_cells"]} for c in revealed]}
    if ablation=="with_criticism":visible["criticism"]=criticism(task,revealed)
    if ablation=="no_observation":visible={"trial_budget":6,"trials_used":len(revealed),"observed_trials":[{"config_id":c} for c in revealed]}
    return visible
def prompt(task,revealed,prefix,ablation=None,evidence=None):
    text="Choose the next untested forecasting experiment under six total numerical trials. Only prior matured validation scores are visible. The final forecaster is the revealed configuration with lowest validation loss. Future reward outcomes are hidden. Select the requested branch of the bounded action menu.\n"
    text+=json.dumps({"state":observation(task,revealed,ablation),"menu_path":list(prefix)},sort_keys=True)
    if evidence:text+="\nCurrent-method evidence, not historical market input:\n"+json.dumps(evidence)
    return text
def options_for(groups):
    return [(label,"Configs: "+", ".join(ids)) for label,ids in groups]
def finish(task,revealed):
    if len(revealed)!=6 or len(set(revealed))!=6:raise ValueError("Unequal information budget")
    selected=min(revealed,key=lambda c:task["validation"][c]["loss"]);f=task["future_evaluator_only"][selected]
    return {"task_id":task["task_id"],"origin":task["origin"],"group":task["group"],"selected_config_id":selected,"revealed":revealed,"pinball":f["loss"],"n_cells":f["cells"],"trial_budget":6,"cases":f["cases"],"hindsight_regret":f["loss"]-min(v["loss"] for v in task["future_evaluator_only"].values())}
def summary(label,rows):
    n=sum(r["n_cells"] for r in rows)
    cases=[c for r in rows for c in r["cases"]]
    def metrics(cs):
        loss=statistics.mean(c["loss"] for c in cs);base=statistics.mean(c["baseline_loss"] for c in cs)
        return {"pinball":loss,"skill":1-loss/base if base>1e-12 else None,"baseline_pinball":base,"coverage":statistics.mean(c["covered"] for c in cs),"mean_width":statistics.mean(c["width"] for c in cs),"n_cells":len(cs)}
    return {"policy":label,**metrics(cases),"tasks":len(rows),"temporal_origins":len({r["origin"] for r in rows}),"hindsight_regret":sum(r["hindsight_regret"]*r["n_cells"] for r in rows)/n,
        "by_horizon":{str(h):metrics([c for c in cases if c["horizon_days"]==h]) for h in (1,3,7)},
        "by_series":{sid:metrics([c for c in cases if c["series_id"]==sid]) for sid in sorted({c["series_id"] for c in cases})},"traces":rows}
def demonstration_examples(tasks,objective,seed):
    examples=[];rng=random.Random(seed);candidates=[c["id"] for c in REGISTRY if c["id"] not in INITIAL]
    for task in tasks:
        if task["phase"]!="training":raise ValueError("Only training tasks may teach")
        for repeat in range(8):
            order=list(candidates);rng.shuffle(order)
            for step in range(4):
                revealed=INITIAL+order[:step]
                remaining=[c for c in candidates if c not in revealed];prefix=()
                while True:
                    prefix,groups=menu(remaining,prefix)
                    if len(groups)==1 and len(groups[0][1])==1:break
                    costs=[min(task["validation"][c]["loss"] for c in ids) for _,ids in groups]
                    best=min(range(len(costs)),key=lambda i:(costs[i],groups[i][0]))
                    if objective=="hard":probs=[float(i==best) for i in range(len(costs))]
                    else:
                        scores=[-(v-min(costs))/(task["scale"]*.15) for v in costs];e=[math.exp(max(-60,v)) for v in scores];probs=[v/sum(e) for v in e]
                    examples.append({"task_id":task["task_id"],"origin":task["origin"],"phase":"training","teacher_last_label":max(task["validation"][c]["last_label_date"] for c in candidates),"prompt":prompt(task,revealed,prefix),"options":options_for(groups),"targets":dict(zip([g[0] for g in groups],probs))})
                    prefix=(*prefix,groups[best][0])
                    if len(groups[best][1])==1:break
    return examples
async def choose(task,revealed,sampler,renderer,rng=None,ablation=None,evidence=None):
    from tinker_cookbook.recipes.decisions import Decision,sample_decision
    remaining=[c["id"] for c in REGISTRY if c["id"] not in revealed];prefix=();decisions=[]
    while True:
        prefix,groups=menu(remaining,prefix)
        if len(groups)==1 and len(groups[0][1])==1:return groups[0][1][0],decisions
        decision=Decision(prompt(task,revealed,prefix,ablation,evidence),options_for(groups));rendered=renderer.render(decision)
        started=time.perf_counter();distribution=await sample_decision(sampler,rendered)
        labels=list(distribution)
        if abs(sum(distribution.values())-1)>1e-6 or set(labels)!={g[0] for g in groups} or not all(math.isfinite(v) and v>=0 for v in distribution.values()):raise ValueError("Invalid action probabilities")
        selected=rng.choices(labels,weights=[distribution[x] for x in labels],k=1)[0] if rng else max(labels,key=lambda x:distribution[x])
        q=distribution[selected]
        decisions.append({"decision":decision,"distribution":distribution,"selected":selected,"log_probability":math.log(max(q,1e-30)),"runtime_seconds":time.perf_counter()-started,"stage":list(prefix)})
        ids=dict(groups)[selected]
        if len(ids)==1:return ids[0],decisions
        prefix=(*prefix,selected)
async def episode(task,sampler,renderer,rng=None,ablation=None,evidence=None):
    revealed=list(INITIAL);steps=[];raw=[]
    for step in range(4):
        selected,decisions=await choose(task,revealed,sampler,renderer,rng,ablation,evidence);raw.extend(decisions)
        steps.append({"step":step,"selected_config_id":selected,"observation":observation(task,revealed,ablation),"decisions":[{k:v for k,v in d.items() if k!="decision"} for d in decisions],"revealed_validation_result":task["validation"][selected]})
        revealed.append(selected)
    result=finish(task,revealed);result["steps"]=steps;return result,raw
async def evaluate(tasks,sampler,renderer,label,ablation=None,evidence=None):
    semaphore=asyncio.Semaphore(3)
    async def one(t):
        async with semaphore:return (await episode(t,sampler,renderer,ablation=ablation,evidence=evidence))[0]
    return summary(label,await asyncio.gather(*(one(t) for t in tasks)))
def controls(tasks,training):
    candidates=[c["id"] for c in REGISTRY if c["id"] not in INITIAL]
    ranks={c:statistics.mean(t["validation"][c]["loss"]/t["scale"] for t in training) for c in candidates}
    fixed=sorted(candidates,key=lambda c:(ranks[c],c))[:4]
    rows=[summary("training_selected_static",[finish(t,INITIAL+fixed) for t in tasks])]
    random_losses=[]
    for seed in range(100):
        traces=[finish(t,INITIAL+random.Random(seed+int(t["task_id"][:8],16)).sample(candidates,4)) for t in tasks]
        score=summary("random_"+str(seed),traces);random_losses.append(score["pinball"])
        if seed<5:rows.append(score)
    rows.append({"policy":"random_100_seed_distribution","pinball":statistics.mean(random_losses),"min":min(random_losses),"max":max(random_losses),"seeds":100})
    # Fixed-kernel Gaussian-process expected-improvement search, same two initial trials.
    import numpy as np
    from scipy.special import ndtr
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern
    families=sorted({c["family"] for c in REGISTRY})
    def vector(identifier):
        c=BY_ID[identifier]
        return [float(c["family"]==f) for f in families]+[c.get("days",0)/56,math.log1p(c.get("alpha",0))/5,float(c.get("space")=="log"),c.get("leaves",0)/7,c.get("weight",0),c.get("smoothing",0)]
    traces=[]
    for t in tasks:
        revealed=list(INITIAL)
        for _ in range(4):
            remaining=[c for c in candidates if c not in revealed]
            gp=GaussianProcessRegressor(kernel=Matern(length_scale=1.0,nu=2.5),alpha=1e-5,optimizer=None,normalize_y=True)
            y=np.array([t["validation"][c]["loss"]/t["scale"] for c in revealed]);gp.fit([vector(c) for c in revealed],y)
            mu,std=gp.predict([vector(c) for c in remaining],return_std=True);std=np.maximum(std,1e-12);z=(y.min()-mu)/std
            ei=(y.min()-mu)*ndtr(z)+std*np.exp(-z*z/2)/math.sqrt(2*math.pi)
            revealed.append(remaining[int(np.argmax(ei))])
        traces.append(finish(t,revealed))
    rows.append(summary("gp_expected_improvement",traces));return rows,fixed
def public_score(report):return {k:v for k,v in report.items() if k!="traces"}

def reachable_training_rewards(task):
    if task["phase"]!="training":raise ValueError("Reward gates may inspect training only")
    candidates=[c for c in BY_ID if c not in INITIAL]
    first=min(INITIAL,key=lambda c:task["validation"][c]["loss"]);threshold=task["validation"][first]["loss"]
    possible=[first] if sum(task["validation"][c]["loss"]>=threshold for c in candidates)>=4 else []
    for c in candidates:
        v=task["validation"][c]["loss"]
        if v<threshold and sum(task["validation"][other]["loss"]>=v for other in candidates if other!=c)>=3:possible.append(c)
    if not possible:raise ValueError("No reachable six-trial terminal winner")
    rewards=[max(-5,min(5,-task["future_evaluator_only"][c]["loss"]/task["scale"])) for c in possible]
    return {"task_id":task["task_id"],"possible_terminal_reward_range":max(rewards)-min(rewards),"possible_winners":len(possible),"reward_is_clipped":True}

async def run(grid_path,output,objective,seed,mode="sft",parent=None,max_updates=None,evidence_path=None):
    import tinker,torch
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import Decision,DecisionRenderer,decision_dist_datums,probability_loss
    grid=json.loads(Path(grid_path).read_text());tasks,excluded=make_tasks(grid)
    packet=None
    if evidence_path:
        ev=json.loads(Path(evidence_path).read_text())
        packet=[{k:s.get(k) for k in ("source_id","title","url","topic","content_sha256")} for s in ev.get("sources",[])[:8]]
    train=[t for t in tasks if t["phase"]=="training"];dev=[t for t in tasks if t["phase"]=="development"];test=[t for t in tasks if t["phase"]=="evaluation"]
    if len(train)<4 or len(dev)<2 or len(test)<2:raise ValueError("Too few eligible v2 tasks")
    out=Path(output);out.mkdir(parents=True,exist_ok=True);run_id=uuid.uuid4().hex;started=time.perf_counter()
    service=tinker.ServiceClient(display_name=f"Compute Forecast v2 {mode} {objective} seed{seed}")
    private={"run_id":run_id,"mode":mode,"seed":seed,"objective":objective,"checkpoints":[],"created_at":now()}
    trainer=await service.create_lora_training_client(base_model=MODEL,rank=16,seed=seed)
    tokenizer=trainer.get_tokenizer();renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(MODEL),tokenizer))
    if parent:
        private_parent=load_private.remote(parent);chosen=private_parent["selected"]
        await trainer.load_state(chosen["state_path"])
    base=await service.create_sampling_client(base_model=MODEL)
    starting=await evaluate(dev,base,renderer,"starting_policy_development");write(out/"starting-development.json",starting)
    checkpoints=[];updates=[];rng=random.Random(seed)
    async def checkpoint(step):
        state=await trainer.save_state("v2_"+mode+"_"+str(step));weights=await trainer.save_weights_for_sampler("v2_"+mode+"_"+str(step))
        sampler=await service.create_sampling_client(model_path=weights.path)
        scored=await evaluate(dev,sampler,renderer,mode+"_"+objective+"_step"+str(step))
        row={"update":len(updates),"rollout_iteration":step,"checkpoint_id":hashlib.sha256(weights.path.encode()).hexdigest()[:20],"development_pinball":scored["pinball"]}
        checkpoints.append(row);private["checkpoints"].append({**row,"state_path":state.path,"sampler_path":weights.path})
        private["rng_state"]=rng.getstate();private["completed_optimizer_updates"]=len(updates)
        retain_private.remote(run_id,private);write(out/"checkpoints.json",checkpoints);write(out/("development-"+str(step)+".json"),scored)
        print("V2_CHECKPOINT:"+json.dumps({**row,"seed":seed,"objective":objective,"mode":mode}),flush=True)
    await checkpoint(0)
    ceiling=protocol()["sft_max_updates"] if mode=="sft" else protocol()["rl_max_updates"]
    limit=max_updates or ceiling
    if not 1<=limit<=ceiling:raise ValueError("Update limit exceeds registered ceiling")
    rl_trajectories=[];gate=None;constant_streak=0;skipped_constant_groups=0;recovery_checkpoints=[]
    private["rollout_snapshots"]=[];private["recovery_states"]=[]
    variation=[reachable_training_rewards(t) for t in train]
    write(out/"reward-audit.json",variation)
    if mode=="rl" and max(v["possible_terminal_reward_range"] for v in variation)<1e-8:
        gate="All reachable training terminal rewards are constant; RL skipped"
        limit=0
    if mode=="sft":
        examples=demonstration_examples(train,objective,seed);write(out/"training-examples.json",examples)
        datums=decision_dist_datums(renderer,[(Decision(e["prompt"],e["options"]),e["targets"]) for e in examples])
        def ce(probs,target):return -(target*torch.log(probs.clamp_min(1e-9))).sum()
        for step in range(1,limit+1):
            indices=[rng.randrange(len(datums)) for _ in range(32)]
            forward=trainer.forward_backward_custom([datums[i] for i in indices],probability_loss(ce))
            optim=trainer.optim_step(tinker.AdamParams(learning_rate=protocol()["learning_rate"]))
            result=await forward;await optim;updates.append({"update":step,"metrics":result.metrics,"datums":len(indices)})
            write(out/"updates.json",updates)
            if step in (20,50,limit):await checkpoint(step)
    else:
        # True sampled-action PPO-style policy gradient on the bounded categorical distribution.
        # Rewards are tool-computed subsequent forecast losses inside TRAINING only.
        for step in range(1,limit+1):
            weights=await trainer.save_weights_for_sampler("v2_rl_rollout_"+str(step),ttl_seconds=3600)
            rollout_checkpoint_id=hashlib.sha256(weights.path.encode()).hexdigest()[:20]
            private["rollout_snapshots"].append({"iteration":step,"checkpoint_id":rollout_checkpoint_id,"sampler_path":weights.path,"ttl_seconds":3600})
            sampler=await service.create_sampling_client(model_path=weights.path)
            task=train[rng.randrange(len(train))]
            batch_tasks=[task]*4  # Same task, four genuinely sampled trajectories.
            rollouts=await asyncio.gather(*(episode(t,sampler,renderer,random.Random(seed*100000+step*10+i)) for i,t in enumerate(batch_tasks)))
            rewards=[max(-5,min(5,-r[0]["pinball"]/t["scale"])) for r,t in zip(rollouts,batch_tasks)]
            for (r,raw),reward,t in zip(rollouts,rewards,batch_tasks):
                rl_trajectories.append({"step":step,"task_id":t["task_id"],"phase":"training","feedback_cache_hit":True,"new_numerical_execution":False,"rollout_checkpoint_id":rollout_checkpoint_id,"reward":reward,"reward_label_end":t["reward_label_end"],"trace":r,"sampled_actions":[{k:v for k,v in d.items() if k!="decision"} for d in raw]})
            write(out/"rl-trajectories.json",rl_trajectories)
            if max(rewards)-min(rewards)<1e-10:
                constant_streak+=1;skipped_constant_groups+=1
                if constant_streak>=5:
                    gate="Five consecutive sampled within-task groups had constant clipped reward; stopped after "+str(len(updates))+" RL optimizer updates";break
                continue
            constant_streak=0
            center=statistics.mean(rewards);training_pairs=[];old_probs=[];advantages=[]
            for (r,raw),reward in zip(rollouts,rewards):
                for d in raw:
                    training_pairs.append((d["decision"],{d["selected"]:1.0}));old_probs.append(math.exp(d["log_probability"]));advantages.append(reward-center)
            if not training_pairs:gate="No model-controlled actions";break
            data=decision_dist_datums(renderer,training_pairs)
            def policy_gradient(batch,logprobs):
                losses=[];ratios=[]
                for datum,lp,old,adv in zip(batch,logprobs,old_probs,advantages):
                    probs=torch.softmax(lp[-1].float(),dim=-1);chosen=datum.loss_fn_inputs["weights"].to_torch()[-1].float()
                    ratio=(probs*chosen).sum()/max(old,1e-9)
                    losses.append(-torch.minimum(ratio*adv,ratio.clamp(.8,1.2)*adv));ratios.append(ratio.detach())
                loss=torch.stack(losses).mean()
                return loss,{"loss":float(loss.detach()),"reward_mean":center,"reward_range":max(rewards)-min(rewards),"ratio_mean":float(torch.stack(ratios).mean())}
            forward=trainer.forward_backward_custom(data,policy_gradient);optim=trainer.optim_step(tinker.AdamParams(learning_rate=1e-5))
            result=await forward;await optim;updates.append({"update":len(updates)+1,"rollout_iteration":step,"metrics":result.metrics,"sampled_episodes":4})
            write(out/"updates.json",updates)
            if len(updates)%10==0:
                recovery=await trainer.save_state("v2_rl_recovery_"+str(len(updates)))
                record={"update":len(updates),"rollout_iteration":step,"checkpoint_id":hashlib.sha256(recovery.path.encode()).hexdigest()[:20],"kind":"optimizer_state","development_evaluated":False}
                recovery_checkpoints.append(record);private["recovery_states"].append({**record,"state_path":recovery.path})
                private["rng_state"]=rng.getstate();private["completed_optimizer_updates"]=len(updates);retain_private.remote(run_id,private)
            if step in (20,50,limit):await checkpoint(step)
    if mode=="rl" and updates and checkpoints[-1]["update"]!=len(updates):await checkpoint(rl_trajectories[-1]["step"])
    best=min(private["checkpoints"],key=lambda x:(x["development_pinball"],x["update"]));private["selected"]=best
    retain_private.remote(run_id,private)
    # Selection is persisted before opening any v2 evaluation score.
    freeze={"selected_checkpoint_id":best["checkpoint_id"],"selected_update":best["update"],"selected_on":"development","frozen_at":now(),"run_id":run_id,"test_opened":False}
    write(out/"selection-freeze.json",freeze)
    sampler=await service.create_sampling_client(model_path=best["sampler_path"])
    trained=await evaluate(test,sampler,renderer,"selected_"+mode+"_"+objective);initial=await evaluate(test,base,renderer,"starting_policy")
    noobs=await evaluate(test,sampler,renderer,"selected_no_observation",ablation="no_observation")
    critic=await evaluate(test,sampler,renderer,"selected_with_criticism",ablation="with_criticism")
    evidence_report=await evaluate(test,sampler,renderer,"selected_with_method_evidence",evidence=packet) if packet else None
    refs,fixed=controls(test,train)
    for label,report in (("trained-evaluation",trained),("starting-evaluation",initial),("no-observation",noobs),("with-criticism",critic)):write(out/(label+".json"),report)
    write(out/"controls.json",refs)
    if evidence_report:write(out/"with-evidence.json",evidence_report)
    result={"schema_version":2,"run_id":run_id,"mode":mode,"objective":objective,"seed":seed,"model":MODEL,
      "dataset_sha256":PACK_SHA256,"grid_source_sha":grid["code_sha"],"code_sha":os.environ.get("GITHUB_SHA"),"created_at":now(),
      "actual_optimizer_updates":len(updates),"checkpoints":checkpoints,"selected_update":best["update"],"private_manifest_id":run_id,
      "training_tasks":len(train),"training_temporal_origins":len({t["origin"] for t in train}),"development_tasks":len(dev),"evaluation_tasks":len(test),
      "evaluation_status":protocol()["evaluation_status"],"future_competition_truth_loaded":False,"v1_final_used":False,
      "comparisons":[public_score(x) for x in [initial,trained,noobs,critic,*([evidence_report] if evidence_report else []),*refs]],"static_portfolio":fixed,
      "rl_gate":gate,"rl_gate_revision":2 if mode=="rl" else None,"skipped_constant_groups":skipped_constant_groups,"sampled_training_episodes":len(rl_trajectories),"recovery_checkpoints":recovery_checkpoints,"numerical_feedback_cache_hit":True,"new_rollout_numerical_executions":0,"reward_audit":variation,"evidence_packet":packet,"critic_behavior":"fixed deterministic, sees revealed validation only","runtime_seconds":time.perf_counter()-started,"cost_status":"unavailable","cost":None,
      "limitations":["Retrospective evaluation reuses previously published v1 development dates","Series and horizons share observations; tasks are dependent","Pretrained knowledge and true historical vintage cannot be excluded"]}
    write(out/"policy-report.json",result);print("V2_POLICY_REPORT:"+json.dumps(result),flush=True)
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write("# V2 policy "+mode+" "+objective+" seed"+str(seed)+"\n\n~~~json\n"+json.dumps(result,indent=2)+"\n~~~\n")
    return result
@app.local_entrypoint()
def main(grid:str="inputs/grid/grid.json",output:str="artifacts/v2-policy",objective:str="hard",seed:int=17,mode:str="sft",parent:str="",max_updates:int=0,evidence:str=""):
    if objective not in ("hard","soft") or seed not in protocol()["training_seeds"] or mode not in ("sft","rl"):raise ValueError("Unregistered policy campaign")
    asyncio.run(run(grid,output,objective,seed,mode,parent or None,max_updates or None,evidence or None))
