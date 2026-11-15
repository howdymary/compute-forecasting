"""Gated successor training; new identities, no changes to canonical clients."""
from __future__ import annotations
import asyncio,hashlib,json,math,os,random,statistics,time,uuid
from pathlib import Path
from datetime import datetime,timezone
from .review_v4 import readiness,digest,encoded
def split_and_gate(tasks):
    train=[t for t in tasks if t["phase"]=="training"];dev=[t for t in tasks if t["phase"]=="development"]
    if len({t["task_id"] for t in tasks})!=len(tasks):raise ValueError("Duplicate training task identities")
    if not train or not dev:raise ValueError("Missing temporal training/development split")
    if max(t["reward_label_end"] for t in train)>=min(t["origin"] for t in dev):raise ValueError("Training labels cross development")
    if any(t["validation"][c]["last_label_date"]>t["origin"] for t in tasks for c in t["validation"]):raise ValueError("Unmatured observations")
    return train,dev,readiness(tasks)
async def train(tasks,private_root,output,mode="sft",parent=None,resume=None):
    train_tasks,dev,gate=split_and_gate(tasks)
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    if gate["status"]!="ready":
        report={"schema_version":4,"status":gate["status"],"readiness":gate,"actual_optimizer_updates":0,"model_clients_created":0}
        (out/"learning-report.json").write_bytes(encoded(report));return report
    # Imports and service creation occur only after the data gate.
    import tinker,torch
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import Decision,DecisionRenderer,decision_dist_datums,probability_loss
    from .policy_v2 import MODEL,demonstration_examples,evaluate,episode
    if mode not in ("sft","rl"):raise ValueError("Unknown training mode")
    if mode=="rl" and not parent:raise ValueError("RL requires an explicitly frozen SFT parent")
    settings=json.loads(Path("configs/review-v4-experiments.json").read_bytes())["learning"]
    identifier=uuid.uuid4().hex;private=Path(private_root)/identifier;private.mkdir(parents=True)
    rng=random.Random(settings["seed"]);updates=[];trajectories=[];checkpoints=[];start=time.perf_counter();iteration=0
    service=tinker.ServiceClient(display_name="Compute Forecast v4 registered successor "+mode)
    if resume:
        saved=json.loads(Path(resume).read_bytes())
        if saved["tasks_sha256"]!=digest(tasks) or saved["mode"]!=mode:raise ValueError("Resume source mismatch")
        trainer=await service.create_training_client_from_state_with_optimizer_async(saved["state_path"])
        updates=saved["updates"];trajectories=saved["trajectories"];checkpoints=saved["checkpoints"];iteration=saved["iteration"]
        state=saved["rng_state"];rng.setstate((state[0],tuple(state[1]),state[2]))
        identifier=saved["run_id"];private=Path(resume).parent
    else:
        trainer=await service.create_lora_training_client_async(base_model=MODEL,rank=settings["rank"],seed=settings["seed"])
        if parent:
            p=json.loads(Path(parent).read_bytes())
            if p.get("selection_uses_evaluation") is not False:raise ValueError("Parent not frozen on development")
            await trainer.load_state(p["state_path"])
    renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(MODEL),trainer.get_tokenizer()))
    async def save(step):
        state=await trainer.save_state("v4_"+identifier+"_"+str(step));weights=await trainer.save_weights_for_sampler("v4_"+identifier+"_"+str(step))
        sampler=await service.create_sampling_client(model_path=weights.path);score=await evaluate(dev,sampler,renderer,"development")
        row={"update":len(updates),"iteration":step,"checkpoint_id":hashlib.sha256(weights.path.encode()).hexdigest()[:20],"development_pinball":score["pinball"],"state_path":state.path,"sampler_path":weights.path}
        checkpoints.append(row)
        record={"schema_version":4,"run_id":identifier,"tasks_sha256":digest(tasks),"mode":mode,"iteration":step,"updates":updates,"trajectories":trajectories,"checkpoints":checkpoints,"state_path":state.path,"rng_state":rng.getstate()}
        temporary=private/"resume.pending";temporary.write_bytes(encoded(record));temporary.replace(private/"resume.json")
        (out/("development-"+str(step)+".json")).write_bytes(encoded(score))
    if not resume:await save(0)
    examples=demonstration_examples(train_tasks,"soft",settings["seed"]) if mode=="sft" else []
    if mode=="sft":
        datums=decision_dist_datums(renderer,[(Decision(e["prompt"],e["options"]),e["targets"]) for e in examples])
    informative={x["task_id"] for x in gate["reward_audit"] if x["possible_terminal_reward_range"]>1e-8};rl_tasks=[t for t in train_tasks if t["task_id"] in informative];constant=0
    while len(updates)<settings["max_optimizer_updates"] and iteration<settings["max_sampling_iterations"]:
        if time.perf_counter()-start>settings["wall_seconds"]:break
        iteration+=1
        if mode=="sft":
            batch=[datums[rng.randrange(len(datums))] for _ in range(settings["batch_size"])]
            def loss(probs,target):return -(target*torch.log(probs.clamp_min(1e-9))).sum()
            forward=trainer.forward_backward_custom(batch,probability_loss(loss))
        else:
            weights=await trainer.save_weights_for_sampler("v4_rollout_"+identifier+"_"+str(iteration),ttl_seconds=3600)
            sampler=await service.create_sampling_client(model_path=weights.path);task=rng.choice(rl_tasks)
            rollouts=await asyncio.gather(*(episode(task,sampler,renderer,random.Random(settings["seed"]*10000+iteration*10+i)) for i in range(4)))
            await service.create_rest_client().delete_checkpoint_from_tinker_path(weights.path)
            rewards=[max(-5,min(5,-r[0]["pinball"]/task["scale"])) for r in rollouts]
            trajectories.extend({"iteration":iteration,"task_id":task["task_id"],"reward":reward,"phase":"training","reward_label_end":task["reward_label_end"],"trace":r[0]} for r,reward in zip(rollouts,rewards))
            if max(rewards)-min(rewards)<1e-10:
                constant+=1
                if constant>=settings["constant_reward_stop_groups"]:break
                continue
            constant=0;center=statistics.mean(rewards);pairs=[];old=[];advantages=[]
            for (_,decisions),reward in zip(rollouts,rewards):
                for d in decisions:pairs.append((d["decision"],{d["selected"]:1.}));old.append(math.exp(d["log_probability"]));advantages.append(reward-center)
            batch=decision_dist_datums(renderer,pairs)
            def pg(batch,logprobs):
                losses=[]
                for datum,lp,previous,adv in zip(batch,logprobs,old,advantages):
                    prob=torch.softmax(lp[-1].float(),dim=-1);chosen=datum.loss_fn_inputs["weights"].to_torch()[-1].float();ratio=(prob*chosen).sum()/max(previous,1e-9)
                    losses.append(-torch.minimum(ratio*adv,ratio.clamp(.8,1.2)*adv))
                v=torch.stack(losses).mean();return v,{"loss":float(v.detach()),"reward_range":max(rewards)-min(rewards)}
            forward=trainer.forward_backward_custom(batch,pg)
        optimizer=trainer.optim_step(tinker.AdamParams(learning_rate=settings["learning_rate"] if mode=="sft" else 1e-5))
        result=await forward;await optimizer;updates.append({"update":len(updates)+1,"iteration":iteration,"metrics":result.metrics})
        if len(updates) in settings["checkpoints"]:await save(iteration)
    if checkpoints[-1]["update"]!=len(updates):await save(iteration)
    selected=min(checkpoints,key=lambda c:(c["development_pinball"],c["update"]))
    selection={**selected,"run_id":identifier,"selection_uses_evaluation":False,"tasks_sha256":digest(tasks)}
    (private/"selected.json").write_bytes(encoded(selection))
    report={"schema_version":4,"run_id":identifier,"mode":mode,"status":"completed","actual_optimizer_updates":len(updates),"sampling_iterations":iteration,"readiness":gate,"checkpoints":[{k:v for k,v in c.items() if k not in ("state_path","sampler_path")} for c in checkpoints],"selected_update":selected["update"],"selection_uses_evaluation":False,"evaluation_status":"pending separately registered evaluation","runtime_seconds":time.perf_counter()-start,"provider_cost_usd":None}
    (out/"learning-report.json").write_bytes(encoded(report));return report
