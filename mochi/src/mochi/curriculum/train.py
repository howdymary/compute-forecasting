"""Actual multi-domain Tinker post-training and continuous closed-loop evaluation."""
import asyncio, hashlib, json, os, time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import numpy as np
import modal
from .world import World, TASKS, PROFILES, ROOT, ROUTE
from .remote import app,contact_trial,expert_sequence,replay,Runner,walking_coverage
from .decisions import decision,choose
from ..desk.services import DeskServices
from ..integrations import now,digest

OUT=ROOT/'artifacts/curriculum'
PROTOCOL=json.loads((ROOT/'configs/curriculum-protocol.json').read_text())
def save(name,value):
    OUT.mkdir(exist_ok=True,parents=True);p=OUT/(name+'.json');t=p.with_suffix('.tmp');t.write_text(json.dumps(value,indent=2,default=lambda x:x.item() if hasattr(x,'item') else str(x)));t.replace(p)
def log(event,**data):print('MOCHI_CURRICULUM '+json.dumps({'event':event,'at':now(),**data}),flush=True)
def rank(row):
    r=row['result'];t=r['task'];error=abs(r['value'])/(.005 if t=='alarm' else .03 if t=='drawer' else 1.)
    return (not r['success'],r['fall'],r['non_hand_contact_steps']>0,error if not r['success'] else r['duration'],r['max_force_n'])
def task_summary(rows):
    return {t:{'n':len(a:=[r for r in rows if r['result']['task']==t]),'successes':sum(r['result']['success'] for r in a),'wilson_95_success_rate':wilson(sum(r['result']['success'] for r in a),len(a)),'mean_duration_s':float(np.mean([r['result']['duration'] for r in a])) if a else None} for t in TASKS}
def wilson(successes,n):
    if not n:return None
    z=1.95996398454;p=successes/n;den=1+z*z/n;center=(p+z*z/(2*n))/den;half=z*((p*(1-p)/n+z*z/(4*n*n))**.5)/den
    return [max(0.,center-half),min(1.,center+half)]
def complete(row):
    ep=row['episode'];states=ep.get('final_object_states',{});speeds=ep.get('final_object_speeds',{})
    return bool(all(ep['results'].get(t,{}).get('success',False) for t in TASKS) and not ep['fall'] and states.get('drawer',1)<.002 and states.get('laptop',9)<np.deg2rad(5) and abs(states.get('globe',9))<np.deg2rad(3) and all(abs(speeds.get(t,9))<v for t,v in [('drawer',.01),('laptop',.15),('globe',.07)]))
def sequence_summary(rows):
    successes=sum(complete(x) for x in rows);arrivals=[a for x in rows for a in x['arrivals']]
    return {'n':len(rows),'full_successes':successes,'wilson_95_full_success_rate':wilson(successes,len(rows)),'task_successes':{t:sum(x['episode']['results'].get(t,{}).get('success',False) for x in rows) for t in TASKS},'stations_reached':len(arrivals),'station_opportunities':len(rows)*len(ROUTE),'falls':sum(x['episode']['fall'] for x in rows),'mean_duration_s':float(np.mean([x['episode']['duration'] for x in rows])),'arrival_measurement_n':len(arrivals),'mean_arrival_position_error_mm':float(np.mean([a['position_error_mm'] for a in arrivals])) if arrivals else None,'mean_arrival_heading_error_degrees':float(np.mean([a['heading_error_degrees'] for a in arrivals])) if arrivals else None,'mean_foot_slip_estimate_m':float(np.mean([sum(x['episode']['foot_slip_estimate_m'].values()) for x in rows]))}

async def drive(sampler,renderer,seed,record=False,expert=False,fixed=None):
    """LLM decisions observe changing physical state; every integration step is local.

    The exact action transcript is independently replayed on Modal below. This
    avoids assuming stateful container affinity across separate Modal calls.
    """
    runner=Runner();status=runner.reset(seed,record);actions=[];decisions=[]
    for step in range(500):
        if status['mode']=='done':break
        obs=status['observation']
        if expert:
            action=World.teacher_move(obs) if obs['domain']=='walk' else (fixed or {}).get(obs['domain'],'B');dist=None
        else:action,dist=await choose(sampler,renderer,obs)
        actions.append(action);decisions.append({'observation':obs,'action':action,'distribution':dist})
        status=runner.advance(action)
    if status['mode']!='done':status={'mode':'budget_exhausted','episode':runner.w.episode(),'arrivals':runner.arrivals}
    return {**status,'seed':seed,'actions':actions,'model_decisions':decisions}

