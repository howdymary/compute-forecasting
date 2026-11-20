"""Durable physical stages. Final evaluations still use uninterrupted V16 run()."""
import asyncio
import copy
import gzip
import hashlib
import json
import pickle
import time
from pathlib import Path

import modal
from ..balanced.onnx_walk import HubWalker, HoldWalker
from ..balanced.sequence import PhysicalStop
from ..control_v8.verification import full_success
from ..curriculum.world import TASKS
from ..terrain_v12.learning_remote import image, secret, receipt
from .remote import app,volume,archive,compact,Selector,physical_hash
from ..smooth_v16.world import EfficientWorld, state, restore, branch
from .policy import observation,choices,execute
from ..smooth_v16.objective import valid_branch, branch_rank, branch_metrics
from ..smooth_v16.navigation import travel_metrics

OLD_RUN='mochi-t16r1-44686221838'
CURSORS=[(domain,task) for task in TASKS for domain in ['walk',task,'recovery']]


def persist(name, value):
    path=Path('/artifacts')/name
    assert not path.exists(), 'Preserve immutable stage: '+name
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=pickle.dumps(value,protocol=5)
    path.write_bytes(gzip.compress(raw,compresslevel=1,mtime=0))
    volume.commit()
    return {'path':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'physical_state_sha256':physical_hash_from_saved(value['state'])}


def physical_hash_from_saved(saved):
    import numpy as np
    d=saved['data']
    return hashlib.sha256(np.r_[d.qpos,d.qvel,d.ctrl,d.time].tobytes()).hexdigest()


