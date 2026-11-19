"""Real Modal physics with incremental branch evidence and fixed checkpoints."""
import asyncio
import gzip
import hashlib
import json
import pickle
import time
from pathlib import Path

import modal
import numpy as np

from ..terrain_v12.learning_remote import image, secret, receipt
from ..terrain_v13.remote import Selector as PriorSelector
from ..balanced.sequence import PhysicalStop
from .world import state, restore, branch
from .sequence import run
from .policy import observation, decision, execute, fixed
from .objective import valid_branch, branch_rank, branch_metrics
from .public import export_clip

app=modal.App('mochi-efficient-v15-learning')
volume=modal.Volume.from_name('mochi-efficient-v15-artifacts',create_if_missing=True)


def archive(value,run_id,name):
    raw=json.dumps(value,separators=(',',':')).encode()
    path=Path('/artifacts')/run_id/(name+'.json.gz')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        raise RuntimeError('Preserve immutable V15 artifact: '+name)
    path.write_bytes(gzip.compress(raw,compresslevel=1))
    volume.commit()
    return {'volume':'mochi-efficient-v15-artifacts','path':str(path.relative_to('/artifacts')),
            'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),'compressed_bytes':path.stat().st_size}


def compact(row):
    # Full measurements and trajectories are already immutable in the volume.
    # Returning compact results avoids transferring gigabytes to the coordinator.
    e=row['episode']
    for key in ['trajectory','balance_measurements','control_telemetry']:
        e.pop(key,None)
    return row


class Selector(PriorSelector):
    async def select(self,obs):
        from tinker_cookbook.recipes.decisions import sample_decision
        key=json.dumps(obs,sort_keys=True)
        if key not in self.cache:
            rendering=self.renderer.render(decision(obs))
            tokens=len(rendering.tokens)+1
            if self.used+tokens>self.cap:
                raise PhysicalStop('inference_token_limit')
            self.used+=tokens
            probabilities=await sample_decision(self.sampler,rendering)
            self.cache[key]=(max(probabilities,key=probabilities.get),probabilities)
        return self.cache[key]


def physical_hash(w):
    return hashlib.sha256(np.r_[w.d.qpos,w.d.qvel,w.d.ctrl,w.d.time].tobytes()).hexdigest()


@app.function(image=image,secrets=[secret],cpu=1,memory=3072,max_containers=4,
              timeout=5400,retries=0,volumes={'/artifacts':volume})
def collect(seed,payload,run_id):
    started=time.perf_counter()

    async def body():
        selector=Selector(payload)
        selector.setup()
        count=1
        examples=[]
        trials=[]

        def choose(w,domain,task,default,choices):
            nonlocal count
            obs=observation(w,domain,task)
            preferred,distribution=selector.sync(obs)
            assert preferred in choices
            initial=physical_hash(w)
            outcomes=[]
            for action in choices:
                count+=1
                assert count<=37
                clone=branch(w)
                assert physical_hash(clone)==initial
                start=float(clone.d.time)
                index=len(clone.measurements)
                result={}
                withdrawal=None
                failure=None
                print(json.dumps({'branch_start':{'seed':seed,'domain':domain,'station':task,'action':action}}),flush=True)
                try:
                    result=execute(clone,domain,task,action)
                    success=all(r['success'] for r in result) if domain=='walk' else result['success']
                    if success and domain not in ['walk','recovery']:
                        withdrawal=execute(clone,'recovery',task,'R0')
                        success=success and withdrawal['success']
                except PhysicalStop as exc:
                    success=False
                    failure=str(exc)
                e=clone.episode()
                row={'action':action,'success':bool(success),'failure':failure,
                    'duration_s':float(clone.d.time)-start,'metrics':branch_metrics(clone.measurements[index:]),
                    'steps':clone.step_counter.summary(since=start),'result':result,'coupled_recovery':withdrawal,
                    'fall':clone.fall,'invalid_contact':clone.invalid_contact,
                    'native_smoothness':e['native_smoothness'],
                    'longest_unsupported_seconds':e['longest_unsupported_seconds'],'initial_state_sha256':initial}
                row['archive']=archive(row,run_id,f'branch-{seed}-{domain}-{task}-{action}')
                modal.Dict.from_name(run_id+'-branches',create_if_missing=True).put(f'{seed}-{domain}-{task}-{action}',row)
                outcomes.append(row)
                print(json.dumps({'branch_finished':{'seed':seed,'domain':domain,'station':task,'action':action,
                    'success':row['success'],'valid':valid_branch(row),'steps':row['steps']['attempts'],'seconds':row['duration_s']}}),flush=True)
            valid=[r for r in outcomes if valid_branch(r)]
            trials.append({'domain':domain,'task':task,'observation':obs,'student_preference':preferred,'outcomes':outcomes})
            if not valid:
                raise PhysicalStop('no_valid_training_action:'+domain+':'+task)
            best=min(valid,key=lambda r:branch_rank(domain,r))['action']
            executed=preferred if any(r['action']==preferred for r in valid) else best
            examples.append({'domain':domain,'task':task,'observation':obs,'action':best,'executed_action':executed,
                'guard_intervened':executed!=preferred,'student_distribution':distribution,'initial_state_sha256':initial})
            w.decisions.append({'t':float(w.d.time),'observation':obs,'action':executed,
                                'source':'guarded parent visitation with measured step-efficiency labels'})
            return executed

        row=await asyncio.to_thread(run,seed,True,choose=choose)
        answer={'seed':seed,'valid':row['complete_sequence_success'],'examples':examples,'trials':trials,'row':row,
                'receipt':{**receipt(started,count),'inference_input_plus_max_output_tokens':selector.used}}
        answer['archive']=archive(answer,run_id,'teacher-'+str(seed))
        compact(row)
        answer['receipt']={**receipt(started,count),'inference_input_plus_max_output_tokens':selector.used}
        return answer
    return asyncio.run(body())


@app.function(image=image,secrets=[secret],cpu=1,memory=3072,max_containers=4,
              timeout=1800,retries=0,volumes={'/artifacts':volume})
def evaluate(seed,label,payload,run_id,group,static=None,capture_states=False):
    started=time.perf_counter()

    async def body():
        selector=Selector(payload) if payload else None
        if selector:
            selector.setup()
        decisions=[]
        states={}

        def choose(w,domain,task,default,choices):
            if capture_states:
                states[domain+':'+task]=state(w)
            obs=observation(w,domain,task)
            if selector:
                action,distribution=selector.sync(obs)
            elif static:
                action,distribution=static[domain+':'+task],None
            else:
                return fixed(w,domain,task,default,choices)
            assert action in choices
            row={'t':float(w.d.time),'observation':obs,'action':action,'distribution':distribution,
                 'source':'Tinker saved checkpoint' if selector else 'training-only static preference'}
            decisions.append(row)
            w.decisions.append(row)
            return action

        row=await asyncio.to_thread(run,seed,True,choose=choose)
        row['model_decisions']=decisions
        if capture_states:
            path=Path('/artifacts')/run_id/f'{group}-{seed}-states.pickle'
            assert not path.exists()
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(pickle.dumps(states))
            volume.commit()
            row['supported_states']={'path':str(path.relative_to('/artifacts')),
                'keys':list(states),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        row['archive']=archive(row,run_id,f'{group}-{seed}-{label}')
        row['public_recording']=export_clip(row,run_id,f'{group}-{seed}-{label}',volume)
        return {'seed':seed,'label':label,'group':group,'row':compact(row),
                'receipt':{**receipt(started,1),'inference_input_plus_max_output_tokens':selector.used if selector else 0}}
    return asyncio.run(body())


@app.function(image=image,secrets=[secret],cpu=1,memory=3072,max_containers=4,
              timeout=3600,retries=0,volumes={'/artifacts':volume})
def components(seed,task,models,run_id,reference):
    started=time.perf_counter()

    async def body():
        volume.reload()
        raw=(Path('/artifacts')/reference['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==reference['sha256']
        states=pickle.loads(raw)  # this application's own simulator snapshots
        results=[]
        count=tokens=0
        for domain in ['walk',task,'recovery']:
            key=domain+':'+task
            if key not in states:
                results.append({'domain':domain,'task':task,'status':'reference_not_reached'})
                continue
            initial_ids=[]
            for label,payload in models:
                selector=Selector(payload)
                selector.setup()
                w=restore(states[key],False)
                initial=physical_hash(w)
                initial_ids.append(initial)
                obs=observation(w,domain,task)
                action,distribution=await selector.select(obs)
                start=float(w.d.time)
                index=len(w.measurements)
                count+=1
                failure=None
                result={}
                withdrawal=None
                try:
                    result=await asyncio.to_thread(execute,w,domain,task,action)
                    success=all(r['success'] for r in result) if domain=='walk' else result['success']
                    if success and domain not in ['walk','recovery']:
                        withdrawal=await asyncio.to_thread(execute,w,'recovery',task,'R0')
                        success=success and withdrawal['success']
                except PhysicalStop as exc:
                    success=False
                    failure=str(exc)
                e=w.episode()
                results.append({'domain':domain,'task':task,'model':label,'scope':'Exact-state diagnostic; not a continuous demonstration',
                    'initial_state_sha256':initial,'action':action,'distribution':distribution,'success':bool(success),
                    'failure':failure,'result':result,'coupled_recovery':withdrawal,'fall':w.fall,'invalid_contact':w.invalid_contact,
                    'duration_s':float(w.d.time)-start,'steps':w.step_counter.summary(since=start),
                    'native_smoothness':e['native_smoothness'],
                    'metrics':branch_metrics(w.measurements[index:]),'longest_unsupported_seconds':e['longest_unsupported_seconds']})
                tokens+=selector.used
            assert len(set(initial_ids))==1
        answer={'seed':seed,'task':task,'results':results,'reference':reference,
                'receipt':{**receipt(started,count),'inference_input_plus_max_output_tokens':tokens}}
        answer['archive']=archive(answer,run_id,f'components-{seed}-{task}')
        answer['receipt']={**receipt(started,count),'inference_input_plus_max_output_tokens':tokens}
        return answer
    return asyncio.run(body())
