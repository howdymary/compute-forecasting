"""Live sponsored research: failure -> Exa -> bounded model choices -> Modal -> memory."""
import asyncio,json,os,time
from dataclasses import asdict,replace
from pathlib import Path
from collections import Counter
from .simulation import Policy,PROTOCOL,PROTOCOL_SHA,summarize,rollout
from .campaign import write,candidates,rank
from .integrations import Services,digest,now

async def run(out):
    from .remote import app,batch
    start=time.perf_counter();out=Path(out);out.mkdir(parents=True,exist_ok=True);s=Services();await s.setup()
    report={'run_id':s.run_id,'mode':'live-sponsored-research','created_at':now(),'protocol_sha256':PROTOCOL_SHA,'rounds':[],'services':{'exa':'pending','past':'pending','modal':'pending','model':'pending'}}
    try:
        private=await s.write('critic',{'kind':'synthetic-canary','value':'MOCHI_PRIVATE_CANARY'},private=True)
        await s.read('critic',private);await s.read('researcher',private,allowed=False)
        prior_id=await s.write('critic',{'kind':'rule','rule':'Use development scenarios only for selection. Hypotheses need physical tests; search excerpts are not proof. Report failed ideas.'})
        dev=PROTOCOL['development_seeds'];selected=Policy();all_rows=[];receipt_count=0
        with app.run():
            initial=batch(asdict(selected),dev);receipt_count+=len(initial)
            prior_results=initial
            for round_id in range(2):
                prior=await s.read('researcher',prior_id)
                failures=dict(Counter(x['failure'] for x in prior_results))
                focus=await s.decide('researcher','Which mechanism should this failure-driven search investigate?',{'failures':failures,'prior':prior},['contact_feedback','push_velocity','termination_dwell'],[prior_id])
                queries={'contact_feedback':'robot planar pushing closed loop feedback object pose contact uncertainty friction control paper','push_velocity':'robot planar pushing velocity friction overshoot quasi static manipulation controller','termination_dwell':'robot manipulation pushing closed loop stopping criteria target velocity settling'}
                evidence=await s.search(queries[focus])
                evidence_id=await s.write('researcher',{'kind':'hypothesis','focus':focus,'failure_counts':failures,'evidence':evidence,'caveat':'Retrieved mechanisms motivate experiments; they do not establish performance.'})
                consumed=await s.read('designer',evidence_id)
                design=await s.decide('designer','Choose a registered policy family to test in response to the sourced mechanism.',consumed,['slow_open_loop','object_feedback','earlier_stop'],[evidence_id])
                proposed=candidates(seed=70+round_id,n=3,feedback=design=='object_feedback')
                if design=='slow_open_loop':proposed=[replace(p,speed=p.speed*.3+.025) for p in proposed]
                if design=='earlier_stop':proposed=[replace(p,stop_distance=.022) for p in proposed]
                proposal_id=await s.write('designer',{'kind':'proposal','family':design,'predicted_effect':{'slow_open_loop':'Less impulsive pushing may improve control but can stall.','object_feedback':'Object-pose feedback may recover contact under varying friction.','earlier_stop':'A larger stopping margin may reduce overshoot but undershoot.'}[design],'policies':[asdict(p) for p in proposed],'source_record':evidence_id})
                plan=await s.read('experimenter',proposal_id)
                diagnostic=await s.decide('experimenter','Choose the failure diagnostic to emphasize; every registered metric will still be measured.',plan,['contact_loss','distance_and_dwell','effort_and_overshoot'],[proposal_id])
                rows=[]
                for p in proposed:
                    results=batch(asdict(p),dev);receipt_count+=len(results)
                    rows.append({'policy':asdict(p),'summary':summarize(results),'results':results,'round':round_id,'source_record':evidence_id})
                all_rows+=rows;best=max(rows,key=rank)
                experiment_id=await s.write('experimenter',{'kind':'observation','diagnostic':diagnostic,'candidates':[{'policy':r['policy'],'summary':r['summary']} for r in rows],'incumbent':summarize(prior_results),'selected_candidate':best['policy']})
                review=await s.read('critic',experiment_id);evidence_read=await s.read('critic',evidence_id)
                verdict=await s.decide('critic','Recommend accepting or rejecting the challenger. A deterministic development gate will also require improvement.',{'experiment':review,'evidence':evidence_read},['accept_with_limits','reject'],[experiment_id,evidence_id])
                gate=rank(best)>rank({'summary':summarize(prior_results)})
                accepted=gate and verdict=='accept_with_limits'
                if accepted:selected=Policy(**best['policy']);prior_results=best['results']
                prior_id=await s.write('critic',{'kind':'conclusion','model_verdict':verdict,'deterministic_gate':gate,'accepted':accepted,'candidate':best['policy'],'summary':best['summary'],'limitation':'Development only; no claim of universal or held-out improvement.','next_question':'Investigate residual failure modes without changing the verifier.'})
                report['rounds'].append({'round':round_id,'focus':focus,'design':design,'candidates':rows,'accepted':accepted,'model_verdict':verdict,'deterministic_gate':gate,'evidence_record':evidence_id,'critic_record':prior_id})
            # Researcher actually consumes the last critic conclusion.
            final_context=await s.read('researcher',prior_id)
            report['next_research_question']=await s.decide('researcher','What should a future run study?',final_context,['contact_feedback','push_velocity','termination_dwell'],[prior_id])
            report['selected']=asdict(selected);report['selected_sha256']=digest(asdict(selected));report['frozen_at']=now()
            # Equal 6-candidate x 8-seed control; no Exa or memory in this arm.
            random_rows=[]
            for p in candidates(seed=42,n=6):
                rs=batch(asdict(p),dev);receipt_count+=len(rs);random_rows.append({'policy':asdict(p),'summary':summarize(rs),'results':rs})
            control=max(random_rows,key=rank);report['random_control']={'candidates':random_rows,'selected':control['policy'],'budget_rollouts':48}
            report['research_budget_rollouts']=48
            sections={}
            for scope,seeds,shift in [('development',dev,False),('heldout',PROTOCOL['heldout_seeds'],False),('changed_conditions',PROTOCOL['shift_seeds'],True)]:
                section={};paired={}
                for label,policy in [('baseline',asdict(Policy())),('selected',asdict(selected)),('random',control['policy'])]:
                    rs=batch(policy,seeds,shift);receipt_count+=len(rs);section[label]=summarize(rs);paired[label]=rs
                section['paired_results']=paired;sections[scope]=section
            report['evaluation']=sections;report['remote_rollouts']=receipt_count
        report['memory']=s.report();report['sources']=s.sources
        assert report['memory']['eligibility']['writers']>1 and report['memory']['eligibility']['readers']>1 and report['memory']['eligibility']['isolation_passed']
        report['services']={k:'executed with receipts' for k in report['services']}
        rs=sections['development']['paired_results'];demo=next((a['scenario']['seed'] for a,b in zip(rs['baseline'],rs['selected']) if not a['success'] and b['success']),dev[0])
        report['demo_seed']=demo;report['demo_scope']='Development illustration; selected to show improvement if available. Full matched held-out results are separate.'
        report['claims']='Parameterized, state-based arm controller search; bounded model-driven research. No new neural policy weights. Equal simulation budgets; research has additional retrieval and model cost.'
        for name,p,seed in [('baseline',Policy(),demo),('selected',selected,demo),('heldout',selected,PROTOCOL['heldout_seeds'][0])]:write(out/(name+'.json'),rollout(p,seed,record=True))
        report['seconds']=time.perf_counter()-start;write(out/'report.json',report);return report
    finally:
        await s.http.aclose()
        if 'evaluation' not in report:write(out/'incomplete.json',{'run_id':s.run_id,'status':'incomplete','memory':s.report(),'rounds':report['rounds']})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',default='mochi/artifacts/live');a=p.parse_args()
    report=asyncio.run(run(a.out));print(json.dumps({'run_id':report['run_id'],'services':report['services'],'rollouts':report['remote_rollouts'],'heldout':{k:v for k,v in report['evaluation']['heldout'].items() if k!='paired_results'}}))
