"""Evaluation-only continuation of durable V12 states. Zero optimizer calls.

Reuse completed outcomes, including failures; rerun only missing infrastructure
results. Preserve an already frozen selection if held-out testing began.
"""
import asyncio,copy,gzip,hashlib,json,os,shutil,time
from pathlib import Path
import modal
from modal.exception import NotFoundError
from ..curriculum.world import ROOT
from ..integrations import now,digest
from .learning_remote import sampler_payload,volume,compact
from .evaluation_remote import app,evaluate
from .train import summary,rank
from .services import TerrainServices
from .resume_training import merged_services

OUT=ROOT/'artifacts/terrain-v12-training'

def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True);p=OUT/(name+'.json');tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(p)

async def main():
    import tinker
    cfg=json.loads((ROOT/'configs/terrain-v12-finalize.json').read_text())
    source=Path(os.environ['MOCHI_RECOVERY_SOURCE'])
    original=json.loads((source/'progress.json').read_text())
    assert original['remote_reference_passed'],'Missing physical reference'
    protocol=original['protocol']
    for path,sha in protocol['frozen_sha256'].items():
        actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
        if path in cfg.get('infrastructure_repairs',{}):
            repair=cfg['infrastructure_repairs'][path]
            assert sha==repair['source_sha256'] and actual==repair['repaired_sha256'],'Undeclared evaluator repair'
        else:assert actual==sha,'Controller changed: '+path
    paths=json.loads((source/'checkpoint-paths.json').read_text())
    updates=original['optimizer_updates_completed'];assert updates>0,'No durable trained state; resume from the saved data instead'
    assert max(map(int,paths))<=updates,'Checkpoint update exceeds recorded optimizer evidence'
    assert len(original['training_log'])==updates and all(x['optimizer_completed'] and x['forward_backward_completed'] for x in original['training_log'])
    assert digest(paths['0']['optimizer'])==protocol['parent_checkpoint_sha256']
    for p in source.glob('*.json'):
        OUT.mkdir(parents=True,exist_ok=True);shutil.copy2(p,OUT/p.name)
    previous_recovery=original.get('recovery',{})
    prior_evaluations=list(dict.fromkeys(previous_recovery.get('previous_evaluation_runs',[])+([str(previous_recovery['evaluation_run'])] if previous_recovery.get('evaluation_run') else [])+list(map(str,cfg.get('reuse_evaluation_runs',[])))))
    report=copy.deepcopy(original);old_run=original['run_id'];run_id='mochi-t12-final-'+os.environ['GITHUB_RUN_ID']
    report.update(status='running',phase='Restore durable checkpoints for evaluation',recovery={
        'source_training_run':previous_recovery.get('source_training_run',cfg['source_run']),'source_artifact_run':cfg['source_run'],'evaluation_run':os.environ['GITHUB_RUN_ID'],'previous_evaluation_runs':prior_evaluations,
        'evaluation_source_sha':os.environ.get('GITHUB_SHA'),'extra_optimizer_updates':0,
        'original_error_type':original.get('error_type'),'deadline_seconds':cfg['evaluation_timeout_s'],
        'physics_unchanged':True,'infrastructure_repairs':cfg.get('infrastructure_repairs',{}),'unavailable_completed_updates_after_last_durable':updates-max(map(int,paths)),
        'evaluated_checkpoint_updates':sorted(map(int,paths)),'reuse_policy':'Reuse completed physical outcomes, including failures. Fill missing outputs only.'})
    report.pop('error',None);report.pop('error_type',None)
    extra=modal.Dict.from_name('mochi-terrain-v12-final-budget',create_if_missing=True)
    usage=await extra.get.aio('usage') or {'modal_rollouts':0,'modal_cpu_hours':0.,'inference_tokens':0,'past_writes':0,'past_recalls':0}
    lock=asyncio.Lock();status=modal.Dict.from_name('mochi-terrain-v12-progress',create_if_missing=True)
    async def change(kind,n):
        async with lock:
            value=usage.get(kind,0)+n
            if not 0<=value<=cfg['bounds'][kind]:raise RuntimeError('Final-evaluation bound reached: '+kind)
            usage[kind]=value;await extra.put.aio('usage',dict(usage))
    async def publish():
        report['recovery']['usage_or_reserved']=dict(usage)
        report['recovery']['previous_budget_sources']=original.get('budget_sources',{})
        save('progress',report);await status.put.aio('latest',json.loads(json.dumps(report)))
    # This changes a deadline, not the function body, image, controller or weights.
    function=evaluate.with_options(timeout=cfg['evaluation_timeout_s'])
    clients=[];snapshots={};started=time.perf_counter();new_results={}
    async def cached(group,seed,label):
        local=source/f'recovered-{group}-{seed}-{label}.json'
        if local.exists():
            row=json.loads(local.read_text());assert row['seed']==seed
            if row.get('failure')!='inference_token_limit':return row
        prefixes=['mochi-t12-final-'+value for value in reversed(prior_evaluations)]+[old_run]
        for prefix in prefixes:
            path=f'{prefix}/{group}-{seed}-{label}.json.gz'
            try:
                chunks=[]
                async for part in volume.read_file.aio(path):chunks.append(part)
                raw=gzip.decompress(b''.join(chunks));row=json.loads(raw)
            except (FileNotFoundError,NotFoundError):continue
            assert row['seed']==seed
            if row.get('failure')=='inference_token_limit':continue
            row['archive']={'volume':'mochi-terrain-v12-artifacts','path':path,'uncompressed_sha256':hashlib.sha256(raw).hexdigest()}
            return compact(row)
        return None
    async def batch(seeds,models,group,domains=None):
        results={};queue=asyncio.Queue()
        for seed in seeds:
            for label,payload in models:
                row=await cached(group,seed,label)
                if row is not None:results[(seed,label)]=row
                else:queue.put_nowait((seed,label,payload))
        async def worker():
            while True:
                try:seed,label,payload=queue.get_nowait()
                except asyncio.QueueEmpty:return
                await change('modal_rollouts',1);await change('modal_cpu_hours',cfg['evaluation_timeout_s']/3600)
                await change('inference_tokens',24000 if payload else 0)
                bundle=await function.remote.aio(seed,[(label,payload)],run_id,group,domains)
                receipt=bundle['receipt'];results[(seed,label)]=bundle['results'][label]
                await change('modal_cpu_hours',(receipt['duration_seconds']-cfg['evaluation_timeout_s'])/3600)
                if payload:await change('inference_tokens',receipt['inference_input_plus_max_output_tokens']-24000)
                report.setdefault('physics_receipts',[]).append({'phase':group,'seed':seed,'model':label,'receipt':receipt})
                report['campaign_modal_rollouts_completed']+=receipt['physical_rollouts']
                save(f'recovered-{group}-{seed}-{label}',results[(seed,label)]);await publish();queue.task_done()
        await asyncio.gather(*(worker() for _ in range(min(cfg['bounds']['modal_concurrency'],queue.qsize()))))
        return {label:[results[(seed,label)] for seed in seeds] for label,_ in models}
    try:
        for key in sorted(paths,key=int):
            service=tinker.ServiceClient(display_name=run_id+'-'+key);clients.append(service)
            restored=await service.create_training_client_from_state(paths[key]['optimizer'])
            snapshots[int(key)]=await restored.save_weights_and_get_sampling_client(kind='snapshot')
        await publish()
        async with app.run():
            checkpoints={c['update']:c for c in original['checkpoints']}
            for update in sorted(snapshots):
                path=source/f'checkpoint-{update}.json'
                if path.exists():rows=json.loads(path.read_text())
                else:
                    report['phase']='Finish development checkpoint '+str(update);await publish()
                    rows=(await batch(protocol['development_seeds'],[('policy',sampler_payload(snapshots[update]))],'dev-'+str(update)))['policy']
                    save('checkpoint-'+str(update),rows)
                if update not in checkpoints:
                    checkpoints[update]={'update':update,'cumulative_updates':protocol['parent_optimizer_updates']+update,
                        'checkpoint_id':digest(paths[str(update)]['optimizer']),'development':summary(rows,protocol),
                        'probe_distributions':[]}
                checkpoints[update]['development']=summary(rows,protocol)
                report['checkpoints']=[checkpoints[k] for k in sorted(checkpoints)]
                await publish()
            report['checkpoints']=[checkpoints[k] for k in sorted(checkpoints)]
            if original['held_out_opened']:
                report['selected_checkpoint']=original['selected_checkpoint']
                report['recovery']['selection_preserved_before_held_out']=True
            else:report['selected_checkpoint']=max(report['checkpoints'],key=lambda c:rank(c['development']))
            save('selection-freeze',report)
            selected=report['selected_checkpoint']['update'];report['held_out_opened']=True
            report['phase']='Complete paired held-out checkpoint tests';await publish()
            models=[('parent',sampler_payload(snapshots[0])),('selected',sampler_payload(snapshots[selected])),('fixed',None)]
            rows=await batch(protocol['held_out_seeds'],models,'held-out')
            for label,values in rows.items():save('held-out-'+label,values)
            report['held_out']={label:summary(values,protocol) for label,values in rows.items()}
            report['isolated']=report.get('isolated') or {}
            for name,active in [('walking',['walk']),('manipulation',['alarm','drawer','laptop','globe']),('recovery',['recovery'])]:
                report['phase']='Finish full-route domain intervention: '+name;await publish()
                values=await batch(protocol['held_out_seeds'][:protocol.get('isolation_seed_count',2)],models,'isolation-'+name,active)
                save('isolated-'+name,values)
                report['isolated'][name]={label:summary(group,protocol) for label,group in values.items()}
            report['recovery']['domain_intervention_limit']='Only the named decision domain uses learned weights; other domains use the fixed policy. These full-route interventions are not exact shared-pose manipulation or disabled-manipulation walking tests.'
            report['phase']='Record checkpoint results and verify cross-role recall';await publish()
            memory=TerrainServices();memory.run_id=run_id
            memory.actors={role:run_id+'-'+role for role in ['researcher','designer','experimenter','critic']}
            memory.audience=run_id+'-shared';memory.private=run_id+'-critic'
            try:
                for role,actor in memory.actors.items():
                    await memory.request('PUT','/identities/'+actor,{'traits':{'project':'mochi-terrain-v12','role':role}})
                for slug,actors in [(memory.audience,list(memory.actors.values())),(memory.private,[memory.actors['critic']])]:
                    assert len(slug)<=40
                    await memory.request('PUT','/audiences/'+slug,{'kind':'fixed','name':'Mochi checkpoint evaluation','identities':actors})
                await change('past_writes',1)
                eid=await memory.write('experimenter',{'kind':'observation','experiment_id':run_id,
                    'training_run':old_run,'optimizer_updates_completed':updates,'selected_update':selected,
                    'held_out':report['held_out'],'domain_interventions':report['isolated']})
                await change('past_recalls',1);evidence=await memory.read('critic',eid)
                await change('past_writes',1)
                vid=await memory.write('critic',{'kind':'qualified-conclusion','experiment_id':run_id,
                    'evidence_record':eid,'evidence_sha256':digest(evidence),
                    'conclusion':'Report measured parent, selected and fixed-controller results, including failures. Native gait weights stayed fixed. Small simulated evaluation; no search or memory causal ablation.'})
                await change('past_recalls',1);await memory.read('researcher',vid)
                await change('past_writes',1);cid=await memory.write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},True)
                await change('past_recalls',1);await memory.read('designer',cid,False)
            except TimeoutError as exc:
                report['final_memory_review_pending']={'error_type':type(exc).__name__,'pending':memory.report().get('pending_ingestions',[])}
            finally:
                report['services']=merged_services(original['services'],memory.report())
                await memory.http.aclose();await publish()
        report.update(status='completed',phase='Frozen checkpoint evaluation complete',completed_at=now())
        report['recovery']['duration_seconds']=time.perf_counter()-started
        save('report',report);await publish();save('report',report)
    except Exception as exc:
        report.update(status='incomplete',phase='Evaluation paused with durable weights preserved',error_type=type(exc).__name__,error=str(exc)[:220])
        save('evaluation-incomplete',report);await publish();raise

if __name__=='__main__':
    with modal.enable_output():asyncio.run(main())
