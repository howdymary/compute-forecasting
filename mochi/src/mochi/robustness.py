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
from .remote import image

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
            caps=self.service.get_server_capabilities()
            if inspect.isawaitable(caps):caps=await caps
            if hasattr(caps,'result'):caps=caps.result()
            rows=getattr(caps,'supported_models',[])
            names=[getattr(x,'model_name',None) or getattr(x,'model_id',None) for x in rows]
            for preferred in ['Qwen/Qwen3.5-35B-A3B','Qwen/Qwen3-30B-A3B']:
                if preferred in names:
                    from tinker_cookbook import model_info,renderers
                    from tinker_cookbook.recipes.decisions import DecisionRenderer
                    self.sampler=await self.service.create_sampling_client(base_model=preferred)
                    self.renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(preferred),self.sampler.get_tokenizer()));self.model=preferred;self.model_selection='Advertised stronger model selected for follow-up';break
        except Exception as error:self.model_selection='Verified 4B fallback; capability inspection: '+type(error).__name__

async def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);s=ExpandedServices();start=time.perf_counter();count=0
    report={'run_id':s.run_id,'study':'robustness-v2','config':CONFIG,'config_sha256':digest(CONFIG),'source_sha':os.getenv('GITHUB_SHA'),'created_at':now(),'scope':'Existing supported right-arm manipulation task; separate from desk-humanoid design concept','rounds':[]}
    try:
        await s.setup();report['model']=s.model;report['model_selection']=s.model_selection
        prior_id=await s.write('critic',{'kind':'prior-result','source':'workflow 43762703104','observation':'V1 selected policy scored 8/12 on heldout but 1/8 under higher friction/mass. Its conventional control scored 6/8 under the shift.','correction':'The V1 gain was not robust. Broaden development and match controller-family access. Use fresh seeds.'})
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
            incumbent=await batch(asdict(selected),dev);count+=len(incumbent)
            for iteration in range(CONFIG['rounds']):
                prior=await s.read('researcher',prior_id);failures=dict(Counter(x['failure'] for x in incumbent))
                focus=await s.decide('researcher','Choose the next uninvestigated mechanism for this failure pattern.',{'prior':prior,'failures':failures},list(queries),[prior_id])
                evidence=await s.search(queries.pop(focus));eid=await s.write('researcher',{'kind':'hypothesis','focus':focus,'failure_counts':failures,'evidence':evidence,'limits':'Sources motivate bounded choices, not guaranteed improvement.'})
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
        report.update(status='completed',remote_rollouts=count,services=s.report(),seconds=time.perf_counter()-start,completed_at=now(),claims='Expanded service use on a registered fresh-seed study; no causal search/memory benefit inferred.')
        assert count==CONFIG['maximum_total_simulations']
        write(out/'report.json',report);return report
    finally:
        if 'evaluation' not in report:write(out/'incomplete.json',{'status':'incomplete','run_id':s.run_id,'rounds_completed':len(report['rounds']),'rollouts':count,'services':s.report()})
        await s.http.aclose()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',default='mochi/artifacts/robustness-v2');a=p.parse_args()
    with modal.enable_output():r=asyncio.run(run(a.out))
    print('MOCHI_ROBUSTNESS_COMPLETE:'+json.dumps({'run_id':r['run_id'],'rollouts':r['remote_rollouts'],'model':r['model'],'evaluation':{k:{n:v for n,v in x.items() if n!='paired_results'} for k,x in r['evaluation'].items()}}),flush=True)
