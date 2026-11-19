"""Matched physical branches and checkpoint inference on a frozen V12 image."""
import asyncio,dataclasses,gzip,hashlib,json,os,pickle,platform,time
from pathlib import Path

import modal
from ..curriculum.remote import ROOT,base_image,with_assets

app=modal.App('mochi-terrain-v12-learning')
image=(with_assets(base_image.env({'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'}).pip_install('onnxruntime==1.32.0','httpx==0.28.1','tinker==0.39.0','tinker-cookbook==0.6.1','transformers==5.23.0','osqp==1.1.1','threadpoolctl==3.6.0'))
       .add_local_dir(ROOT/'configs',remote_path='/app/configs')
       .add_local_dir(ROOT/'assets/robot/g1-v11-policy',remote_path='/app/assets/robot/g1-v11-policy'))
secret=modal.Secret.from_dict({k:os.environ[k] for k in ['TINKER_API_KEY'] if k in os.environ})
volume=modal.Volume.from_name('mochi-terrain-v12-artifacts',create_if_missing=True)

def sampler_payload(sampler):
    state=sampler._pickle_state()
    state=dataclasses.replace(state,holder=dataclasses.replace(state.holder,api_key=None,default_headers_overrides={}))
    payload=pickle.dumps(state)
    if os.environ.get('TINKER_API_KEY') and os.environ['TINKER_API_KEY'].encode() in payload:
        raise RuntimeError('Credential in sampler transport')
    return payload

