"""Larger, family-matched follow-up on fresh mixtures, separately registered from V1."""
import asyncio,json,os,time,inspect,hashlib
from pathlib import Path
from dataclasses import asdict
from collections import Counter
import numpy as np
import modal
from .simulation import ROOT,Policy,summarize,rollout
from .integrations import Services,now,digest
from .campaign import write,rank
image=modal.Image.debian_slim(python_version='3.11').apt_install('libgl1','libglib2.0-0').pip_install('mujoco==3.3.7','numpy==2.3.4','httpx==0.28.1').env({'PYTHONPATH':'/app/src','MUJOCO_GL':'disable','MOCHI_ROOT':'/app'}).add_local_dir(ROOT/'src',remote_path='/app/src').add_local_dir(ROOT/'configs',remote_path='/app/configs')

CONFIG=json.loads((ROOT/'configs/robustness-v2.json').read_text());FAMILIES=['open_loop','object_feedback','slow_open_loop','earlier_stop']
app=modal.App('mochi-robustness-lab')
@app.function(image=image,cpu=1,memory=1024,timeout=180,max_containers=8)
def robust_trial(policy,seed,shift):
    start=time.perf_counter();r=rollout(Policy(**policy),seed,shift)
    r['remote_receipt']={'provider':'Modal','duration_seconds':time.perf_counter()-start,'cpu_requested':1,'memory_mib':1024};return r

async def batch(policy,seeds,stress=False):
    return [r async for r in robust_trial.starmap.aio([(policy,s,stress or s%2==1) for s in seeds])]

def propose(family,rng,index):
    speed={'open_loop':(.04,.20),'object_feedback':(.06,.18),'slow_open_loop':(.025,.08),'earlier_stop':(.04,.18)}[family]
    stop={'open_loop':(-.01,.025),'object_feedback':(.008,.022),'slow_open_loop':(.005,.025),'earlier_stop':(.018,.028)}[family]
    return Policy(name=f'{family}-{index}',speed=float(rng.uniform(*speed)),stop_distance=float(rng.uniform(*stop)),approach_offset=float(rng.uniform(.04,.06)),contact_height=float(rng.uniform(.486,.490)),recovery=family=='object_feedback')

