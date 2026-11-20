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
from ..smooth_v16.remote import (app as physical_app, volume, archive, compact,
    Selector, physical_hash, evaluate, components)
from ..smooth_v16.world import EfficientWorld, state, restore, branch
from ..smooth_v16.policy import observation, choices, execute
from ..smooth_v16.objective import valid_branch, branch_rank, branch_metrics
from ..smooth_v16.navigation import travel_metrics

app=modal.App('mochi-smooth-v16r1-learning').include(physical_app)
OLD_RUN='mochi-t16-44669222147'
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
            row={'study':'mochi-smooth-v16','seed':seed,'complete_sequence_success':complete,
                'failure':None,'arrivals':arrivals,'episode':e,'terrain_conditions':w.terrain_conditions,
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
                if success and domain not in ['walk','recovery']:
                    withdrawal=execute(w,'recovery',task,'R0');success=success and withdrawal['success']
            except PhysicalStop as exc:
                success=False;failure=str(exc)
            e=w.episode()
            row={'action':action,'success':bool(success),'failure':failure,
                'duration_s':float(w.d.time)-start,'metrics':branch_metrics(w.measurements[index:]),
                'steps':w.step_counter.summary(since=start),'result':detail,'coupled_recovery':withdrawal,
                'fall':w.fall,'invalid_contact':w.invalid_contact,'native_smoothness':e['native_smoothness'],
                'longest_unsupported_seconds':e['longest_unsupported_seconds'],'initial_state_sha256':initial}
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
    result['receipt']=receipt(started,1)
    result['receipt']['memory_mib']=4096
    result['receipt']['operation']=operation
    result['receipt']['cursor']=cursor
    journal.put(key,result)
    print(json.dumps({'physical_stage_completed':key,'seconds':result['receipt']['duration_seconds']}),flush=True)
    return result


@app.function(image=image,secrets=[secret],cpu=.125,memory=2048,max_containers=3,
              timeout=10800,retries=0,volumes={'/artifacts':volume})
async def staged_collect(seed,payload,run_id):
    """No physics here. Persist the cursor after each measured state/action stage."""
    started=time.perf_counter()
    selector=Selector(payload);selector.setup()
    progress=modal.Dict.from_name(run_id+'-collectors',create_if_missing=True)
    resume=await progress.get.aio(str(seed))
    history=copy.deepcopy(resume) if resume else {'cursor':0,'examples':[],'trials':[],
        'physical_receipts':[],'reused_outcomes':[],'state':None,'observation':None}
    old=modal.Dict.from_name(OLD_RUN+'-branches')

    async def call(operation,**kwargs):
        result=await physics_stage.remote.aio(seed,run_id,operation,**kwargs)
        identifier=stage_key(seed,kwargs.get('cursor',0),operation,kwargs.get('action'))
        if not any(x['stage_key']==identifier for x in history['physical_receipts']):
            history['physical_receipts'].append({'stage_key':identifier,**result['receipt']})
        return result

    if not history['state']:
        initial=await call('init');history.update(state=initial['state'],observation=initial['observation'])
        await progress.put.aio(str(seed),history)
    for cursor in range(history['cursor'],len(CURSORS)):
        domain,task=CURSORS[cursor];obs=history['observation']
        preferred,distribution=await selector.select(obs)
        outcomes=[]
        for action in choices(domain,task):
            key=f'{seed}-{domain}-{task}-{action}'
            cached=await old.get.aio(key)
            if cached_outcome_eligible(cached,history['state']):
                row=copy.deepcopy(cached)
                reference={'source_run':OLD_RUN,'source_key':key,'initial_state_sha256':cached['initial_state_sha256'],
                           'archive':cached['archive'],
                           'hash_scope':'Legacy qpos, qvel, ctrl and physical time; unchanged source and parent replay. Legacy controller internals were not separately hashed.'}
                if reference not in history['reused_outcomes']:history['reused_outcomes'].append(reference)
            else:
                result=await call('branch',descriptor=history['state'],cursor=cursor,action=action)
                row=result['outcome']
            outcomes.append(row)
            await progress.put.aio(str(seed),history)
        valid=[r for r in outcomes if valid_branch(r)]
        if not valid:raise RuntimeError('No valid physical action: '+domain+':'+task)
        best=min(valid,key=lambda r:branch_rank(domain,r))['action']
        executed=preferred if any(r['action']==preferred for r in valid) else best
        initial=history['state']['physical_state_sha256']
        example={'domain':domain,'task':task,'observation':obs,'action':best,'executed_action':executed,
            'guard_intervened':executed!=preferred,'student_distribution':distribution,'initial_state_sha256':initial}
        trial={'domain':domain,'task':task,'observation':obs,'student_preference':preferred,'outcomes':outcomes}
        selected={'t':None,'observation':obs,'action':executed,
                  'source':'guarded parent visitation with measured step-efficiency labels'}
        # Timestamp is assigned from the actual restored state in the worker.
        result=await call('advance',descriptor=history['state'],cursor=cursor,action=executed,decision=selected)
        history['examples'].append(example);history['trials'].append(trial)
        history.update(cursor=cursor+1,state=result['state'],observation=result['observation'])
        await progress.put.aio(str(seed),history)
        print(json.dumps({'collector_cursor_completed':{'seed':seed,'cursor':cursor+1,
              'reused_outcomes':len(history['reused_outcomes'])}}),flush=True)
    final=await call('finalize',descriptor=history['state'],cursor=len(CURSORS))
    children=history['physical_receipts'];wall=time.perf_counter()-started
    worker_cpu_seconds=sum(r['duration_seconds']*r['cpu'] for r in children)
    # CPU-normalized total permits the unchanged coordinator's budget math;
    # raw per-child execution receipts and supervisor wall time stay explicit.
    answer={'seed':seed,'valid':final['row']['complete_sequence_success'],'examples':history['examples'],
        'trials':history['trials'],'row':final['row'],'reused_outcomes':history['reused_outcomes'],
        'physical_receipts':children,'receipt':{'provider':'Modal','cpu':1,
            'physical_rollouts':len(children),'duration_seconds':worker_cpu_seconds+.125*wall,
            'duration_scope':'CPU-normalized aggregate, not elapsed time; raw child receipts retained.',
            'physics_worker_cpu_seconds':worker_cpu_seconds,'supervisor_cpu':.125,'supervisor_wall_seconds':wall,
            'inference_input_plus_max_output_tokens':selector.used}}
    answer['archive']=archive(answer,run_id,'teacher-'+str(seed))
    return answer