def load(descriptor):
    volume.reload()
    raw=(Path('/artifacts')/descriptor['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==descriptor['sha256']
    result=pickle.loads(gzip.decompress(raw))  # this application's own state only
    assert physical_hash_from_saved(result['state'])==descriptor['physical_state_sha256']
    return result


def cached_outcome_eligible(cached,descriptor):
    return bool(cached and cached['initial_state_sha256']==descriptor['physical_state_sha256'])


def stage_key(seed,cursor,operation,action=None):
    return f'{seed}:{cursor}:{operation}'+(':'+action if action else '')


@app.function(image=image,cpu=1,memory=4096,max_containers=4,timeout=1800,
              retries=0,volumes={'/artifacts':volume})
def physics_stage(seed,run_id,operation,descriptor=None,cursor=0,action=None,decision=None):
    """The sole collection physics function, capped at four active workers."""
    started=time.perf_counter()
    journal=modal.Dict.from_name(run_id+'-stages',create_if_missing=True)
    key=stage_key(seed,cursor,operation,action)
    request={'state':descriptor,'action':action,'decision':decision}
    existing=journal.get(key)
    if existing:
        assert existing.get('request')==request, 'Cached stage request changed: '+key
        assert existing.get('stage_status')=='completed', 'Unfinished stage requires usage reconciliation: '+key
        return {**existing,'retrieved_existing_stage':True}
    journal.put(key,{'stage_status':'started','seed':seed,'operation':operation,'cursor':cursor,
                     'initial_state':descriptor,'request':request,'action':action,'started_unix':time.time()})
    if operation=='init':
        w=EfficientWorld(seed,True)
        w.terrain_controller_history=[];w.use_native_stand=True
        while w.d.time<.4:w.step(standing=True)
        w.walker=HubWalker(w);w.walker=HoldWalker(w)
        saved={'state':state(w,include_history=True),'arrivals':[],'cursor':0}
        result={'state':persist(f'{run_id}/stages/{seed}-0-initial.pickle.gz',saved),
                'observation':observation(w,*CURSORS[0]),'seed':seed}
    else:
        saved=load(descriptor)
        assert saved['cursor']==cursor
        w=restore(saved['state'],True)
        assert physical_hash(w)==descriptor['physical_state_sha256']
        if operation in ['finalize','finalize_failure']:
            if operation=='finalize':
                end=float(w.d.time)+.5
                while w.d.time<end:w.step()
            e=w.episode();arrivals=saved['arrivals']
            complete=bool(full_success(e) and not w.invalid_contact and e['efficiency_validity']
                and e['maximum_applied_base_force']==0 and len(w.recoveries)==4
                and all(r['success'] for r in w.recoveries)
                and all(w.foot_touching(s) for s in ['left','right'])
                and any(a['label']=='book-ascent' for a in arrivals)
                and any(a['label']=='book-top-turnaround' and a['success'] for a in arrivals)
                and any(a['label']=='book-forward-descent' for a in arrivals)
                and bool(e['postit_crossings']))
            row={'study':'mochi-smooth-v17','seed':seed,'complete_sequence_success':complete,
                'failure':None if operation=='finalize' else 'no_valid_training_action','arrivals':arrivals,'episode':e,'terrain_conditions':w.terrain_conditions,
                'direction_metrics':travel_metrics(w.direction_samples),'model_decisions':w.decisions,
                'scope':'Guarded training sequence continued through exact physical/controller snapshots; not a demo recording.'}
            row['archive']=archive(row,run_id,f'teacher-state-continuation-{seed}')
            result={'seed':seed,'row':compact(row)}
        elif operation=='branch':
            domain,task=CURSORS[cursor];w=branch(w);initial=physical_hash(w)
            start=float(w.d.time);index=len(w.measurements);detail={};withdrawal=None;failure=None
            try:
                detail=execute(w,domain,task,action)
                success=all(a['success'] for a in detail) if domain=='walk' else detail['success']
                if success and domain=='alarm' and action=='H0':
                    posttask=persist(f'{run_id}/augmentation/{seed}-H0-posttask.pickle.gz',{'state':state(w,include_history=False),'arrivals':saved['arrivals'],'cursor':2})
                    posttask_observation=observation(w,'recovery','alarm')
                if success and domain not in ['walk','recovery']:
                    recovery_start=float(w.d.time);recovery_index=len(w.measurements);recovery_initial=physical_hash(w)
                    withdrawal=execute(w,'recovery',task,'R4');success=success and withdrawal['success']
            except PhysicalStop as exc:
                success=False;failure=str(exc)
            e=w.episode()
            row={'action':action,'success':bool(success),'failure':failure,
                'duration_s':float(w.d.time)-start,'metrics':branch_metrics(w.measurements[index:]),
                'steps':w.step_counter.summary(since=start),'result':detail,'coupled_recovery':withdrawal,
                'fall':w.fall,'invalid_contact':w.invalid_contact,'native_smoothness':e['native_smoothness'],
                'longest_unsupported_seconds':e['longest_unsupported_seconds'],'initial_state_sha256':initial}
            if domain=='alarm' and action=='H0' and success:
                row['posttask_state']=posttask
                row['posttask_observation']=posttask_observation
                assert recovery_initial==posttask['physical_state_sha256']
                row['coupled_recovery_outcome']={'action':'R4','success':withdrawal['success'],'failure':None,
                    'duration_s':float(w.d.time)-recovery_start,'metrics':branch_metrics(w.measurements[recovery_index:]),
                    'steps':w.step_counter.summary(since=recovery_start),'result':withdrawal,'coupled_recovery':None,
                    'fall':w.fall,'invalid_contact':w.invalid_contact,'native_smoothness':e['native_smoothness'],
                    'longest_unsupported_seconds':e['longest_unsupported_seconds'],'initial_state_sha256':recovery_initial,
                    'scope':'Actual R4 subsegment of this H0 rollout; reused as measured data without another simulation.'}
            row['archive']=archive(row,run_id,f'branch-{seed}-{domain}-{task}-{action}')
            result={'seed':seed,'outcome':row}
        elif operation=='advance':
            domain,task=CURSORS[cursor]
            assert decision['observation']==observation(w,domain,task)
            decision={**decision,'t':float(w.d.time)}
            w.decisions.append(decision)
            detail=execute(w,domain,task,action)
            success=all(r['success'] for r in detail) if domain=='walk' else detail['success']
            assert success, f'Guarded execution failed: {domain}:{task}'
            arrivals=saved['arrivals']+(detail if domain=='walk' else [])
            advanced={'state':state(w,include_history=True),'arrivals':arrivals,'cursor':cursor+1}
            result={'seed':seed,'state':persist(f'{run_id}/stages/{seed}-{cursor+1}-advanced.pickle.gz',advanced),
                'observation':observation(w,*CURSORS[cursor+1]) if cursor+1<len(CURSORS) else None,
                'physical_time':float(w.d.time)}
        else:
            raise ValueError(operation)
    result['request']=request
    result['stage_status']='completed'
    result['receipt']=receipt(started,0 if operation=='finalize_failure' else 1)
    result['receipt']['memory_mib']=4096
    result['receipt']['operation']=operation
    result['receipt']['cursor']=cursor
    journal.put(key,result)
    print(json.dumps({'physical_stage_completed':key,'seconds':result['receipt']['duration_seconds']}),flush=True)
    return result



@app.function(image=image,secrets=[secret],cpu=.125,memory=2048,max_containers=3,
              timeout=3600,retries=0,volumes={'/artifacts':volume})
async def staged_collect(seed,payload,run_id):
    """Offline parent-prefix states plus freshly measured extended actions."""
    started=time.perf_counter();selector=Selector(payload);selector.setup()
    progress=modal.Dict.from_name(run_id+'-collectors',create_if_missing=True)
    history=await progress.get.aio(str(seed))
    if not history:
        old=await modal.Dict.from_name(OLD_RUN+'-collectors').get.aio(str(seed))
        assert old['cursor']>=7 and len(old['examples'])>=7
        stages=modal.Dict.from_name(OLD_RUN+'-stages')
        walk=old['examples'][6]['executed_action']
        source=await stages.get.aio(stage_key(seed,6,'advance',walk))
        ascent=await stages.get.aio(stage_key(seed,0,'advance',old['examples'][0]['executed_action']))
        assert source['stage_status']==ascent['stage_status']=='completed'
        history={'cursor':7,'state':source['state'],'observation':source['observation'],
            'examples':copy.deepcopy(old['examples'][:7]),'trials':copy.deepcopy(old['trials'][:7]),
            'physical_receipts':[],'clock_state':ascent['state'],'clock_observation':ascent['observation'],
            'clock_augmentation_done':False,'historical_prefix':{'run_id':OLD_RUN,'state':source['state'],
                'behavior_policy':'Verified 121-update parent before adding H0/P4. Prefix is recorded history, not a new extended-policy rollout.'}}
        await progress.put.aio(str(seed),history)

    async def call(operation,**kwargs):
        result=await physics_stage.remote.aio(seed,run_id,operation,**kwargs)
        identifier=stage_key(seed,kwargs.get('cursor',0),operation,kwargs.get('action'))
        if not any(x['stage_key']==identifier for x in history['physical_receipts']):
            history['physical_receipts'].append({'stage_key':identifier,**result['receipt']})
        await progress.put.aio(str(seed),history)
        return result

    if not history['clock_augmentation_done']:
        obs={**history['clock_observation'],'available_actions':choices('alarm','alarm')}
        preferred,distribution=await selector.select(obs);outcomes=[]
        for action in choices('alarm','alarm'):
            r=await call('branch',descriptor=history['clock_state'],cursor=1,action=action)
            outcomes.append(r['outcome'])
        valid=[r for r in outcomes if valid_branch(r)]
        assert valid,'No valid clock reach and R4 recovery'
        # Frozen before gradients: reduce the terminal arm excursion first.
        best=min(valid,key=lambda r:(r['coupled_recovery']['arm_joint_travel_rad'],r['duration_s']))['action']
        prior=history['examples'][1]
        history['examples'][1]={**prior,'observation':obs,'action':best,'student_distribution':distribution,
            'label_source':'New measured alternatives from a historical prefix state; fixed R4 withdrawal.',
            'historical_behavior_action':prior['executed_action']}
        history['trials'][1]={'domain':'alarm','task':'alarm','observation':obs,
            'student_preference':preferred,'outcomes':outcomes}
        home=next(r for r in outcomes if r['action']=='H0')
        if home['success'] and home.get('posttask_state'):
            # Train recovery on the actual new reach's terminal state as well.
            descriptor=home['posttask_state']
            recovery_obs=home['posttask_observation']
            recovery_preference,recovery_distribution=await selector.select(recovery_obs)
            recovery_rows=[]
            for action in choices('recovery','alarm'):
                if action=='R4':
                    measured=copy.deepcopy(home['coupled_recovery_outcome']);measured['archive']=home['archive']
                    assert measured['initial_state_sha256']==descriptor['physical_state_sha256']
                    recovery_rows.append(measured)
                else:
                    r=await call('branch',descriptor=descriptor,cursor=2,action=action)
                    recovery_rows.append(r['outcome'])
            valid_recovery=[r for r in recovery_rows if valid_branch(r)]
            assert valid_recovery,'New clock reach has no safe recovery'
            action=min(valid_recovery,key=lambda r:branch_rank('recovery',r))['action']
            history['extra_example']={'domain':'recovery','task':'alarm','observation':recovery_obs,
                'action':action,'executed_action':'R4','guard_intervened':False,
                'student_distribution':recovery_distribution,'initial_state_sha256':descriptor['physical_state_sha256'],
                'label_source':'Measured recovery alternatives from H0 terminal state; not an invented trajectory.'}
            history['extra_trial']={'domain':'recovery','task':'alarm','observation':recovery_obs,
                'student_preference':recovery_preference,'outcomes':recovery_rows}
        history['clock_augmentation_done']=True
        await progress.put.aio(str(seed),history)

    for cursor in range(history['cursor'],len(CURSORS)):
        domain,task=CURSORS[cursor]
        obs={**history['observation'],'available_actions':choices(domain,task)}
        preferred,distribution=await selector.select(obs);outcomes=[]
        for action in choices(domain,task):
            r=await call('branch',descriptor=history['state'],cursor=cursor,action=action)
            outcomes.append(r['outcome'])
        valid=[r for r in outcomes if valid_branch(r)]
        trial={'domain':domain,'task':task,'observation':obs,'student_preference':preferred,'outcomes':outcomes}
        if not valid:
            history['failure']='no_valid_training_action:'+domain+':'+task
            history['failed_trial']=trial
            await progress.put.aio(str(seed),history)
            break
        best=min(valid,key=lambda r:branch_rank(domain,r))['action']
        executed=preferred if any(r['action']==preferred for r in valid) else best
        initial=history['state']['physical_state_sha256']
        example={'domain':domain,'task':task,'observation':obs,'action':best,'executed_action':executed,
            'guard_intervened':executed!=preferred,'student_distribution':distribution,'initial_state_sha256':initial}
        selected={'t':None,'observation':obs,'action':executed,
                  'source':'Measured extended action on a historical parent-prefix state'}
        r=await call('advance',descriptor=history['state'],cursor=cursor,action=executed,decision=selected)
        history['examples'].append(example);history['trials'].append(trial)
        history.update(cursor=cursor+1,state=r['state'],observation=r['observation'])
        await progress.put.aio(str(seed),history)
        print(json.dumps({'collector_cursor_completed':{'seed':seed,'cursor':cursor+1}}),flush=True)
    final=await call('finalize' if history['cursor']==len(CURSORS) else 'finalize_failure',
        descriptor=history['state'],cursor=history['cursor'])
    children=history['physical_receipts'];wall=time.perf_counter()-started
    worker_cpu_seconds=sum(r['duration_seconds']*r['cpu'] for r in children)
    answer={'seed':seed,'valid':final['row']['complete_sequence_success'],
        'examples':history['examples']+([history['extra_example']] if history.get('extra_example') else []),
        'trials':history['trials']+([history['extra_trial']] if history.get('extra_trial') else []),
        'row':final['row'],'historical_prefix':history['historical_prefix'],
        'reused_physical_subsegments':int(bool(history.get('extra_trial'))),
        'failed_trial':history.get('failed_trial'),'physical_receipts':children,
        'receipt':{'provider':'Modal','cpu':1,
            'physical_rollouts':sum(r['physical_rollouts'] for r in children),
            'duration_seconds':worker_cpu_seconds+.125*wall,
            'duration_scope':'CPU-normalized aggregate; raw child receipts and supervisor wall time retained.',
            'physics_worker_cpu_seconds':worker_cpu_seconds,'supervisor_cpu':.125,'supervisor_wall_seconds':wall,
            'inference_input_plus_max_output_tokens':selector.used}}
    answer['archive']=archive(answer,run_id,'teacher-'+str(seed))
    await modal.Dict.from_name(run_id+'-teachers',create_if_missing=True).put.aio(str(seed),answer)
    return answer