class ExpandedServices(Services):
    async def setup(self):
        # Reuse proven identity/audience/Tinker setup, then upgrade if advertised.
        await super().setup();self.model='Qwen/Qwen3.5-4B';self.model_selection='Existing verified base model'
        try:
            import tinker
            caps=tinker.RestClient().get_server_capabilities()
            if inspect.isawaitable(caps):caps=await caps
            if hasattr(caps,'result'):caps=caps.result()
            rows=getattr(caps,'supported_models',[])
            names=[getattr(x,'model_name',None) or getattr(x,'model_id',None) for x in rows]
            self.advertised_models=names
            for preferred in ['Qwen/Qwen3.6-35B-A3B','Qwen/Qwen3.8-27B','Qwen/Qwen3.5-9B']:
                if preferred in names:
                    from tinker_cookbook import model_info,renderers
                    from tinker_cookbook.recipes.decisions import DecisionRenderer
                    candidate_sampler=await self.service.create_sampling_client(base_model=preferred)
                    candidate_renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(preferred),candidate_sampler.get_tokenizer()))
                    self.sampler=candidate_sampler;self.renderer=candidate_renderer;self.model=preferred;self.model_selection='Advertised stronger model selected for follow-up';break
        except Exception as error:self.model_selection='Verified 4B fallback; capability inspection: '+type(error).__name__

    async def write(self,role,content,private=False):
        # Store semantic findings in memory; exact numerical records belong in
        # artifacts. The source ID + canonical hash binds those layers together.
        rid=self.run_id+'-record-'+str(len(self.records));at=now();started=time.perf_counter()
        value={'record_id':rid,'author':self.actors[role],'occurred_at':at,'content':content}
        kind=content.get('kind','finding')
        if kind=='observation':
            summary={'kind':kind,'diagnostic':content['diagnostic'],'candidate_successes':[x['summary']['successes'] for x in content['candidates']],'trials_per_candidate':content['candidates'][0]['summary']['n'],'incumbent':content['incumbent'],'environment':content['environment']}
        elif kind=='proposal':summary={k:content[k] for k in ['kind','family','predicted_effect','source_record']}
        else:summary=content
        narrative=f'Mochi {role} record {rid}. Canonical artifact SHA256: {digest(value)}. Finding: '+json.dumps(summary,sort_keys=True)
        x=await self.request('POST','/ingest',{'id':rid,'identity':self.actors[role],'audience':self.private if private else self.audience,'timestamp':at,'label':f'Mochi {role}: {kind}','content':narrative})
        for attempt in range(150):
            status=await self.request('GET','/ingest/'+x['ingestionId'])
            if status.get('status')=='completed':break
            if status.get('status')=='failed':raise RuntimeError('past.dev ingestion failed')
            if attempt%20==19:print('MOCHI_MEMORY_WAIT:'+json.dumps({'record':rid,'seconds':round(time.perf_counter()-started)}),flush=True)
            await asyncio.sleep(2)
        else:raise TimeoutError('past.dev ingestion exceeded the expanded five-minute bound')
        self.records[rid]={'id':rid,'role':role,'author':self.actors[role],'audience':self.private if private else self.audience,'at':at,'sha256':digest(value),'ingestion_id':x['ingestionId'],'write_to_ready_seconds':time.perf_counter()-started,'payload':value,'memory_summary':summary,'memory_layout':'Semantic finding and canonical artifact hash in past.dev; exact parameter/numerical payload in artifact storage'}
        return rid

    async def read(self,role,rid,allowed=True):
        # Semantic recall is not a key/value lookup. Use the documented occurrence
        # window to disambiguate same-topic records, retaining identity ACL checks.
        wanted=self.records[rid];content=wanted['payload']['content'];found=False;attempts=[]
        topic=' '.join(str(content.get(k,'')) for k in ['kind','focus','family','diagnostic'])
        for attempt in range(5 if allowed else 1):
            query=f'Mochi {topic}. Find the evidence authored by {wanted["role"]} in record {rid}.'
            reply=await self.request('POST','/recall',{'identity':self.actors[role],'query':query,'level':'medium','limit':200,'occurredFrom':wanted['at'],'occurredTo':wanted['at']})
            ids={source.get('sourceId') for result in reply.get('results',[]) for source in result.get('sources',[])}
            found=rid in ids;attempts.append({'query':query,'returned_source_ids':sorted(x for x in ids if x),'source_id_verified':found})
            if found or not allowed:break
            await asyncio.sleep(2+attempt)
        if not allowed and (found or 'MOCHI_PRIVATE_CANARY' in json.dumps(reply)):raise RuntimeError('Memory isolation test failed')
        self.reads.append({'reader':self.actors[role],'reader_role':role,'author':wanted['author'],'record_id':rid,'source_id_verified':found,'expected_access':allowed,'cross_agent_use':found and self.actors[role]!=wanted['author'],'sha256':wanted['sha256'] if found else None,'at':now(),'occurrence_window':[wanted['at'],wanted['at']],'attempts':attempts})
        if allowed and not found:raise RuntimeError('Source ID absent from time-scoped semantic recall; no canonical fallback')
        return wanted['payload']['content'] if found else {'access':'denied-as-expected'}

