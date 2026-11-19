"""Same frozen evaluator with larger execution/token allowances."""
import asyncio,pickle,time
import modal
from .learning_remote import image,secret,volume,archive,compact,receipt
app=modal.App('mochi-terrain-v12-weight-evaluation')

@app.function(image=image,secrets=[secret],cpu=1,memory=3072,max_containers=4,timeout=1500,volumes={'/artifacts':volume})
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
                cap=12000 if domains else 24000
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
