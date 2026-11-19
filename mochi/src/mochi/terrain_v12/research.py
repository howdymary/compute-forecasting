"""Observed transfer failure → Exa → shared proposal → matched physical test.

Tinker supplies one research inference decision here. Actual post-training is
separate and remains gated by the full continuous physical reference.
"""
import asyncio,json,os,time
import modal
from ..curriculum.world import ROOT
from ..desk.services import DeskServices
from ..integrations import digest,now
from .remote import app,traversal,runtime_check

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
        await add('modal_cpu_hours',15/3600)
        async with app.run():report['runtime_check']=await runtime_check.remote.aio()
        await add('modal_cpu_hours',(report['runtime_check']['duration_seconds']*.25-15)/3600)
        await s.setup()
        rid=await write('experimenter',{'kind':'observation','experiment_ids':['contact-descent-height10-0','contact-bounded-descent6-0'],
            'ascent_verified':True,'complete_descent':False,'engineering_seed':41000,
            'failure':'Legacy backward IK drove the hip reference toward 2.77 rad after an ankle-limit conflict. Bounded backward IK and flight-pitch relaxation passed the first drop, then lost balance on the next. These are engineering tests, not trained checkpoint results.',
            'kinematic_reference':'artifacts/terrain-v12/kinematic-support-comparison.json','training_gate':'closed'})
        observed=await read('researcher',rid);await add('exa_searches',1)
        sources=await s.search('humanoid backward stair descent ankle joint limits inverse kinematics posture regularization swing foot pitch toe clearance')
        hid=await write('researcher',{'kind':'hypothesis','observation_record':rid,'sources':sources,
            'mechanism':'Keep normal stance-leg height during single support; lower during supported transfer. Use a bounded posture-continuous backward IK search and allow sagittal foot pitch in flight, returning to a level landing.'})
        idea=await read('designer',hid);await add('inference_tokens',4000)
        options={'lower_clearance':.004,'more_clearance':.006}
        choice=await s.decide('designer','Choose extra descent swing clearance for a matched backward-IK diagnostic. 4 mm reduces knee flexion; 6 mm adds riser clearance. Both remain subject to the same physical verifier. Compare bounded posture-continuous IK with the legacy IK search. No weights are updated.',{'failure':observed,'research':idea,'choices':options},list(options),[rid,hid])
        pid=await write('designer',{'kind':'proposal','source_record':hid,'descent_lift_m':options[choice],
            'width_m':.024,'matched_difference':'bounded backward IK with flight-pitch allowance','tinker_operation':'research inference, zero optimizer updates'})
        proposal=await read('experimenter',pid);report['proposal']=proposal;report['phase']='Matched book traversal on Modal';await publish()
        await add('modal_rollouts',2);await add('modal_cpu_hours',1800/3600)
        parameters={'width':proposal['width_m'],'descent_lift':proposal['descent_lift_m'],'balance_feedback':.5}
        async with app.run():
            async for row in traversal.starmap.aio([(41000,{**parameters,'bounded_backward':False},'legacy-backward-ik'),(41000,{**parameters,'bounded_backward':True},'bounded-backward-ik')],order_outputs=False):
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
