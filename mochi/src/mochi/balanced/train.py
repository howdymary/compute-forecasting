"""Actual resumed LoRA gradients, bounded physics and frozen checkpoint tests."""
import asyncio,hashlib,json,math,os,time
from collections import Counter,defaultdict

import modal
import numpy as np
from ..curriculum.world import ROOT,TASKS
from ..desk.services import DeskServices
from ..integrations import now,digest
from ..maintenance.checkpoints_by_date import inventory
from .learning_remote import app,collect_teacher,evaluate,sampler_payload
from .policy import decision

OUT=ROOT/'artifacts/balance-v11-training'

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

async def main():
    import tinker
    from tinker_cookbook.recipes.decisions import decision_choice_datums,sample_decision
    cfg=json.loads((ROOT/'configs/balanced-v11-training.json').read_text());run_id='mochi-b11-'+os.environ['GITHUB_RUN_ID']
    for path,expected in cfg['frozen_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:raise RuntimeError('Frozen source mismatch: '+path)
    services=DeskServices();services.run_id=run_id
    services.actors={r:run_id+'-'+r for r in ['researcher','designer','experimenter','critic']}
    services.audience=run_id+'-shared';services.private=run_id+'-critic'
    report={'study':cfg['study'],'run_id':run_id,'source_sha':os.getenv('GITHUB_SHA'),'created_at':now(),
            'status':'running','phase':'Remote feasibility preflight','protocol':cfg,'scope':cfg['scope'],
            'optimizer_updates_completed':0,'training_log':[],'checkpoints':[],'held_out_opened':False}
    budget_store=modal.Dict.from_name('mochi-balanced-v11-budget',create_if_missing=True)
    usage=await budget_store.get.aio('usage')
    if usage is None:
        usage={'modal_rollouts':2,'modal_cpu_hours':151.918771723/3600,'optimizer_updates':0,
               'training_token_presentations':0,'inference_tokens':4000,'exa_searches':1,'past_writes':5,'past_recalls':5}
    async def change(kind,n):
        next_value=usage.get(kind,0)+n
        if next_value<0 or next_value>cfg['bounds'][kind]:raise RuntimeError('Hard budget ceiling: '+kind)
        usage[kind]=next_value;await budget_store.put.aio('usage',usage);report['budget_usage_or_reserved']=dict(usage)
    async def publish():
        report['services']=services.report();save('progress',report)
        await modal.Dict.from_name('mochi-balanced-v11-progress',create_if_missing=True).put.aio('latest',report)
        print('MOCHI_B11 '+json.dumps({'phase':report['phase'],'updates':report['optimizer_updates_completed'],'usage':usage}),flush=True)
    async def write(role,content,private=False):
        await change('past_writes',1);return await services.write(role,content,private)
    async def read(role,rid,allowed=True):
        await change('past_recalls',1);return await services.read(role,rid,allowed)
    async def physics_batch(function,args,rollout_cap,timeout,inference_cap=0):
        count=len(args);await change('modal_rollouts',count*rollout_cap)
        await change('modal_cpu_hours',count*timeout/3600)
        if inference_cap:await change('inference_tokens',count*inference_cap)
        answers=[]
        async for row in function.starmap.aio(args,order_outputs=True):
            answers.append(row)
        actual_rollouts=sum(r['receipt']['physical_rollouts'] for r in answers)
        await change('modal_rollouts',actual_rollouts-count*rollout_cap)
        await change('modal_cpu_hours',sum(r['receipt']['duration_seconds'] for r in answers)/3600-count*timeout/3600)
        if inference_cap:await change('inference_tokens',sum(r['receipt'].get('inference_input_plus_max_output_tokens',0) for r in answers)-count*inference_cap)
        return answers
    start=time.perf_counter();paths={};snapshots={};rng=np.random.default_rng(cfg['training']['seed'])
    try:
        records=await inventory(tinker.RestClient());parents=[c for c in records if digest(c.tinker_path)==cfg['parent_checkpoint_sha256']]
        assert len(parents)==1,'Canonical V8 parent missing or ambiguous'
        assert len(records)+5<100,'Insufficient checkpoint storage headroom; no deletion authorized'
        parent=parents[0].tinker_path;report['checkpoint_storage_count_before']=len(records)
        await services.setup()
        async with app.run():
            await publish()
            preflight=(await physics_batch(collect_teacher,[(31000,run_id,True)],1,1200))[0]
            save('remote-preflight',preflight)
            if not preflight['valid']:raise RuntimeError('Remote continuous reference failed; gradients remain gated')
            report['remote_reference_passed']=True
            rid=await write('experimenter',{'kind':'observation','study':cfg['study'],'remote_complete_reference':True,
                'failure_history':'Moving-pose capture caused falls or drift; settled phase-freeze then static hold established a reference. Profile A drawer stalled above its braking threshold.',
                'held_out_opened':False})
            seen=await read('researcher',rid);await change('exa_searches',1)
            sources=await services.search('humanoid manipulation standing balance policy transition arm retraction contact force learning controller selection')
            hid=await write('researcher',{'kind':'hypothesis','observation_record':rid,'sources':sources,
                'mechanism':'Train decisions about walking speed/terrain strategies and force/retraction profiles on physical branches. This does not train the native gait network.'})
            idea=await read('designer',hid);await change('inference_tokens',4000)
            allocation=await services.decide('designer','Choose balanced or recovery_first supervision. Both train every domain each update. balanced=16 walking,4 per task,8 recovery. recovery_first=8 walking,4 per task,16 recovery.',{'observation':seen,'evidence':idea},['balanced','recovery_first'],[rid,hid])
            pid=await write('designer',{'kind':'proposal','source_record':hid,'allocation':allocation,'frozen_controller':True})
            proposal=await read('experimenter',pid)
            counts={'walk':16 if proposal['allocation']=='balanced' else 8,**{t:4 for t in TASKS},'recovery':8 if proposal['allocation']=='balanced' else 16}
            report['domain_batch_counts']=counts;report['phase']='Physical training branches on Modal';await publish()
            teachers=await physics_batch(collect_teacher,[(seed,run_id,False) for seed in cfg['training_seeds']],37,1200)
            for row in teachers:save('teacher-'+str(row['seed']),row)
            data=defaultdict(list)
            for row in teachers:
                for e in row['examples']:data[e['domain']].append((e['observation'],e['action']))
            domains=cfg['training']['domains'];report['data_audit']={d:{'examples':len(data[d]),'labels':dict(Counter(a for _,a in data[d]))} for d in domains}
            report['valid_teacher_sequences']=sum(r['valid'] for r in teachers)
            save('training-observations',data)
            assert all(data[d] for d in domains),'Missing physical training domain'
            assert len(report['data_audit']['walk']['labels'])>=2,'No consequential varied walking labels'
            assert report['valid_teacher_sequences']>=1,'No safe training-sequence reference'
            eid=await write('experimenter',{'kind':'observation','data_audit':report['data_audit'],'valid_teacher_sequences':report['valid_teacher_sequences']})
            evidence=await read('critic',eid)
            vid=await write('critic',{'kind':'qualified-conclusion','evidence':evidence,'decision':'Proceed with bounded SFT; branch outcomes and failures are retained. Held-out scenarios remain unopened.'})
            await read('researcher',vid)
            canary=await write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},True);await read('designer',canary,False)
            trainer=await services.service.create_training_client_from_state_with_optimizer(parent)
            datums={d:decision_choice_datums(services.renderer,[(decision(o),a) for o,a in data[d]]) for d in domains}
            paths['0']={'optimizer':parent};best=None;probe_obs=[data[d][0][0] for d in domains]
            for update in range(cfg['training']['updates']+1):
                if update in cfg['training']['checkpoints']:
                    if update:
                        state=await trainer.save_state(f'mochi_b11_{os.environ["GITHUB_RUN_ID"]}_{update}')
                        paths[str(update)]={'optimizer':state.path,'rng_state':rng.bit_generator.state}
                    sampler=await trainer.save_weights_and_get_sampling_client(kind='snapshot');snapshots[update]=sampler
                    probes=[]
                    for obs in probe_obs:
                        rendering=services.renderer.render(decision(obs));await change('inference_tokens',len(rendering.tokens)+1)
                        probes.append({'domain':obs['domain'],'distribution':await sample_decision(sampler,rendering)})
                    payload=sampler_payload(sampler);save('checkpoint-paths',paths)
                    report['phase']='Development checkpoint '+str(update);await publish()
                    bundles=await physics_batch(evaluate,[(seed,[('policy',payload)],run_id,'dev-'+str(update),None) for seed in cfg['development_seeds']],1,900,5000)
                    rows=[b['results']['policy'] for b in bundles];save('checkpoint-'+str(update),rows)
                    s=summary(rows,cfg);cp={'update':update,'cumulative_updates':cfg['parent_optimizer_updates']+update,
                        'checkpoint_id':digest(paths[str(update)]['optimizer']),'development':s,'probe_distributions':probes}
                    report['checkpoints'].append(cp)
                    if best is None or rank(s)>best[0]:best=(rank(s),cp)
                    await publish()
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
            report['selected_checkpoint']=best[1]
            initial={p['domain']:p['distribution'] for p in report['checkpoints'][0]['probe_distributions']}
            report['decision_distribution_change_by_checkpoint']=[{'update':c['update'],
                'maximum_absolute_probability_change_by_domain':{
                    p['domain']:max(abs(v-initial[p['domain']][a]) for a,v in p['distribution'].items())
                    for p in c['probe_distributions']}} for c in report['checkpoints']]
            save('selection-freeze',report)
            selected=best[1]['update'];report['held_out_opened']=True;report['phase']='Unopened held-out sequence evaluation';await publish()
            models=[('parent',sampler_payload(snapshots[0])),('selected',sampler_payload(snapshots[selected])),('fixed',None)]
            bundles=await physics_batch(evaluate,[(s,models,run_id,'held-out',None) for s in cfg['held_out_seeds']],3,900,10000)
            results={label:[b['results'][label] for b in bundles] for label,_ in models}
            for label,rows in results.items():save('held-out-'+label,rows)
            report['held_out']={label:summary(rows,cfg) for label,rows in results.items()};report['modal_receipts']=[b['receipt'] for b in bundles]
            report['phase']='Walking, manipulation and recovery isolation';await publish()
            report['isolated']={}
            for name,active in [('walking',['walk']),('manipulation',list(TASKS)),('recovery',['recovery'])]:
                batch=await physics_batch(evaluate,[(s,models,run_id,'isolation-'+name,active) for s in cfg['held_out_seeds'][:2]],3,900,4000)
                save('isolated-'+name,batch);report['isolated'][name]={label:summary([b['results'][label] for b in batch],cfg) for label,_ in models}
            eid=await write('experimenter',{'kind':'observation','held_out':report['held_out'],'isolated':report['isolated'],
                    'optimizer_updates_completed':report['optimizer_updates_completed'],'selected_update':selected})
            checked=await read('critic',eid)
            vid=await write('critic',{'kind':'qualified-conclusion','evidence_sha256':digest(checked),
                'conclusion':'Report measured parent, trained and fixed outcomes separately. The low-level gait weights were not trained. Small simulated pilot; no causal search or memory ablation.'})
            await read('researcher',vid)
        report.update(status='completed',phase='Frozen evaluation complete',completed_at=now(),duration_seconds=time.perf_counter()-start)
        save('report',report);await publish()
    except Exception as exc:
        report.update(status='incomplete',phase='Stopped with preserved evidence',error_type=type(exc).__name__,error=str(exc)[:240])
        save('incomplete',report);await publish();raise
    finally:
        await services.http.aclose()

if __name__=='__main__':
    with modal.enable_output():asyncio.run(main())