async def run(out,resume=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);s=ExpandedServices();start=time.perf_counter();count=0
    report={'run_id':s.run_id,'study':'robustness-v2','config':CONFIG,'config_sha256':digest(CONFIG),'source_sha':os.getenv('GITHUB_SHA'),'created_at':now(),'scope':'Existing supported right-arm manipulation task; separate from desk-humanoid design concept','rounds':[]}
    recovery=None
    if resume:
        path=Path(resume);checkpoint=json.loads((path/'progress.json').read_text());stopped=json.loads((path/'incomplete.json').read_text());memory=stopped['services']
        assert stopped['run_id']==checkpoint['run_id'] and stopped['rollouts']==checkpoint['rollouts']
        s.run_id=stopped['run_id'];s.actors=memory['actors'];s.audience=memory['audiences']['shared'];s.private=memory['audiences']['critic_private'];s.records={x['id']:x for x in memory['records']};s.reads=memory['reads'];s.decisions=memory['decisions'];s.calls=memory['calls'];s.sources=memory['sources']
        report.update(run_id=s.run_id,rounds=checkpoint['rounds'],created_at=memory['records'][0]['at'],resumed_at=now(),resumed_from='workflow 43767839726',recovery_extra_rollouts=24,recovery_extra_memory_reads=1)
        recovery=checkpoint;count=checkpoint['rollouts']
    try:
        await s.setup();report['model']=s.model;report['model_selection']=s.model_selection
        print('MOCHI_MODEL:'+json.dumps({'model':s.model,'selection':s.model_selection}),flush=True)
        prior_id=report['rounds'][-1]['critic_record'] if recovery else await s.write('critic',{'kind':'prior-result','source':'workflow 43762703104','observation':'V1 selected policy scored 8/12 on heldout but 1/8 under higher friction/mass. Its conventional control scored 6/8 under the shift.','correction':'The V1 gain was not robust. Broaden development and match controller-family access. Use fresh seeds.'})
        selected=Policy();dev=CONFIG['development_seeds'];rng=np.random.default_rng(7621);queries={
          'friction':'robot planar pushing uncertain friction robust feedback adaptive control primary research',
          'contact':'pusher slider closed loop contact loss recovery control paper',
          'velocity':'robot pushing quasi static velocity choice friction motion control research',
          'stopping':'robot manipulation object pushing stopping threshold velocity terminal precision',
          'system_identification':'planar pushing online friction identification adaptive robot control paper',
          'risk':'risk sensitive robust model predictive control planar pushing uncertain contact',
          'curriculum':'robot manipulation domain randomization friction mass generalization curriculum research',
          'stability':'frictional contact hybrid dynamics stable pushing robot feedback controller research'}
        async with app.run():
            incumbent=await batch(asdict(selected),dev);report['initial_results']=incumbent
            if not recovery:count+=len(incumbent)
            else:
                for completed in report['rounds']:
                    queries.pop(completed['focus'])
                    replayed=[asdict(propose(completed['family'],rng,completed['iteration']*4+i)) for i in range(4)]
                    assert replayed==[x['policy'] for x in completed['candidates']]
                    if completed['accepted']:
                        best=max(completed['candidates'],key=rank);selected=Policy(**best['policy']);incumbent=best['results']
                print('MOCHI_RESUMED:'+json.dumps({'rounds':len(report['rounds']),'protocol_rollouts':count,'extra_initial_recovery_rollouts':24}),flush=True)
            for iteration in range(len(report['rounds']),CONFIG['rounds']):
                prior=await s.read('researcher',prior_id);failures=dict(Counter(x['failure'] for x in incumbent))
                context={'prior':prior,'failures':failures}
                if len(queries)>1:
                    focus=await s.decide('researcher','Choose the next uninvestigated mechanism for this failure pattern.',context,list(queries),[prior_id]);query=queries.pop(focus)
                else:
                    focus=next(iter(queries));stance=await s.decide('researcher','For the last registered mechanism, choose whether to investigate the mechanism or seek counterevidence.',context,['mechanism','counterevidence'],[prior_id]);query=queries.pop(focus)+(' counterexamples failure limitations' if stance=='counterevidence' else '')
                evidence=await s.search(query);eid=await s.write('researcher',{'kind':'hypothesis','focus':focus,'failure_counts':failures,'evidence':evidence,'limits':'Sources motivate bounded choices, not guaranteed improvement.'})
                context=await s.read('designer',eid);family=await s.decide('designer','Choose the registered controller family suggested by these sources and failures.',context,FAMILIES,[eid])
                policies=[propose(family,rng,iteration*4+i) for i in range(4)]
                pid=await s.write('designer',{'kind':'proposal','family':family,'predicted_effect':{'open_loop':'Test direct trajectory parameters','object_feedback':'Test object-pose corrective feedback','slow_open_loop':'Reduce impulsive contact while risking stall','earlier_stop':'Increase braking margin while risking undershoot'}[family],'policies':[asdict(x) for x in policies],'source_record':eid})
                plan=await s.read('experimenter',pid)
                diagnostic=await s.decide('experimenter','Which registered diagnostic should the report emphasize? All metrics are still computed.',plan,['mass_friction_failures','contact_loss','overshoot_undershoot'],[pid])
                rows=[]
                for policy in policies:
                    rs=await batch(asdict(policy),dev);count+=len(rs);rows.append({'policy':asdict(policy),'summary':summarize(rs),'results':rs})
                best=max(rows,key=rank);rid=await s.write('experimenter',{'kind':'observation','diagnostic':diagnostic,'candidates':[{'policy':x['policy'],'summary':x['summary']} for x in rows],'incumbent':summarize(incumbent),'environment':'balanced friction/mass mixture'})
                observations=await s.read('critic',rid);support=await s.read('critic',eid)
                verdict=await s.decide('critic','Accept this challenger only with development evidence. Remain explicit about generalization limits.',{'experiment':observations,'source':support},['accept_with_limits','reject'],[rid,eid])
                gate=rank(best)>rank({'summary':summarize(incumbent)});accepted=gate and verdict=='accept_with_limits'
                if accepted:selected=Policy(**best['policy']);incumbent=best['results']
                prior_id=await s.write('critic',{'kind':'qualified-conclusion','accepted':accepted,'verdict':verdict,'gate':gate,'best':best['summary'],'family':family,'limits':'Development mixture only. Heldout and stress cohorts remain untouched.'})
                report['rounds'].append({'iteration':iteration,'focus':focus,'family':family,'accepted':accepted,'candidates':rows,'evidence_record':eid,'critic_record':prior_id})
                print('MOCHI_ROBUSTNESS_ROUND:'+json.dumps({'iteration':iteration,'family':family,'accepted':accepted,'model':s.model,'rollouts':count}),flush=True)
                write(out/'progress.json',{'run_id':s.run_id,'rounds':report['rounds'],'rollouts':count})
            final=await s.read('researcher',prior_id);report['next_question']=await s.decide('researcher','Choose the next prospective question after this development campaign.',final,['new_contact_geometry','new_friction_range','matched_no_search_ablation'],[prior_id])
            report['selected']=asdict(selected);report['frozen_at']=now();report['selected_sha256']=digest(asdict(selected))
            control=[]
            for i in range(32):
                family=str(rng.choice(FAMILIES));policy=propose(family,rng,100+i);rs=await batch(asdict(policy),dev);count+=len(rs);control.append({'policy':asdict(policy),'summary':summarize(rs),'results':rs,'family':family})
            random_best=max(control,key=rank);report['control_candidates']=control
            sections={}
            for label,seeds,stress in [('development',dev,False),('heldout',list(range(51000,51064)),False),('stress',list(range(61000,61064)),True)]:
                scope={};pairs={}
                for name,policy in [('baseline',asdict(Policy())),('research',asdict(selected)),('family_matched_random',random_best['policy'])]:
                    rs=await batch(policy,seeds,stress);count+=len(rs);scope[name]=summarize(rs);pairs[name]=rs
                scope['paired_results']=pairs;sections[label]=scope
            report['evaluation']=sections
        report.update(status='completed',remote_rollouts=count,actual_remote_rollouts=count+report.get('recovery_extra_rollouts',0),services=s.report(),seconds=time.perf_counter()-start,completed_at=now(),claims='Expanded service use on a registered fresh-seed study; no causal search/memory benefit inferred. Recovery reruns are counted separately from protocol trials.')
        assert count==CONFIG['maximum_total_simulations']
        write(out/'report.json',report);return report
    finally:
        if 'evaluation' not in report:write(out/'incomplete.json',{'status':'incomplete','run_id':s.run_id,'rounds_completed':len(report['rounds']),'rollouts':count,'services':s.report()})
        await s.http.aclose()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',default='mochi/artifacts/robustness-v2');p.add_argument('--resume');a=p.parse_args()
    with modal.enable_output():r=asyncio.run(run(a.out,a.resume))
    print('MOCHI_ROBUSTNESS_COMPLETE:'+json.dumps({'run_id':r['run_id'],'rollouts':r['remote_rollouts'],'model':r['model'],'evaluation':{k:{n:v for n,v in x.items() if n!='paired_results'} for k,x in r['evaluation'].items()}}),flush=True)
