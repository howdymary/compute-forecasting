"""Actual resumed LoRA gradients, bounded physics and frozen checkpoint tests."""
import asyncio,copy,hashlib,json,math,os,time
from collections import Counter,defaultdict

import modal
import numpy as np
from ..curriculum.world import ROOT,TASKS
from .services import TerrainServices
from ..integrations import now,digest
from ..maintenance.checkpoints_by_date import inventory
from .learning_remote import app,evaluate as base_evaluate,sampler_payload
evaluate=base_evaluate.with_options(timeout=1500)
from .policy import decision

OUT=ROOT/'artifacts/terrain-v12-training'

def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True);p=OUT/(name+'.json');tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,indent=2));tmp.replace(p)

def summary(rows,cfg):
    smooth=cfg['smoothness'];complete=[];quiet=[]
    for r in rows:
        e=r['episode'];m=e['balance_metrics'];ok=r['complete_sequence_success'];complete.append(ok)
        quiet.append(bool(ok and m['roll_rms_deg']<=smooth['roll_rms_degrees_max']
            and m['roll_peak_deg']<=smooth['roll_peak_degrees_max']
            and m['lateral_rms_m']<=smooth['path_lateral_rms_m_max']
            and m['lateral_peak_to_peak_m']<=smooth['path_lateral_peak_to_peak_m_max']
            and e['duration']<=smooth['sequence_time_seconds_max']
            and sum(e['foot_slip_estimate_m'].values())<=smooth['loaded_contact_travel_estimate_m_max']))
    n=len(rows);k=sum(complete);z=1.96;den=1+z*z/max(1,n);center=(k/max(1,n)+z*z/(2*max(1,n)))/den
    error=z*math.sqrt(k/max(1,n)*(1-k/max(1,n))/max(1,n)+z*z/(4*max(1,n)**2))/den
    recovered=[x for r in rows for x in r['episode'].get('recoveries',[]) if x['success']]
    return {'n':n,'complete_successes':k,'smooth_complete_successes':sum(quiet),
        'wilson_95_complete_rate':[max(0,center-error),min(1,center+error)],
        'task_successes':{t:sum(r['episode']['results'].get(t,{}).get('success',False) for r in rows) for t in TASKS},
        'falls':sum(r['episode']['fall'] for r in rows),'invalid_contacts':sum(r['episode'].get('invalid_contact',False) for r in rows),
        'mean_duration_s':float(np.mean([r['episode']['duration'] for r in rows])),
        'mean_roll_rms_deg':float(np.mean([r['episode']['balance_metrics']['roll_rms_deg'] for r in rows])),
        'mean_contact_travel_m':float(np.mean([sum(r['episode']['foot_slip_estimate_m'].values()) for r in rows])),
        'recovery_successes':len(recovered),'successful_recovery_mean_joint_travel_rad':float(np.mean([x['arm_joint_travel_rad'] for x in recovered])) if recovered else None}

def rank(s):
    return (s['complete_successes'],-s['falls'],-s['invalid_contacts'],sum(s['task_successes'].values()),
            s['smooth_complete_successes'],s['recovery_successes'],-s['mean_roll_rms_deg'],
            -(s['successful_recovery_mean_joint_travel_rad'] or 0),-s['mean_duration_s'])


def merged_services(a,b):
    records=a.get('records',[])+b.get('records',[]);reads=a.get('reads',[])+b.get('reads',[])
    writers={r['author'] for r in records};readers={r['reader'] for r in reads if r['source_id_verified']}
    return {'actors':{'source':a.get('actors',{}),'continuation':b.get('actors',{})},
        'audiences':{'source':a.get('audiences',{}),'continuation':b.get('audiences',{})},
        'records':records,'reads':reads,'calls':a.get('calls',[])+b.get('calls',[]),
        'sources':a.get('sources',[])+b.get('sources',[]),'decisions':a.get('decisions',[])+b.get('decisions',[]),
        'pending_ingestions':a.get('pending_ingestions',[])+b.get('pending_ingestions',[]),
        'eligibility':{'writers':len(writers),'readers':len(readers),'cross_agent_reads':sum(r['cross_agent_use'] for r in reads),
            'isolation_passed':a.get('eligibility',{}).get('isolation_passed',False) or b.get('eligibility',{}).get('isolation_passed',False)}}

