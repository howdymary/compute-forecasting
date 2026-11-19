"""Observed transfer failure → Exa → shared proposal → matched physical test.

Tinker supplies one research inference decision here. Actual post-training is
separate and remains gated by the full continuous physical reference.
"""
import asyncio,json,os,time
import modal
from ..curriculum.world import ROOT
from ..desk.services import DeskServices
from ..integrations import digest,now
from .remote import app,traversal

OUT=ROOT/'artifacts/terrain-v12-research'

def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

async def main():
    cfg=json.loads((ROOT/'configs/terrain-v12.json').read_text());assert not cfg['training_gate_open']
    run_id='mochi-t12-'+os.environ['GITHUB_RUN_ID'];s=DeskServices();s.run_id=run_id
    s.actors={r:run_id+'-'+r for r in ['researcher','designer','experimenter','critic']}
    s.audience=run_id+'-shared';s.private=run_id+'-critic'
    store=modal.Dict.from_name('mochi-terrain-v12-budget',create_if_missing=True)
    usage=await store.get.aio('usage') or {k:0 for k in cfg['bounds'] if k not in ['modal_concurrency','local_rollouts']}
    status=modal.Dict.from_name('mochi-terrain-v12-progress',create_if_missing=True)
    report={'study':cfg['study'],'workflow_run':os.environ['GITHUB_RUN_ID'],'source_sha':os.environ['GITHUB_SHA'],
        'run_id':run_id,'status':'running','phase':'Failure research and controller diagnostic','created_at':now(),
        'optimizer_updates_completed':0,'held_out_opened':False,'results':[]}
    async def add(kind,n):
        value=usage.get(kind,0)+n
        if not 0<=value<=cfg['bounds'][kind]:raise RuntimeError('V12 budget ceiling: '+kind)
        usage[kind]=value;await store.put.aio('usage',usage)
    async def publish():
        report['budget_usage_or_reserved']=usage;report['services']=s.report();save('progress',report);await status.put.aio('latest',report)
    async def write(role,content,private=False):
        await add('past_writes',1);return await s.write(role,content,private)
    async def read(role,rid,allowed=True):
        await add('past_recalls',1);return await s.read(role,rid,allowed)
    try:
        await s.setup()
        rid=await write('experimenter',{'kind':'observation','experiment_ids':['contact-preload-wide-0','contact-preload-narrow-0'],
            'wide_stance_steps':9,'narrow_stance_steps':15,'complete_ascent':False,
            'failure':'Loss of support during a mixed-height transfer or trailing-foot swing. Fixed low pelvis height, changing swing-leg mass and arm dynamics are hypotheses, not established causes.',
            'kinematic_reference':'artifacts/terrain-v12/kinematic-support-comparison.json','training_gate':'closed'})
        observed=await read('researcher',rid);await add('exa_searches',1)
        sources=await s.search('humanoid stair ascent trailing leg swing pelvis height contact inverse dynamics center of mass arm coupling full sole landing')
        hid=await write('researcher',{'kind':'hypothesis','observation_record':rid,'sources':sources,
            'mechanism':'Retain low pelvis height while the lower foot is planted, then extend the stance leg after unloading; account for swing-leg COM and prescribed arm servo efforts in inverse dynamics.'})
        idea=await read('designer',hid);await add('inference_tokens',4000)
        options={'closer_station':.015,'longer_approach':.020}
        choice=await s.decide('designer','Choose the final book-top foot-centre y coordinate for a matched arm-dynamics diagnostic. .015 m shortens the step; .020 m improves later alarm reach. Both remain subject to the same physical verifier. The test compares coupled arm dynamics with the earlier fixed-arm-acceleration approximation. No weights are updated.',{'failure':observed,'research':idea,'choices':options},list(options),[rid,hid])
        pid=await write('designer',{'kind':'proposal','source_record':hid,'book_goal_m':options[choice],
            'width_m':.024,'matched_difference':'arm acceleration model','tinker_operation':'research inference, zero optimizer updates'})
        proposal=await read('experimenter',pid);report['proposal']=proposal;report['phase']='Matched book traversal on Modal';await publish()
        await add('modal_rollouts',2);await add('modal_cpu_hours',1800/3600)
        parameters={'width':proposal['width_m'],'book_goal':proposal['book_goal_m']}
        async with app.run():
            async for row in traversal.starmap.aio([(41000,{**parameters,'arm_model':False},'prior-arm-approximation'),(41000,{**parameters,'arm_model':True},'coupled-arm-dynamics')],order_outputs=False):
                save(row['variant'],row)
                report['results'].append({'variant':row['variant'],'failure':row['failure'],'ascent':row['book_ascent_verified'],
                    'descent':row['book_descent_verified'],'duration_s':row['episode']['duration'],
                    'contact_failures':row['episode']['contact_failures'],'metrics':row['episode']['balance_metrics'],'receipt':row['receipt']})
                await publish()
        await add('modal_cpu_hours',sum(r['receipt']['duration_seconds'] for r in report['results'])/3600-.5)
        eid=await write('experimenter',{'kind':'observation','proposal_record':pid,'matched_results':report['results']})
        checked=await read('critic',eid)
        vid=await write('critic',{'kind':'qualified-conclusion','evidence_record':eid,'evidence_sha256':digest(checked),
            'measured_results':report['results'],'training_gate':'Closed until repeated unassisted traversal and a complete fixture-safe four-task reference pass.','optimizer_updates_completed':0})
        await read('researcher',vid)
        canary=await write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},True);await read('designer',canary,False)
        report.update(status='completed',phase='Controller diagnostic reviewed; full-sequence training gate remains closed',completed_at=now())
        save('report',report);await publish()
    except Exception as exc:
        report.update(status='incomplete',error_type=type(exc).__name__);await publish();raise
    finally:await s.http.aclose()

if __name__=='__main__':
    with modal.enable_output():asyncio.run(main())
