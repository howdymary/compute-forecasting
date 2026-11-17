"""Research -> physical labels -> Tinker LoRA post-training -> sealed evaluation.

The model selects a controller once per episode. It never changes the simulator,
verifier, test set, or actuator implementation. No LLM runs in the motor loop.
"""
import asyncio,hashlib,json,os,time
from pathlib import Path
from dataclasses import asdict
from collections import Counter
import numpy as np
import modal
from .physics import ROOT,PROTOCOL,PROTOCOL_SHA,CATALOG,REFERENCE,Controller,summary,observation,scenario
from .remote import app,grid,trial
from .services import DeskServices
from ..integrations import now,digest

OUT=ROOT/'artifacts/desk-v3'
def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True);p=OUT/(name+'.json');q=p.with_suffix('.tmp');q.write_text(json.dumps(value,indent=2));q.replace(p)
def log(event,**fields):print('MOCHI_DESK '+json.dumps({'event':event,'at':now(),**fields}),flush=True)
def rank(r):return (not r['success'],r['pose_error'])
def select_rows(data,choices):return [next(r for r in cell if r['controller']['code']==choice) for cell,choice in zip(data,choices)]
def paired(before,after):
    d=np.asarray([int(b['success'])-int(a['success']) for a,b in zip(before,after)]);rng=np.random.default_rng(9812)
    means=d[rng.integers(0,len(d),size=(10000,len(d)))].mean(axis=1)
    return {'percentage_points':float(d.mean()*100),'paired_bootstrap_95_pp':(np.quantile(means,[.025,.975])*100).tolist(),'improved_cases':int((d>0).sum()),'regressed_cases':int((d<0).sum())}

def make_decision(obs,catalog):
    from tinker_cookbook.recipes.decisions import Decision
    xy=np.array(obs['target_xy_mm'])-np.array(obs['object_xy_mm'])
    state={**obs,'push_distance_mm':round(float(np.linalg.norm(xy)),1),'push_direction_degrees':round(float(np.degrees(np.arctan2(xy[1],xy[0]))),1)}
    prompt=('Select the controller most likely to put the entire rectangular eraser inside its desk target, aligned and stationary for 0.35 seconds, within six seconds. '
      'The supported robot uses the same inverse-kinematics arm controller in every case. Material and geometry are visible; exact friction and mass are unknown. '
      'You select one controller before execution. Observation: '+json.dumps(state,sort_keys=True))
    choices=[(c.code,f'feedback push {c.speed*1000:.0f} mm/s; retract at {c.brake*1000:.0f} mm remaining; yaw-contact alignment gain {c.align*1000:.0f} mm/rad') for c in catalog]
    return Decision(prompt,choices)

async def infer(sampler,renderer,data,catalog):
    from tinker_cookbook.recipes.decisions import sample_decision
    sem=asyncio.Semaphore(8)
    async def one(cell):
        async with sem:
            dec=make_decision(cell[0]['observation'],catalog)
            dist=await sample_decision(sampler,renderer.render(dec));choice=max(dist,key=dist.get)
            return {'seed':cell[0]['scenario']['seed'],'choice':choice,'distribution':dist,'prompt_sha256':digest(dec.prompt if hasattr(dec,'prompt') else str(dec))}
    return await asyncio.gather(*(one(cell) for cell in data))

async def research(s,report):
    catalog=list(CATALOG);calibration=list(range(*PROTOCOL['seed_splits']['calibration']))[:12]
    initial=await grid([REFERENCE],calibration);report['reference']=initial;report['remote_rollouts']+=len(initial)
    failures=dict(Counter(c[0]['failure'] for c in initial));prior=await s.write('experimenter',{'kind':'observation','failure_counts':failures,'reference':asdict(REFERENCE),'scope':'Calibration seeds only; no train, validation or test labels.'})
    for iteration in range(2):
        recalled=await s.read('researcher',prior)
        focus=await s.decide('researcher','Choose a physical failure mechanism to research next.',recalled,['contact_alignment','velocity_and_stopping'],[prior])
        query={'contact_alignment':'robot planar pushing rectangular object orientation contact point feedback control research','velocity_and_stopping':'robot planar pushing velocity friction quasi static stopping precision control paper'}[focus]
        evidence=await s.search(query)
        eid=await s.write('researcher',{'kind':'hypothesis','focus':focus,'evidence':evidence,'claim':'Source mechanisms motivate candidate tests; they do not establish improvement.'})
        found=await s.read('designer',eid)
        mechanism=await s.decide('designer','Use the retrieved research to choose one bounded controller change. No simulator edits are permitted.',found,['slow_contact','stronger_alignment','later_brake'],[eid])
        specs={'slow_contact':(.025,.002,.025),'stronger_alignment':(.040,.003,.038),'later_brake':(.055,-.004,.025)}
        c=Controller(chr(ord('I')+iteration),*specs[mechanism]);catalog.append(c)
        pid=await s.write('designer',{'kind':'proposal','mechanism':mechanism,'controller':asdict(c),'source_record':eid,'prediction':'Change contact speed, yaw correction or braking to reduce the observed pose error; test required.'})
        plan=await s.read('experimenter',pid);measured=await grid([Controller(**plan['controller'])],calibration);report['remote_rollouts']+=len(measured)
        rid=await s.write('experimenter',{'kind':'observation','controller':asdict(c),'summary':summary([x[0] for x in measured]),'source_record':pid,'reference_summary':summary([x[0] for x in initial])})
        facts=await s.read('critic',rid);source=await s.read('critic',eid)
        verdict=await s.decide('critic','Choose the strongest conclusion supported by calibration evidence. Neither option claims held-out improvement.',{'facts':facts,'source':source},['candidate_worth_training','insufficient_reliability'],[rid,eid])
        prior=await s.write('critic',{'kind':'qualified-conclusion','verdict':verdict,'observed':facts['summary'],'correction':'Calibration evidence is not held-out evidence. Keep rejected and successful candidates in the equal-access selector catalog.','source_record':rid})
        report['research'].append({'focus':focus,'mechanism':mechanism,'evidence_record':eid,'proposal_record':pid,'results':measured,'verdict_record':prior})
        save('progress',report);log('research_round',iteration=iteration,mechanism=mechanism)
    await s.read('researcher',prior)
    canary=await s.write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},private=True);await s.read('designer',canary,allowed=False)
    return catalog