async def main():
    import tinker
    from tinker_cookbook.recipes.decisions import decision_choice_datums,sample_decision
    cfg=json.loads((ROOT/'configs/terrain-v12-resume-training.json').read_text());run_id='mochi-t12-resume-'+os.environ['GITHUB_RUN_ID']
    if not json.loads((ROOT/'configs/terrain-v12.json').read_text())['training_gate_open']:
        raise RuntimeError('Physical reference gate is closed; no training is authorized by this protocol')
    for path,expected in cfg['frozen_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:raise RuntimeError('Frozen source mismatch: '+path)
    source=ROOT/'.cache/terrain-recovery-source'
    previous=json.loads((source/'progress.json').read_text())
    assert previous['optimizer_updates_completed']==0,'Do not repeat completed optimizer updates'
    assert previous['budget_usage_or_reserved'].get('optimizer_updates',0)==0,'Unreconciled optimizer reservation; inspect before resuming from parent'
    assert not previous['held_out_opened'],'Do not retrain after opening the held-out set'
    assert previous['run_id'].endswith(str(cfg['source_run'])),'Wrong source artifact'
    assert previous['remote_reference_passed'] and previous['valid_teacher_sequences']>=1
    assert previous['protocol']['parent_checkpoint_sha256']==cfg['parent_checkpoint_sha256']
    previous_services=previous['services']
    services=TerrainServices();services.run_id=run_id
    services.actors={r:run_id+'-'+r for r in ['researcher','designer','experimenter','critic']}
    services.audience=run_id+'-shared';services.private=run_id+'-critic'
    report={'study':cfg['study'],'run_id':run_id,'source_sha':os.getenv('GITHUB_SHA'),'created_at':now(),
            'status':'running','phase':'Restore validated physical data and optimizer parent','protocol':cfg,'scope':cfg['scope'],
            'optimizer_updates_completed':0,'training_log':[],'checkpoints':[],'held_out_opened':False,
            'physics_receipts':copy.deepcopy(previous['physics_receipts']),'campaign_modal_rollouts_completed':previous['campaign_modal_rollouts_completed'],
            'recovery':{'source_run':cfg['source_run'],'reused_training_data':True,'previous_optimizer_updates_completed':0,'data_recovery':previous.get('data_recovery'),'development_schedule':'Train durable checkpoints before physical development evaluation; labels and optimizer schedule are fixed.'}}
    budget_store=modal.Dict.from_name('mochi-terrain-v12-resume-budget',create_if_missing=True)
    usage=await budget_store.get.aio('usage')
    if usage is None:
        usage={k:0 for k in cfg['bounds'] if k not in ['local_rollouts','modal_concurrency']}
    async def change(kind,n):
        next_value=usage.get(kind,0)+n
        if next_value<0 or next_value>cfg['bounds'][kind]:raise RuntimeError('Hard budget ceiling: '+kind)
        usage[kind]=next_value;await budget_store.put.aio('usage',usage);report['budget_usage_or_reserved']=dict(usage);report['budget_sources']={'original':previous['budget_usage_or_reserved'],'continuation':dict(usage)}
    async def publish():
        report['services']=merged_services(previous_services,services.report());save('progress',report)
        await modal.Dict.from_name('mochi-terrain-v12-progress',create_if_missing=True).put.aio('latest',report)
        print('MOCHI_T12 '+json.dumps({'phase':report['phase'],'updates':report['optimizer_updates_completed'],'usage':usage}),flush=True)
    async def write(role,content,private=False):
        await change('past_writes',1);return await services.write(role,content,private)
    async def read(role,rid,allowed=True):
        await change('past_recalls',1);return await services.read(role,rid,allowed)
    async def physics_batch(function,args,rollout_cap,timeout,inference_cap=0):
        answers=[]
        for begin in range(0,len(args),cfg['bounds']['modal_concurrency']):
            chunk=args[begin:begin+cfg['bounds']['modal_concurrency']];count=len(chunk)
            await change('modal_rollouts',count*rollout_cap)
            await change('modal_cpu_hours',count*timeout/3600)
            if inference_cap:await change('inference_tokens',count*inference_cap)
            completed=[]
            async for row in function.starmap.aio(chunk,order_outputs=True):
                completed.append(row);answers.append(row)
                report['physics_receipts'].append({'phase':report['phase'],'receipt':row['receipt'],'seed':row.get('seed')})
                report['campaign_modal_rollouts_completed']+=row['receipt']['physical_rollouts']
                await publish()
            await change('modal_rollouts',sum(r['receipt']['physical_rollouts'] for r in completed)-count*rollout_cap)
            await change('modal_cpu_hours',sum(r['receipt']['duration_seconds'] for r in completed)/3600-count*timeout/3600)
            if inference_cap:await change('inference_tokens',sum(r['receipt'].get('inference_input_plus_max_output_tokens',0) for r in completed)-count*inference_cap)
        return answers
    async def paired(seeds,models,group,active=None):
        raw=await physics_batch(evaluate,[(seed,[(label,payload)],run_id,group,active) for seed in seeds for label,payload in models],1,1500,5000)
        bundles=[]
        for seed in seeds:
            selected=[r for r in raw if r['seed']==seed]
            bundles.append({'seed':seed,'results':{label:r['results'][label] for r in selected for label in r['results']},
                'receipt':{'provider':'Modal','physical_rollouts':len(selected),'paired_on_one_worker':False,
                    'duration_seconds':sum(r['receipt']['duration_seconds'] for r in selected),'component_receipts':[r['receipt'] for r in selected]}})
        return bundles
    start=time.perf_counter();paths={};snapshots={};rng=np.random.default_rng(cfg['training']['seed'])
    try:
        records=await inventory(tinker.RestClient());parents=[c for c in records if digest(c.tinker_path)==cfg['parent_checkpoint_sha256']]
        assert len(parents)==1,'Canonical V8 parent missing or ambiguous'
        assert len(records)+len(cfg['training']['checkpoints'])-1<100,'Insufficient checkpoint storage headroom; no deletion authorized'
        parent=parents[0].tinker_path;report['checkpoint_storage_count_before']=len(records)
        await services.setup()
        async with app.run():
            await publish()
            report['remote_reference_passed']=True
            counts=previous['domain_batch_counts'];report['domain_batch_counts']=counts
            report['phase']='Reused physical data; resume real Tinker gradients';await publish()
            data=defaultdict(list,json.loads((source/'training-observations.json').read_text()))
            domains=cfg['training']['domains'];assert all(data[d] for d in domains)
            report['data_audit']=copy.deepcopy(previous['data_audit'])
            report['valid_teacher_sequences']=previous['valid_teacher_sequences']
            report['walking_label_diversity']=previous['walking_label_diversity']
            report['walking_adaptation_qualification']=previous['walking_adaptation_qualification']
            save('training-observations',data)
            trainer=await services.service.create_training_client_from_state_with_optimizer(parent)
            datums={d:decision_choice_datums(services.renderer,[(decision(o),a) for o,a in data[d]]) for d in domains}
            paths['0']={'optimizer':parent};best=None;probe_obs=[data[d][0][0] for d in domains]
            for update in range(cfg['training']['updates']+1):
                if update in cfg['training']['checkpoints']:
                    if update:
                        state=await trainer.save_state(f'mochi_t12_{os.environ["GITHUB_RUN_ID"]}_{update}')
                        paths[str(update)]={'optimizer':state.path,'rng_state':rng.bit_generator.state}
                    sampler=await trainer.save_weights_and_get_sampling_client(kind='snapshot');snapshots[update]=sampler
                    probes=[]
                    for obs in probe_obs:
                        rendering=services.renderer.render(decision(obs));await change('inference_tokens',len(rendering.tokens)+1)
                        probes.append({'domain':obs['domain'],'distribution':await sample_decision(sampler,rendering)})
                    if update==1:
                        starting={p['domain']:p['distribution'] for p in report['checkpoints'][0]['probe_distributions']}
                        changed={p['domain']:max(abs(v-starting[p['domain']][a]) for a,v in p['distribution'].items()) for p in probes}
                        report['first_optimizer_behavioral_probe']=changed
                        assert max(changed.values())>1e-7,'First actual optimizer update produced no detectable policy change'
                    payload=sampler_payload(sampler);save('checkpoint-paths',paths)
                    cp={'update':update,'cumulative_updates':cfg['parent_optimizer_updates']+update,
                        'checkpoint_id':digest(paths[str(update)]['optimizer']),'development':None,'probe_distributions':probes}
                    report['checkpoints'].append(cp);await publish()
                if update==cfg['training']['updates']:break
                batches={d:[int(i) for i in rng.choice(len(data[d]),counts[d],replace=True)] for d in domains}
                tokens=sum(datums[d][i].model_input.length for d in domains for i in batches[d])
                await change('training_token_presentations',tokens);await change('optimizer_updates',1)
                pending=[(d,trainer.forward_backward([datums[d][i] for i in batches[d]],loss_fn='cross_entropy')) for d in domains]
                optimizer=trainer.optim_step(tinker.AdamParams(learning_rate=cfg['training']['learning_rate']))
                losses={d:(await future).metrics for d,future in pending};await optimizer
                report['optimizer_updates_completed']=update+1
                report['training_log'].append({'update':update+1,'domain_loss_metrics':losses,'domain_counts':counts,
                    'tokens':tokens,'batch_sha256':digest(batches),'forward_backward_completed':True,'optimizer_completed':True,'at':now()})
                report['phase']='Tinker six-domain post-training'
                if (update+1)%4==0:await publish()
            for cp in report['checkpoints']:
                update=cp['update'];report['phase']='Development checkpoint '+str(update);await publish()
                bundles=await physics_batch(evaluate,[(seed,[('policy',sampler_payload(snapshots[update]))],run_id,'dev-'+str(update),None) for seed in cfg['development_seeds']],1,1500,5000)
                rows=[b['results']['policy'] for b in bundles];save('checkpoint-'+str(update),rows)
                score=summary(rows,cfg);cp['development']=score
                if best is None or rank(score)>best[0]:best=(rank(score),cp)
                await publish()
            report['selected_checkpoint']=best[1]
            initial={p['domain']:p['distribution'] for p in report['checkpoints'][0]['probe_distributions']}
            report['decision_distribution_change_by_checkpoint']=[{'update':c['update'],
                'maximum_absolute_probability_change_by_domain':{
                    p['domain']:max(abs(v-initial[p['domain']][a]) for a,v in p['distribution'].items())
                    for p in c['probe_distributions']}} for c in report['checkpoints']]
            save('selection-freeze',report)
            try:
                eid=await write('experimenter',{'kind':'observation','data_audit':report['data_audit'],'valid_teacher_sequences':report['valid_teacher_sequences']})
                evidence=await read('critic',eid)
                vid=await write('critic',{'kind':'qualified-conclusion','evidence':evidence,'decision':'Physical dataset meets the frozen checks. Review checkpoint results with those limitations; held-out scenarios remain unopened.'})
                await read('researcher',vid)
                canary=await write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},True);await read('designer',canary,False)
            except TimeoutError as exc:
                report['memory_review_pending']={'stage':'dataset review','error_type':type(exc).__name__,'pending':services.report().get('pending_ingestions',[])}
                await publish()
            selected=best[1]['update'];report['held_out_opened']=True;report['phase']='Unopened held-out sequence evaluation';await publish()
            models=[('parent',sampler_payload(snapshots[0])),('selected',sampler_payload(snapshots[selected])),('fixed',None)]
            bundles=await paired(cfg['held_out_seeds'],models,'held-out')
            results={label:[b['results'][label] for b in bundles] for label,_ in models}
            for label,rows in results.items():save('held-out-'+label,rows)
            report['held_out']={label:summary(rows,cfg) for label,rows in results.items()};report['modal_receipts']=[b['receipt'] for b in bundles]
            report['phase']='Walking, manipulation and recovery isolation';await publish()
            report['isolated']={}
            for name,active in [('walking',['walk']),('manipulation',list(TASKS)),('recovery',['recovery'])]:
                batch=await paired(cfg['held_out_seeds'][:cfg.get('isolation_seed_count',2)],models,'isolation-'+name,active)
                save('isolated-'+name,batch);report['isolated'][name]={label:summary([b['results'][label] for b in batch],cfg) for label,_ in models}
            try:
                eid=await write('experimenter',{'kind':'observation','held_out':report['held_out'],'isolated':report['isolated'],
                        'optimizer_updates_completed':report['optimizer_updates_completed'],'selected_update':selected})
                checked=await read('critic',eid)
                vid=await write('critic',{'kind':'qualified-conclusion','evidence_sha256':digest(checked),
                    'conclusion':'Report measured parent, trained and fixed outcomes separately. The low-level gait weights were not trained. Small simulated pilot; no causal search or memory ablation.'})
                await read('researcher',vid)
            except TimeoutError as exc:
                report['final_memory_review_pending']={'error_type':type(exc).__name__,'pending':services.report().get('pending_ingestions',[])}
                await publish()
        report.update(status='completed',phase='Frozen evaluation complete',completed_at=now(),duration_seconds=time.perf_counter()-start)
        save('report',report);await publish()
    except Exception as exc:
        report.update(status='incomplete',phase='Stopped with preserved evidence',error_type=type(exc).__name__,error=str(exc)[:240])
        save('incomplete',report);await publish();raise
    finally:
        await services.http.aclose()

if __name__=='__main__':
    with modal.enable_output():asyncio.run(main())
