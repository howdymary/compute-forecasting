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
from .learning_remote import app,evaluate,sampler_payload,volume,compact
from .train import summary,rank

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
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,'Controller changed: '+path
    paths=json.loads((source/'checkpoint-paths.json').read_text())
    updates=original['optimizer_updates_completed'];assert updates>0,'No durable trained state; resume from the saved data instead'
    assert max(map(int,paths))<=updates,'Checkpoint update exceeds recorded optimizer evidence'
    assert len(original['training_log'])==updates and all(x['optimizer_completed'] and x['forward_backward_completed'] for x in original['training_log'])
    assert digest(paths['0']['optimizer'])==protocol['parent_checkpoint_sha256']
    for p in source.glob('*.json'):
        OUT.mkdir(parents=True,exist_ok=True);shutil.copy2(p,OUT/p.name)
    report=copy.deepcopy(original);old_run=original['run_id'];run_id='mochi-t12-final-'+os.environ['GITHUB_RUN_ID']
    report.update(status='running',phase='Restore durable checkpoints for evaluation',recovery={
        'source_training_run':cfg['source_run'],'evaluation_run':os.environ['GITHUB_RUN_ID'],
        'evaluation_source_sha':os.environ.get('GITHUB_SHA'),'extra_optimizer_updates':0,
        'original_error_type':original.get('error_type'),'deadline_seconds':cfg['evaluation_timeout_s'],
        'physics_unchanged':True,'unavailable_completed_updates_after_last_durable':updates-max(map(int,paths)),
        'evaluated_checkpoint_updates':sorted(map(int,paths)),'reuse_policy':'Reuse completed physical outcomes, including failures. Fill missing outputs only.'})
    report.pop('error',None);report.pop('error_type',None)
    extra=modal.Dict.from_name('mochi-terrain-v12-final-budget',create_if_missing=True)
    usage=await extra.get.aio('usage') or {'modal_rollouts':0,'modal_cpu_hours':0.,'inference_tokens':0}
    lock=asyncio.Lock();status=modal.Dict.from_name('mochi-terrain-v12-progress',create_if_missing=True)
    async def change(kind,n):
        async with lock:
            value=usage.get(kind,0)+n
            if not 0<=value<=cfg['bounds'][kind]:raise RuntimeError('Final-evaluation bound reached: '+kind)
            usage[kind]=value;await extra.put.aio('usage',dict(usage))
    async def publish():
        report['recovery']['usage_or_reserved']=dict(usage)
        save('progress',report);await status.put.aio('latest',json.loads(json.dumps(report)))
    # This changes a deadline, not the function body, image, controller or weights.
    function=evaluate.with_options(timeout=cfg['evaluation_timeout_s'])
    clients=[];snapshots={};started=time.perf_counter();new_results={}
    async def cached(group,seed,label):
        path=f'{old_run}/{group}-{seed}-{label}.json.gz'
        try:
            chunks=[]
            async for part in volume.read_file.aio(path):chunks.append(part)
            raw=gzip.decompress(b''.join(chunks));row=json.loads(raw)
        except (FileNotFoundError,NotFoundError):return None
        row['archive']={'volume':'mochi-terrain-v12-artifacts','path':path,'uncompressed_sha256':hashlib.sha256(raw).hexdigest()}
        return compact(row)
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
                await change('inference_tokens',5000 if payload else 0)
                bundle=await function.remote.aio(seed,[(label,payload)],run_id,group,domains)
                receipt=bundle['receipt'];results[(seed,label)]=bundle['results'][label]
                await change('modal_cpu_hours',(receipt['duration_seconds']-cfg['evaluation_timeout_s'])/3600)
                if payload:await change('inference_tokens',receipt['inference_input_plus_max_output_tokens']-5000)
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
            report['isolated']=report.get('isolated',{})
            for name,active in [('walking',['walk']),('manipulation',['alarm','drawer','laptop','globe']),('recovery',['recovery'])]:
                report['phase']='Finish full-route domain intervention: '+name;await publish()
                values=await batch(protocol['held_out_seeds'][:2],models,'isolation-'+name,active)
                save('isolated-'+name,values)
                report['isolated'][name]={label:summary(group,protocol) for label,group in values.items()}
            report['recovery']['domain_intervention_limit']='Only the named decision domain uses learned weights; other domains use the fixed policy. These full-route interventions are not exact shared-pose manipulation or disabled-manipulation walking tests.'
        report.update(status='completed',phase='Frozen checkpoint evaluation complete',completed_at=now())
        report['recovery']['duration_seconds']=time.perf_counter()-started
        save('report',report);await publish();save('report',report)
    except Exception as exc:
        report.update(status='incomplete',phase='Evaluation paused with durable weights preserved',error_type=type(exc).__name__,error=str(exc)[:220])
        save('evaluation-incomplete',report);await publish();raise

if __name__=='__main__':
    with modal.enable_output():asyncio.run(main())