async def run():
    import tinker
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import DecisionRenderer,decision_choice_datums
    started=time.perf_counter();s=DeskServices()
    report={'study':'desk-v3','run_id':s.run_id,'status':'running','created_at':now(),'source_sha':os.getenv('GITHUB_SHA'),'protocol':PROTOCOL,'protocol_sha256':PROTOCOL_SHA,'physics_sha256':hashlib.sha256(Path(__file__).with_name('physics.py').read_bytes()).hexdigest(),'remote_rollouts':0,'research':[],'checkpoints':[],'training_log':[],'scope':'LoRA post-training of an episode-level controller selector; classical supported right-arm contact manipulation, state observations, simulated eraser, no walking or vision.'}
    try:
        log('services_setup');await s.setup()
        async with app.run():
            catalog=await research(s,report)
            report['catalog']=[asdict(c) for c in catalog];report['frozen_at']=now();report['frozen_sha256']=digest({'protocol':PROTOCOL_SHA,'physics':report['physics_sha256'],'catalog':report['catalog']});save('frozen-protocol',report)
            datasets={}
            for split in ['train','validation']:
                log('modal_dataset_start',split=split)
                seeds=list(range(*PROTOCOL['seed_splits'][split]));datasets[split]=await grid(catalog,seeds);report['remote_rollouts']+=len(seeds)*len(catalog);save(split+'-outcomes',datasets[split]);log('modal_dataset_done',split=split,rollouts=len(seeds)*len(catalog))
            train=datasets['train'];val=datasets['validation'];labels=[min(cell,key=rank)['controller']['code'] for cell in train]
            fixed=min(catalog,key=lambda c:(-sum(next(r for r in cell if r['controller']['code']==c.code)['success'] for cell in train),sum(next(r for r in cell if r['controller']['code']==c.code)['pose_error'] for cell in train)))
            report['data_audit']={'training_examples':len(train),'label_counts':dict(Counter(labels)),'outcome_informative_examples':sum(len({r['success'] for r in cell})>1 for cell in train),'fixed_controller_train_selected':asdict(fixed),'hidden_fields_excluded':['mass','friction','seed','teacher_labels','validation_outcomes','test_outcomes']};save('data-audit',report['data_audit'])
            cfg=PROTOCOL['training'];rng=np.random.default_rng(8127)
            trainer=await s.service.create_lora_training_client(base_model=cfg['base_model'],rank=cfg['lora_rank'],seed=8127)
            renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(cfg['base_model']),trainer.get_tokenizer()))
            datums=decision_choice_datums(renderer,[(make_decision(cell[0]['observation'],catalog),label) for cell,label in zip(train,labels)])
            private={};best=None
            for update in range(cfg['maximum_updates']+1):
                if update in cfg['checkpoints']:
                    state=await trainer.save_state(f'desk_v3_{update}');weights=await trainer.save_weights_for_sampler(f'desk_v3_{update}')
                    sampler=await s.service.create_sampling_client(model_path=weights.path)
                    decisions=await infer(sampler,renderer,val,catalog);rows=select_rows(val,[x['choice'] for x in decisions]);score=summary(rows)
                    cp={'update':update,'checkpoint_id':hashlib.sha256(weights.path.encode()).hexdigest()[:20],'optimizer_state_id':hashlib.sha256(state.path.encode()).hexdigest()[:20],'validation':score,'decisions':decisions,'created_at':now()}
                    report['checkpoints'].append(cp);private[update]={'weights':weights.path,'state':state.path,'rng_state':rng.bit_generator.state}
                    cache=ROOT/'.cache';cache.mkdir(exist_ok=True);(cache/'desk-training-state.json').write_text(json.dumps(private,indent=2))
                    if best is None or (-score['successes'],score['mean_pose_error'])<(-best['validation']['successes'],best['validation']['mean_pose_error']):best=cp
                    save('progress',report);log('checkpoint',update=update,validation=score,checkpoint_id=cp['checkpoint_id'])
                if update==cfg['maximum_updates']:break
                indices=rng.integers(0,len(datums),cfg['batch_size']);batch=[datums[int(i)] for i in indices]
                fw=trainer.forward_backward(batch,loss_fn='cross_entropy');op=trainer.optim_step(tinker.AdamParams(learning_rate=cfg['learning_rate']))
                result=await fw;optimizer=await op
                metrics=result.metrics if hasattr(result,'metrics') else {};entry={'update':update+1,'batch_size':len(batch),'batch_indices_sha256':digest(indices.tolist()),'learning_rate':cfg['learning_rate'],'metrics':metrics,'forward_backward_completed':True,'optimizer_completed':True,'at':now()}
                report['training_log'].append(entry);save('progress',report)
                if (update+1)%5==0:log('optimizer_update',update=update+1,metrics=metrics)
            report['selected_checkpoint']={k:v for k,v in best.items() if k!='decisions'};report['checkpoint_frozen_at']=now();report['test_not_yet_executed']=True;save('checkpoint-freeze',report)
            log('test_unsealed',selected_update=best['update'])
            testseeds=list(range(*PROTOCOL['seed_splits']['test']));test=await grid(catalog,testseeds);report['remote_rollouts']+=len(testseeds)*len(catalog);save('test-outcomes',test)
            evaluations={};decision_sets={}
            for label,update in [('starting_model',0),('post_trained_model',best['update'])]:
                sampler=await s.service.create_sampling_client(model_path=private[update]['weights']);decs=await infer(sampler,renderer,test,catalog);decision_sets[label]=decs;evaluations[label]=select_rows(test,[x['choice'] for x in decs])
            evaluations['fixed_controller']=select_rows(test,[fixed.code]*len(test))
            rr=np.random.default_rng(9971);evaluations['random_selector']=select_rows(test,[str(rr.choice([c.code for c in catalog])) for _ in test]);evaluations['oracle_upper_bound']=[min(cell,key=rank) for cell in test]
            report['evaluation']={k:summary(v) for k,v in evaluations.items()};report['paired_improvement']=paired(evaluations['starting_model'],evaluations['post_trained_model']);report['test_decisions']=decision_sets;report['test_not_yet_executed']=False
            save('test-evaluation',{'summaries':report['evaluation'],'paired_improvement':report['paired_improvement'],'paired_results':evaluations,'decisions':decision_sets})
            # Prefer a paired failure/success from the test cohort; disclose the selection.
            candidates=[i for i,(a,b) in enumerate(zip(evaluations['starting_model'],evaluations['post_trained_model'])) if not a['success'] and b['success']]
            if not candidates:candidates=[i for i,(a,b) in enumerate(zip(evaluations['starting_model'],evaluations['post_trained_model'])) if b['pose_error']<a['pose_error']]
            chosen=candidates[0] if candidates else 0;seed=testseeds[chosen];trajectories={}
            for label in ['starting_model','post_trained_model']:
                row=evaluations[label][chosen];trajectories[label]=await trial.remote.aio(row['controller'],seed,True);report['remote_rollouts']+=1
            save('demo',{'selection':'First test scenario with starting-model failure and post-trained success, else first lower-error case; illustrative, not a separate evaluation.','seed':seed,'episodes':trajectories})
            evidence=await s.write('experimenter',{'kind':'observation','evaluation':report['evaluation'],'paired_improvement':report['paired_improvement'],'updates':len(report['training_log']),'selected_update':best['update'],'scope':'Fresh sealed test scenarios, same catalog, same observation, same simulator.'})
            checked=await s.read('critic',evidence);verdict=await s.decide('critic','Qualify this result. Does the paired interval support a clear gain or only a limited observation?',checked,['measured_gain_with_limits','inconclusive_generalization'],[evidence])
            rid=await s.write('critic',{'kind':'conclusion','verdict':verdict,'facts':checked,'limits':'One training seed; simulated states; no hardware transfer; no causal Exa or memory ablation; does not establish neural low-level motor learning.'});await s.read('researcher',rid)
        report.update(status='completed',services=s.report(),completed_at=now(),duration_seconds=time.perf_counter()-started,optimizer_updates_completed=len(report['training_log']))
        save('report',report);log('completed',evaluation=report['evaluation'],paired=report['paired_improvement'])
    except Exception as error:
        report.update(status='incomplete',error_type=type(error).__name__,services=s.report(),duration_seconds=time.perf_counter()-started);save('incomplete',report);raise
    finally:await s.http.aclose()

if __name__=='__main__':
    with modal.enable_output():asyncio.run(run())