def archive(row,run_id,name):
    raw=json.dumps(row,separators=(',',':')).encode();path=Path('/artifacts')/run_id/(name+'.json.gz')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise RuntimeError('Refuse to overwrite an archived physics result')
    path.write_bytes(gzip.compress(raw,compresslevel=1));volume.commit()
    return {'volume':'mochi-terrain-v12-artifacts','path':str(path.relative_to('/artifacts')),
            'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),'compressed_bytes':path.stat().st_size}

def compact(row):
    e=row.get('episode',{})
    e.pop('control_telemetry',None)
    for r in e.get('balance_measurements',[]):
        for k in ['q','qd','tau','support']:r.pop(k,None)
    return row

def receipt(start,count):
    return {'provider':'Modal','physical_rollouts':count,'cpu':1,'memory_mib':3072,
            'duration_seconds':time.perf_counter()-start,'architecture':platform.machine(),
            'threadpools':__import__('threadpoolctl').threadpool_info(),
            'duration_scope':'Function execution including imports; not an invoice or cold-start billing receipt'}

@app.function(image=image,cpu=1,memory=3072,max_containers=4,timeout=3600,volumes={'/artifacts':volume})
def collect_teacher(seed,run_id,preflight=False):
    started=time.perf_counter()
    import numpy as np
    from .sequence import run,PhysicalStop
    from .snapshot import branch
    from .policy import fixed,observation,execute
    from ..balanced.verification import metrics
    count=1;examples=[];trials=[]
    def choose(w,domain,task,default,choices):
        nonlocal count
        if preflight:return fixed(w,domain,task,default,choices)
        observed=observation(w,domain,task);outcomes=[]
        initial=hashlib.sha256(np.r_[w.d.qpos,w.d.qvel,w.d.ctrl,float(w.d.time)].tobytes()).hexdigest()
        for action in choices:
            if count>=37:raise RuntimeError('Teacher rollout ceiling')
            count+=1;clone=branch(w);start=float(clone.d.time);index=len(clone.measurements)
            try:
                result=execute(clone,domain,task,action)
                success=bool(all(x['success'] for x in result)) if domain=='walk' else bool(result['success'])
                detail={'arrivals':result} if domain=='walk' else result
                failure=None
            except PhysicalStop as exc:
                success=False;detail={};failure=str(exc)
            measured=metrics(clone.measurements[index:])
            outcome={'action':action,'success':success,'duration_s':float(clone.d.time)-start,
                     'failure':failure,'result':detail,'metrics':measured,'initial_state_sha256':initial,
                     'fall':clone.fall,'invalid_contact':clone.invalid_contact}
            outcomes.append(outcome)
        valid=[r for r in outcomes if r['success'] and not r['fall'] and not r['invalid_contact']]
        trials.append({'domain':domain,'task':task,'observation':observed,'outcomes':outcomes})
        if not valid:raise PhysicalStop('teacher_no_valid_action:'+domain+':'+task)
        def rank(r):
            if domain=='recovery':return (r['result']['arm_joint_travel_rad'],r['duration_s'])
            if domain=='walk':return (round(r['metrics']['roll_rms_deg']/.5),round(r['metrics']['lateral_rms_m']/.002),r['duration_s'])
            return (r['result']['max_force_n'],r['duration_s'])
        best=min(valid,key=rank);action=best['action']
        examples.append({'domain':domain,'task':task,'observation':observed,'action':action,
                         'initial_state_sha256':initial,'outcomes_sha256':hashlib.sha256(json.dumps(outcomes,sort_keys=True).encode()).hexdigest()})
        w.decisions.append({'t':float(w.d.time),'observation':observed,'action':action,'source':'physically evaluated training branches'})
        return action
    row=run(seed,True,choose=choose)
    answer={'seed':seed,'valid':row['complete_sequence_success'],'examples':examples,'trials':trials,
            'row':row,'receipt':receipt(started,count),'preflight':preflight}
    answer['archive']=archive(answer,run_id,('preflight-' if preflight else 'teacher-')+str(seed))
    compact(row)
    return answer

@app.function(image=image,secrets=[secret],cpu=1,memory=3072,max_containers=4,timeout=900,volumes={'/artifacts':volume})
def evaluate(seed,models,run_id,group,domains=None):
    started=time.perf_counter()
    async def body():
        from tinker.lib.public_interfaces.sampling_client import _unpickle_sampling_client
        from tinker_cookbook import model_info,renderers
        from tinker_cookbook.recipes.decisions import DecisionRenderer,sample_decision
        from .sequence import run,PhysicalStop
        from .policy import fixed,observation,decision
        results={};inference_tokens=0
        for label,payload in models:
            sampler=_unpickle_sampling_client(pickle.loads(payload)) if payload else None
            renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'),sampler.get_tokenizer())) if sampler else None
            loop=asyncio.get_running_loop();used=0;calls=0;cache={};records=[]
            async def select(observed):
                nonlocal used,calls,inference_tokens
                key=json.dumps(observed,sort_keys=True)
                if key in cache:return cache[key]
                rendering=renderer.render(decision(observed));tokens=len(rendering.tokens)+1
                cap=2000 if domains else 5000
                if used+tokens>cap:raise PhysicalStop('inference_token_limit')
                used+=tokens;inference_tokens+=tokens;calls+=1
                probabilities=await sample_decision(sampler,rendering)
                action=max(probabilities,key=probabilities.get)
                cache[key]=(action,probabilities);return cache[key]
            def choose(w,domain,task,default,choices):
                if sampler is None or domains is not None and domain not in domains:
                    return fixed(w,domain,task,default,choices)
                observed=observation(w,domain,task)
                action,probabilities=asyncio.run_coroutine_threadsafe(select(observed),loop).result()
                entry={'t':float(w.d.time),'observation':observed,'action':action,'distribution':probabilities,'source':'Tinker saved weights'}
                records.append(entry);w.decisions.append(entry);return action
            row=await asyncio.to_thread(run,seed,True,choose=choose)
            row['model_decisions']=records;row['inference']={'calls':calls,'input_plus_max_output_tokens':used,
                                                          'cache_entries':len(cache),'learned_domains':domains or 'all six'}
            row['archive']=archive(row,run_id,f'{group}-{seed}-{label}')
            results[label]=compact(row)
        return {'seed':seed,'results':results,'receipt':{**receipt(started,len(models)),
                'inference_input_plus_max_output_tokens':inference_tokens,'paired_on_one_worker':True}}
    return asyncio.run(body())
