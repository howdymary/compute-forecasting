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
from ..smooth_v16.world import state, restore, branch
from .sequence import run
from .policy import observation, decision, execute, fixed
from ..smooth_v16.objective import valid_branch, branch_rank, branch_metrics
from ..smooth_v16.public import export_clip

app=modal.App('mochi-smooth-v17-learning')
volume=modal.Volume.from_name('mochi-smooth-v16-artifacts',create_if_missing=True)


def archive(value,run_id,name):
    raw=json.dumps(value,separators=(',',':')).encode()
    path=Path('/artifacts')/run_id/(name+'.json.gz')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        raise RuntimeError('Preserve immutable V16 artifact: '+name)
    path.write_bytes(gzip.compress(raw,compresslevel=1))
    volume.commit()
    return {'volume':'mochi-smooth-v16-artifacts','path':str(path.relative_to('/artifacts')),
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
                 'initial_physical_state_sha256':physical_hash(w),
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
              timeout=1200,retries=0,volumes={'/artifacts':volume})
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
        assert len(models)==1
        answer={'seed':seed,'task':task,'model_label':models[0][0],'results':results,'reference':reference,
                'receipt':{**receipt(started,count),'inference_input_plus_max_output_tokens':tokens}}
        answer['archive']=archive(answer,run_id,f'components-{seed}-{task}-{models[0][0]}')
        answer['receipt']={**receipt(started,count),'inference_input_plus_max_output_tokens':tokens}
        return answer
    return asyncio.run(body())
