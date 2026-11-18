"""Recover the original 64-update study from its durable 32-update state."""
import asyncio,hashlib,json,os,time,shutil
from pathlib import Path
import numpy as np,modal
from collections import Counter
from .train import ROOT,OUT,PROTOCOL,save,log,rank,task_summary,sequence_summary,complete,drive,publish
from .world import TASKS,PROFILES,ROUTE
from .remote import app,contact_trial,replay
from .decisions import decision,choose
from .checkpoints import retire_reconstructible_mochi_samplers,StateSampler
from ..desk.services import DeskServices
from ..integrations import now,digest

def merged_services(old,new):
    result=dict(new)
    for key in ['records','reads','decisions','calls','sources']:result[key]=old.get(key,[])+new.get(key,[])
    result['prior_actor_sets']=[old.get('actors',{})]
    result['eligibility']={'writers':len({r['author'] for r in result['records']}),'readers':len({r['reader'] for r in result['reads'] if r['source_id_verified']}),'cross_agent_reads':sum(r['cross_agent_use'] for r in result['reads']),'isolation_passed':old.get('eligibility',{}).get('isolation_passed',False) and new.get('eligibility',{}).get('isolation_passed',False)}
    return result

async def main():
    import tinker
    from tinker_cookbook import renderers,model_info
    from tinker_cookbook.recipes.decisions import DecisionRenderer,decision_choice_datums
    source=ROOT/'.cache/resume-source';old_path=next(source.rglob('incomplete.json'));report=json.loads(old_path.read_text());folder=old_path.parent;prior_services=report['services'];paths=json.loads((folder/'checkpoint-paths.json').read_text());start=time.perf_counter();services=DeskServices()
    for p in folder.iterdir():
        if p.is_file():
            name='previous-'+p.name if p.name in ['incomplete.json','readiness.json','checkpoint-paths.json'] else p.name
            OUT.mkdir(exist_ok=True,parents=True);shutil.copy2(p,OUT/name)
    report.update(status='running',phase='Restoring optimizer state',resume_source_sha=os.getenv('GITHUB_SHA'),resumed_at=now());report.pop('error',None);report.pop('error_type',None)
    try:
        rest=tinker.RestClient();last=paths['16']['optimizer'];run=tinker.types.ParsedCheckpointTinkerPath.from_tinker_path(last).training_run_id
        recovery,checkpoints=await retire_reconstructible_mochi_samplers(rest,run,OUT/'sampler-cache-recovery.json');report['storage_recovery']=recovery;report['recovery_source_run']=44239627558;report['research_payload_revision']='At update 32, include existing isolated skill results and domain losses in the failure diagnosis; same two equal-size allocation choices.';report['duration_scope']='Resumed execution; prior campaign creation time and workflow retained.'
        state32=checkpoints['weights/mochi_walk_tasks_32'].tinker_path
        for saved in paths.values():saved['original_sampler_receipt']=saved['weights'];saved['weights']=None;saved['sampling_mode']='snapshot_from_optimizer'
        rows=json.loads((folder/'contact-outcomes.json').read_text());groups={}
        for r in rows:groups.setdefault((r['seed'],r['result']['task']),[]).append(r)
        train_seeds=PROTOCOL['train_seeds'];dev_seeds=PROTOCOL['development_seeds'];test_seeds=PROTOCOL['held_out_seeds'];fixed=report['fixed_baseline'];cfg=PROTOCOL['training'];domain_data={}
        for task in TASKS:
            domain_data[task]=[(r['observation'],r['result']['profile']['code']) for seed in train_seeds for r in [min(groups[(seed,task)],key=rank)]]
        teachers=json.loads((folder/'walking-teachers.json').read_text())+json.loads((folder/'walking-coverage.json').read_text());domain_data['walk']=[(x['observation'],x['action']) for ep in teachers for x in ep['episode']['decisions'] if x['observation']['domain']=='walk']
        rng=np.random.default_rng(cfg['seed']);rng.bit_generator.state=paths['16']['rng_state']
        for entry in report['training_log']:
            if 16<entry['update']<=32:
                batch={d:rng.integers(0,len(data),entry['domain_counts'][d]).tolist() for d,data in domain_data.items()}
                if digest(batch)!=entry['batch_sha256']:raise RuntimeError('RNG reconstruction mismatch; refusing to resume')
        report['storage_recovery']['rng_batches_verified']=16
        await services.setup();trainer=await services.service.create_training_client_from_state_with_optimizer(state32)
        renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(cfg['base_model']),trainer.get_tokenizer()));datums={d:decision_choice_datums(renderer,[(decision(o),y) for o,y in examples]) for d,examples in domain_data.items()}
        allocation=report['research_allocation'][-1]['domain_batch_counts'];best=None
        for cp in report['checkpoints']:
            s=cp['continuous_development'];key=(s['full_successes'],sum(s['task_successes'].values()),s['stations_reached'],-s['falls'],-s['mean_duration_s'])
            if best is None or key>best[0]:best=(key,cp)
        async with app.run():
            report['phase']='Resumed Tinker post-training';await publish(report)
            canary=await services.write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},private=True);await services.read('designer',canary,False)
            for update in range(32,cfg['updates']+1):
                if update in cfg['checkpoints']:
                    state_path=state32 if update==32 else (await trainer.save_state(f'mochi_walk_tasks_{update}')).path
                    paths[str(update)]={'weights':None,'optimizer':state_path,'rng_state':rng.bit_generator.state,'sampling_mode':'snapshot_from_optimizer'};save('checkpoint-paths',paths)
                    sampler=await trainer.save_weights_and_get_sampling_client(kind='snapshot');dev=await asyncio.gather(*(drive(sampler,renderer,seed,True) for seed in dev_seeds));save('checkpoint-'+str(update),dev)
                    picked=[]
                    for seed in dev_seeds:
                        for task in TASKS:
                            action,dist=await choose(sampler,renderer,groups[(seed,task)][0]['observation']);picked.append(next(r for r in groups[(seed,task)] if r['result']['profile']['code']==action))
                    summary=sequence_summary(dev);cp={'update':update,'checkpoint_id':digest(state_path)[:20],'checkpoint_id_kind':'canonical_optimizer_state','optimizer_state_id':digest(state_path)[:20],'sampling_mode':'fixed_ephemeral_snapshot','continuous_development':summary,'isolated_contact_development':task_summary(picked),'created_at':now()};report['checkpoints'].append(cp)
                    key=(summary['full_successes'],sum(summary['task_successes'].values()),summary['stations_reached'],-summary['falls'],-summary['mean_duration_s'])
                    if best is None or key>best[0]:best=(key,cp)
                    report['services']=merged_services(prior_services,services.report());save('progress',report);await publish(report);log('checkpoint',**cp)
                    if update==32:
                        rid=await services.write('experimenter',{'kind':'observation','update':32,'development':summary,'isolated_contact':cp['isolated_contact_development'],'last_training_losses':report['training_log'][-1]['domain_loss_metrics'],'scope':'Development only; held-out unchanged. No contact stage was reached if arrivals are zero.'})
                        evidence=await services.read('researcher',rid);query='robot waypoint navigation policy imitation learning target relative heading stopping compounding errors' if summary['stations_reached']==0 else 'humanoid contact force feedback pushing hinge friction robustness'
                        sources=await services.search(query);hid=await services.write('researcher',{'kind':'hypothesis','evidence':evidence,'sources':sources,'prediction':'Use existing development evidence to focus the next equal-size batches on the bottleneck.'});recalled=await services.read('designer',hid)
                        focus=await services.decide('designer','Choose the training emphasis supported by arrival counts, isolated skills and domain losses.',recalled,['precision_arrival','contact_force_backoff'],[hid]);pid=await services.write('designer',{'kind':'proposal','focus':focus,'source_record':hid,'update':32});used=await services.read('experimenter',pid);allocation={'walk':16,**{t:4 for t in TASKS}} if used['focus']=='precision_arrival' else {'walk':8,**{t:6 for t in TASKS}};report['research_allocation'].append({'update':32,'focus':focus,'domain_batch_counts':allocation.copy(),'proposal_record':pid})
                if update==cfg['updates']:break
                pending=[];batches={}
                for domain,data in datums.items():
                    indices=rng.integers(0,len(data),allocation[domain]);batches[domain]=indices.tolist();pending.append((domain,trainer.forward_backward([data[int(i)] for i in indices],loss_fn='cross_entropy')))
                op=trainer.optim_step(tinker.AdamParams(learning_rate=cfg['learning_rate']));metrics={}
                for domain,future in pending:metrics[domain]=(await future).metrics
                await op;report['training_log'].append({'update':update+1,'domain_counts':{d:len(v) for d,v in batches.items()},'domain_loss_metrics':metrics,'batch_sha256':digest(batches),'forward_backward_completed':True,'optimizer_completed':True,'resumed_from_update':32,'at':now()});save('progress',report)
                if (update+1)%4==0:await publish(report);log('optimizer_update',update=update+1,domain_loss_metrics=metrics)
            inference=StateSampler(services.service,trainer)
            selected=best[1]['update'];report['selected_checkpoint']=best[1];report['held_out_not_yet_run']=True;save('selection-freeze',report);log('held_out_unsealed',selected_update=selected)
            results={}
            for name,update in [('starting_model',0),('post_trained_model',selected)]:
                sampler=await inference.load(paths[str(update)]['optimizer']);results[name]=await asyncio.gather(*(drive(sampler,renderer,seed,True) for seed in test_seeds));save('held-out-'+name,results[name])
            results['classical_fixed']=await asyncio.gather(*(drive(None,None,seed,True,expert=True,fixed=fixed) for seed in test_seeds))
            isolated_jobs=[(seed,t,p.code,False) for seed in test_seeds for t in TASKS for p in PROFILES]
            isolated=[r async for r in contact_trial.starmap.aio(isolated_jobs,order_outputs=True)];report['rollouts']+=len(isolated);save('held-out-isolated-outcomes',isolated);isolated_evaluation={}
            for name,update in [('starting_model',0),('post_trained_model',selected)]:
                sampler=await inference.load(paths[str(update)]['optimizer']);picked=[]
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
        report.update(status='completed',completed_at=now(),duration_seconds=time.perf_counter()-start,services=merged_services(prior_services,services.report()),optimizer_updates_completed=len(report['training_log']));save('report',report);await publish(report);log('completed',held_out=report['held_out'])
    except Exception as exc:
        report.update(status='incomplete',error_type=type(exc).__name__,error=str(exc)[:240],services=merged_services(prior_services,services.report()));save('incomplete',report);await publish(report);raise
    finally:await services.http.aclose()

if __name__=='__main__':
    with modal.enable_output():asyncio.run(main())
