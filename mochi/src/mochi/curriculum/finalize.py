"""Finish evaluation of the saved 64-update campaign; no optimizer calls."""
import asyncio,json,os,time,shutil
import numpy as np,modal
from .train import ROOT,OUT,PROTOCOL,save,log,task_summary,sequence_summary,complete,drive,publish
from .world import TASKS,PROFILES
from .remote import app,contact_trial,replay
from .decisions import choose
from .checkpoints import StateSampler
from .resume import merged_services
from ..desk.services import DeskServices
from ..integrations import now

async def main():
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import DecisionRenderer
    source=ROOT/'.cache/resume-source';old_path=next(source.rglob('incomplete.json'));folder=old_path.parent;report=json.loads(old_path.read_text());prior_services=report['services'];paths=json.loads((folder/'checkpoint-paths.json').read_text());start=time.perf_counter();services=DeskServices()
    assert len(report['training_log'])==64 and report['checkpoints'][-1]['update']==64
    for p in folder.iterdir():
        if p.is_file():
            OUT.mkdir(exist_ok=True,parents=True);shutil.copy2(p,OUT/('before-evaluation-'+p.name if p.name in ['incomplete.json','readiness.json'] else p.name))
    report.update(status='running',phase='Fresh-scenario evaluation',evaluation_source_sha=os.getenv('GITHUB_SHA'),evaluation_recovery_at=now(),evaluation_extra_optimizer_updates=0,evaluation_source_run=44244443083,duration_scope='Evaluation-only recovery; training creation and resume times retained.');report.pop('error',None);report.pop('error_type',None)
    cfg=PROTOCOL['training'];test_seeds=PROTOCOL['held_out_seeds'];dev_seeds=PROTOCOL['development_seeds'];fixed=report['fixed_baseline']
    best=max((( (cp['continuous_development']['full_successes'],sum(cp['continuous_development']['task_successes'].values()),cp['continuous_development']['stations_reached'],-cp['continuous_development']['falls'],-cp['continuous_development']['mean_duration_s']),cp) for cp in report['checkpoints']),key=lambda x:x[0])
    try:
        await services.setup();renderer=services.renderer
        async with app.run():
            await publish(report)
            canary=await services.write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},private=True);await services.read('designer',canary,False)
            inference=StateSampler(services.service)
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