async def publish(report):
    public={k:v for k,v in report.items() if k not in ['implementation_sha256']}
    await modal.Dict.from_name('mochi-curriculum-v6-progress',create_if_missing=True).put.aio('latest',public)

async def main():
    import tinker
    from tinker_cookbook import renderers,model_info
    from tinker_cookbook.recipes.decisions import DecisionRenderer,decision_choice_datums
    start=time.perf_counter();services=DeskServices();report={'study':'mochi-curriculum-v6','status':'running','source_sha':os.getenv('GITHUB_SHA'),'created_at':now(),'protocol':PROTOCOL,'protocol_sha256':digest(PROTOCOL),'scope':'Tinker LoRA learns repeated observed-state walking commands and contact-profile selection for four tasks. Native Unitree gait, classical standing balance and IK remain fixed. No raw-torque learning or hardware validation.','training_log':[],'checkpoints':[],'rollouts':0,'sources':[]}
    report['implementation_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    try:
        await services.setup();log('services_ready')
        async with app.run():
            await publish(report)
            # Research affects candidate interpretation/training examples, never the verifier.
            prior=await services.write('experimenter',{'kind':'observation','study':report['study'],'failures':['walking-to-standing drift','contact force overshoot','laptop hinge creep'],'constraint':'Frozen simulator and verified task criteria; no held-out evidence.'})
            observed=await services.read('researcher',prior)
            evidence=await services.search('humanoid locomotion manipulation velocity command contact force feedback position control pushing friction robustness')
            idea=await services.write('researcher',{'kind':'hypothesis','observed':observed,'sources':evidence,'mechanism':'Separate commanded locomotion from fast gait stabilization; use force-aware bounded contact profiles.','prediction':'State-conditioned decisions can improve reaching and contact completion; needs evaluation.'})
            found=await services.read('designer',idea)
            focus=await services.decide('designer','Choose a training emphasis informed by these sources and failures.',found,['precision_arrival','contact_force_backoff'],[idea])
            proposal=await services.write('designer',{'kind':'proposal','focus':focus,'hypothesis_record':idea,'bounded_change':'Train the shared walking and contact decision model; keep all physical profiles and verifiers identical across checkpoints.'})
            await services.read('experimenter',proposal);report['research_focus']=focus;allocation={'walk':16,**{t:4 for t in TASKS}} if focus=='precision_arrival' else {'walk':8,**{t:6 for t in TASKS}};report['research_allocation']=[{'update':0,'focus':focus,'domain_batch_counts':allocation.copy(),'proposal_record':proposal}]
            train_seeds=PROTOCOL['train_seeds'];dev_seeds=PROTOCOL['development_seeds'];test_seeds=PROTOCOL['held_out_seeds']
            jobs=[(seed,t,p.code,False) for seed in train_seeds+dev_seeds for t in TASKS for p in PROFILES]
            report['phase']='Modal contact experiments';await publish(report);log('contact_labels_start',rollouts=len(jobs))
            phase=json.loads((ROOT/'configs/curriculum-phase.json').read_text());bootstrap=list((ROOT/'.cache/bootstrap').rglob('contact-outcomes.json')) if phase.get('reuse_contact_run') else []
            if phase.get('reuse_contact_run'):
                if len(bootstrap)!=1:raise RuntimeError('Expected exactly one verified prior contact dataset')
                rows=json.loads(bootstrap[0].read_text());expected={(seed,t,code) for seed,t,code,_ in jobs};actual={(r['seed'],r['result']['task'],r['result']['profile']['code']) for r in rows}
                if len(rows)!=len(jobs) or actual!=expected:raise RuntimeError('Prior contact dataset does not match frozen trials')
                report['contact_dataset_provenance']={'source_github_run':phase['reuse_contact_run'],'sha256':hashlib.sha256(bootstrap[0].read_bytes()).hexdigest(),'prior_completed_rollouts':len(rows),'reused_rows':sum(r['result']['task']!='laptop' for r in rows),'superseded_domain':'laptop','reason':'Before any optimizer updates, added measured walking observations and a collision-free laptop approach. Reuse unchanged alarm/drawer/globe trials; regenerate all laptop trials.'}
                replacement_jobs=[j for j in jobs if j[1]=='laptop'];replacement=[r async for r in contact_trial.starmap.aio(replacement_jobs,order_outputs=True)];report['rollouts']+=len(replacement);rows=[r for r in rows if r['result']['task']!='laptop']+replacement
                report['contact_dataset_provenance']['regenerated_laptop_rows']=len(replacement);report['rollouts']+=6;report['contact_dataset_provenance']['superseded_walking_rollouts']=6
            else:rows=[r async for r in contact_trial.starmap.aio(jobs,order_outputs=True)]
            report['rollouts']+=len(rows);assert report['rollouts']<PROTOCOL['validity']['maximum_rollouts'];save('contact-outcomes',rows)
            groups={}
            for r in rows:groups.setdefault((r['seed'],r['result']['task']),[]).append(r)
            domain_data={t:[] for t in TASKS};audit={}
            for t in TASKS:
                cells=[groups[(seed,t)] for seed in train_seeds];best=[min(c,key=rank) for c in cells]
                domain_data[t]=[(r['observation'],r['result']['profile']['code']) for r in best]
                audit[t]={'n':len(cells),'teacher_successes':sum(r['result']['success'] for r in best),'label_counts':dict(Counter(label for _,label in domain_data[t])),'informative_cases':sum(len({r['result']['success'] for r in c})>1 for c in cells)}
                if not audit[t]['teacher_successes']:raise RuntimeError('No valid physical training example for '+t)
            def fixed_key(task,profile):
                selected=[next(r for r in groups[(seed,task)] if r['result']['profile']['code']==profile.code) for seed in train_seeds]
                return (-sum(r['result']['success'] for r in selected),sum(r['result']['duration'] for r in selected),sum(r['result']['max_force_n'] for r in selected))
            fixed={t:min(PROFILES,key=lambda p:fixed_key(t,p)).code for t in TASKS}

            log('walking_labels_start');experts=[r async for r in expert_sequence.starmap.aio([(seed,False) for seed in train_seeds[:6]],order_outputs=True)];report['rollouts']+=len(experts);save('walking-teachers',experts)
            coverage_jobs=[(train_seeds[i],offset) for i,offset in enumerate([(.015,.050,0.),(.015,-.05,0.),(.045,.035,.35),(.045,-.035,-.35),(.025,.050,-.2),(.025,-.050,.2)])]
            coverage=[r async for r in walking_coverage.starmap.aio(coverage_jobs,order_outputs=True)];report['rollouts']+=len(coverage);save('walking-coverage',coverage)
            domain_data['walk']=[(x['observation'],x['action']) for ep in experts+coverage for x in ep['episode']['decisions'] if x['observation']['domain']=='walk']
            audit['walk']={'n':len(domain_data['walk']),'label_counts':dict(Counter(y for _,y in domain_data['walk']))}
            if len(audit['walk']['label_counts'])<5:raise RuntimeError('Insufficient walking action coverage')
            report['data_audit']=audit;report['fixed_baseline']=fixed;save('data-audit',audit);save('frozen',report);report['phase']='Tinker post-training';await publish(report)
            record=await services.write('experimenter',{'kind':'observation','data_audit':audit,'split':'training only','rollouts':report['rollouts']})
            checked=await services.read('critic',record)
            verdict=await services.write('critic',{'kind':'qualified-conclusion','evidence':checked,'qualification':'Informative training outcomes establish learnability only; checkpoint and fresh scenario evaluation still required.','supersedes':idea})
            await services.read('researcher',verdict)
            canary=await services.write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},private=True);await services.read('designer',canary,False)
            cfg=PROTOCOL['training'];trainer=await services.service.create_lora_training_client(base_model=cfg['base_model'],rank=cfg['rank'],seed=cfg['seed'])
            renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(cfg['base_model']),trainer.get_tokenizer()))
            datums={d:decision_choice_datums(renderer,[(decision(x),y) for x,y in examples]) for d,examples in domain_data.items()};rng=np.random.default_rng(cfg['seed']);paths={};best=None
            for update in range(cfg['updates']+1):
                if update in cfg['checkpoints']:
                    state=await trainer.save_state(f'mochi_walk_tasks_{update}');weights=await trainer.save_weights_for_sampler(f'mochi_walk_tasks_{update}');paths[str(update)]={'weights':weights.path,'optimizer':state.path,'rng_state':rng.bit_generator.state};save('checkpoint-paths',paths)
                    sampler=await services.service.create_sampling_client(model_path=weights.path)
                    dev=await asyncio.gather(*(drive(sampler,renderer,seed,True) for seed in dev_seeds))
                    # Preserve each real continuous checkpoint, including failures.
                    save('checkpoint-'+str(update),dev)
                    contact_choices=[]
                    for seed in dev_seeds:
                        for t in TASKS:
                            action,dist=await choose(sampler,renderer,groups[(seed,t)][0]['observation']);contact_choices.append(next(r for r in groups[(seed,t)] if r['result']['profile']['code']==action))
                    summary=sequence_summary(dev);cp={'update':update,'checkpoint_id':digest(weights.path)[:20],'optimizer_state_id':digest(state.path)[:20],'continuous_development':summary,'isolated_contact_development':task_summary(contact_choices),'created_at':now()};report['checkpoints'].append(cp)
                    key=(summary['full_successes'],sum(summary['task_successes'].values()),summary['stations_reached'],-summary['falls'],-summary['mean_duration_s'])
                    if best is None or key>best[0]:best=(key,cp)
                    save('progress',report);await publish(report);log('checkpoint',**cp)
                    if update in [8,32]:
                        rid=await services.write('experimenter',{'kind':'observation','update':update,'development':summary,'scope':'Development only; held-out seeds remain unused.'})
                        failure=await services.read('researcher',rid)
                        mechanism=await services.search('humanoid precise waypoint stopping lateral drift contact force feedback manipulation robustness '+('locomotion' if summary['stations_reached']<len(dev_seeds)*len(ROUTE) else 'pushing hinge friction'))
                        hid=await services.write('researcher',{'kind':'hypothesis','evidence':failure,'sources':mechanism,'prediction':'Reallocate the equal-size training batch toward the observed bottleneck; the next checkpoint tests it.'})
                        recalled=await services.read('designer',hid)
                        focus=await services.decide('designer','Choose whether to emphasize precision walking or force-aware task decisions in the next equal-size training batches.',recalled,['precision_arrival','contact_force_backoff'],[hid])
                        pid=await services.write('designer',{'kind':'proposal','focus':focus,'source_record':hid,'update':update})
                        used=await services.read('experimenter',pid);allocation={'walk':16,**{t:4 for t in TASKS}} if used['focus']=='precision_arrival' else {'walk':8,**{t:6 for t in TASKS}}
                        report['research_allocation'].append({'update':update,'focus':focus,'domain_batch_counts':allocation.copy(),'proposal_record':pid})

                if update==cfg['updates']:break
                pending=[];batches={}
                for domain,data in datums.items():
                    count=allocation[domain];indices=rng.integers(0,len(data),count);batches[domain]=indices.tolist();pending.append((domain,trainer.forward_backward([data[int(i)] for i in indices],loss_fn='cross_entropy')))
                optimizer=trainer.optim_step(tinker.AdamParams(learning_rate=cfg['learning_rate']));metrics={}
                for domain,future in pending:
                    result=await future;metrics[domain]=result.metrics
                await optimizer
                report['training_log'].append({'update':update+1,'domain_counts':{d:len(i) for d,i in batches.items()},'domain_loss_metrics':metrics,'batch_sha256':digest(batches),'forward_backward_completed':True,'optimizer_completed':True,'at':now()});save('progress',report)
                if (update+1)%4==0:
                    await publish(report);log('optimizer_update',update=update+1,domain_loss_metrics=metrics)
            selected=best[1]['update'];report['selected_checkpoint']=best[1];report['held_out_not_yet_run']=True;save('selection-freeze',report);log('held_out_unsealed',selected_update=selected)
            results={}
            for name,update in [('starting_model',0),('post_trained_model',selected)]:
                sampler=await services.service.create_sampling_client(model_path=paths[str(update)]['weights']);results[name]=await asyncio.gather(*(drive(sampler,renderer,seed,True) for seed in test_seeds));save('held-out-'+name,results[name])
            results['classical_fixed']=await asyncio.gather(*(drive(None,None,seed,True,expert=True,fixed=fixed) for seed in test_seeds))
            isolated_jobs=[(seed,t,p.code,False) for seed in test_seeds for t in TASKS for p in PROFILES]
            isolated=[r async for r in contact_trial.starmap.aio(isolated_jobs,order_outputs=True)];report['rollouts']+=len(isolated);save('held-out-isolated-outcomes',isolated);isolated_evaluation={}
            for name,update in [('starting_model',0),('post_trained_model',selected)]:
                sampler=await services.service.create_sampling_client(model_path=paths[str(update)]['weights']);picked=[]
                for seed in test_seeds:
                    for t in TASKS:
                        cell=[r for r in isolated if r['seed']==seed and r['result']['task']==t];action,dist=await choose(sampler,renderer,cell[0]['observation']);picked.append(next(r for r in cell if r['result']['profile']['code']==action))
                isolated_evaluation[name]=picked
            isolated_evaluation['fixed_profiles']=[r for r in isolated if r['result']['profile']['code']==fixed[r['result']['task']]]
            report['held_out_isolated_contact']={k:task_summary(v) for k,v in isolated_evaluation.items()};save('held-out-isolated-evaluation',isolated_evaluation)

            # Independently execute every selected action sequence on Modal.
            replay_jobs=[(x['seed'],x['actions'],False) for group in results.values() for x in group];verified=[r async for r in replay.starmap.aio(replay_jobs,order_outputs=True)];report['rollouts']+=len(verified);save('modal-replays',verified)
            all_local=[x for group in results.values() for x in group]
            report['remote_replay_checks']=[{'seed':a['seed'],'same_task_success':{t:a['episode']['results'].get(t,{}).get('success',False)==b['episode']['results'].get(t,{}).get('success',False) for t in TASKS},'duration_delta_s':abs(a['episode']['duration']-b['episode']['duration']),'receipt':b['receipt']} for a,b in zip(all_local,verified)]
            if any(x['duration_delta_s']>.01 or not all(x['same_task_success'].values()) for x in report['remote_replay_checks']):raise RuntimeError('Local/Modal replay disagreement')
            report['held_out']={name:sequence_summary(group) for name,group in results.items()};report['paired_outcomes']=[{'seed':a['seed'],'starting_full':complete(a),'trained_full':complete(b),'starting_tasks':sum(v['success'] for v in a['episode']['results'].values()),'trained_tasks':sum(v['success'] for v in b['episode']['results'].values()),'starting_arrivals':len(a['arrivals']),'trained_arrivals':len(b['arrivals'])} for a,b in zip(results['starting_model'],results['post_trained_model'])];delta=np.array([int(x['trained_full'])-int(x['starting_full']) for x in report['paired_outcomes']]);boot=delta[np.random.default_rng(8312).integers(0,len(delta),(10000,len(delta)))].mean(1);report['paired_full_success_gain']={'percentage_points':float(delta.mean()*100),'bootstrap_95_percentage_points':(np.quantile(boot,[.025,.975])*100).tolist(),'n':len(delta)};report['held_out_not_yet_run']=False;report['local_continuous_rollouts']=len(dev_seeds)*len(cfg['checkpoints'])+len(test_seeds)*3;save('held-out-classical',results['classical_fixed'])
            conclusion=await services.write('experimenter',{'kind':'observation','held_out':report['held_out'],'selected_update':selected,'optimizer_updates_completed':len(report['training_log']),'checkpoint_summaries':report['checkpoints']})
            checked=await services.read('critic',conclusion);verdict=await services.write('critic',{'kind':'conclusion','evidence':checked,'limits':'Small simulation pilot; shared fixed gait and IK; state observations; no raw-torque post-training, hardware validation or causal sponsor ablation. Nonmonotonic checkpoints retained.'});await services.read('researcher',verdict)
        report.update(status='completed',completed_at=now(),duration_seconds=time.perf_counter()-start,services=services.report(),optimizer_updates_completed=len(report['training_log']));save('report',report);await publish(report);log('completed',held_out=report['held_out'])
    except Exception as exc:
        report.update(status='incomplete',error_type=type(exc).__name__,error=str(exc)[:240],services=services.report());save('incomplete',report);await publish(report);raise
    finally:await services.http.aclose()

if __name__=='__main__':
    with modal.enable_output():asyncio.run(main())
