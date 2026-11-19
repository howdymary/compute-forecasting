"""Failure → memory → Exa → bounded model proposal → Modal → qualified verdict.

This pre-training probe never opens the Tinker training gate or held-out set.
"""
import asyncio,json,os,uuid
from pathlib import Path
from ..desk.services import DeskServices
from ..integrations import now,digest
from .world import ROOT
from .remote import app,probe

OUT=ROOT/'artifacts/richdesk-v10-remote'

def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')


async def main():
    cfg=json.loads((ROOT/'configs/richdesk-campaign.json').read_text())
    assert not cfg['training_gate']['open'],'Use the separate frozen training campaign after feasibility'
    services=DeskServices();services.run_id='mochi-r10-'+uuid.uuid4().hex[:8]
    services.actors={r:services.run_id+'-'+r for r in ['researcher','designer','experimenter','critic']}
    services.audience=services.run_id+'-shared';services.private=services.run_id+'-critic'
    report={'study':cfg['study'],'phase':'pretraining-feasibility','created_at':now(),
        'workflow_run':os.getenv('GITHUB_RUN_ID'),'source_sha':os.getenv('GITHUB_SHA'),
        'optimizer_updates_completed':0,'scope':'Engineering failure-directed probes, not a model-training gain.',
        'bounds':{'modal_rollouts':3,'exa_searches':1,'past_writes':5,'past_recalls':5,'tinker_optimizer_updates':0}}
    try:
        await services.setup()
        observation={'kind':'observation','study':cfg['study'],'scene_sha256':digest(json.loads((ROOT/'configs/richdesk-v9.json').read_text())),
          'measured_failure':'Native controller stalls or falls near book risers. A contact-constrained prototype establishes support and takes steps, but touchdown or the following weight transfer remains unreliable.',
          'training_gate':'closed','held_out_opened':False}
        rid=await services.write('experimenter',observation);seen=await services.read('researcher',rid)
        sources=await services.search('humanoid robot stair climbing inverse dynamics support transfer touchdown contact foot trajectory center of pressure')
        hid=await services.write('researcher',{'kind':'hypothesis','study':cfg['study'],'observation_record':rid,'sources':sources,
           'mechanism':'Longer support transfer and bounded swing motion may reduce contact transitions that destabilize a small biped. This is a hypothesis, not a measured improvement.'})
        idea=await services.read('designer',hid)
        options={'slow_transfer':{'shift_seconds':1.6,'stride':.022,'crouch':.012,'swing_seconds':.52},
                 'slow_swing':{'shift_seconds':1.6,'stride':.022,'crouch':.012,'swing_seconds':.9}}
        action=await services.decide('designer','Choose one bounded controller experiment using the failure and retrieved mechanism. Neither candidate is trained. Both will be compared with the native controller on one engineering seed.',
           {'evidence':seen,'research':idea,'candidates':options},list(options),[rid,hid])
        pid=await services.write('designer',{'kind':'proposal','study':cfg['study'],'source_record':hid,'selected':action,'parameters':options[action]})
        proposal=await services.read('experimenter',pid)
        async with app.run():
            baseline=await probe.remote.aio(31000,{},'native',12.)
            params={**proposal['parameters'],'com_tracking':0.,'torso_gain':0.,'angular_damping':0.}
            candidate=await probe.remote.aio(31000,params,'wholebody',12.)
        save('native',baseline);save('candidate',candidate)
        summary=lambda r:{'fall':r['episode']['fall'],'seconds':r['episode']['duration'],
            'steps':r['controller'].get('steps'),'book_top':r['book_top'],
            'metrics':r['episode']['locomotion_metrics'],'receipt':r['receipt']}
        results={'kind':'observation','study':cfg['study'],'proposal_record':pid,'baseline':summary(baseline),'candidate':summary(candidate)}
        eid=await services.write('experimenter',results);recalled=await services.read('critic',eid)
        verdict={'kind':'qualified-conclusion','study':cfg['study'],'evidence_record':eid,
          'book_ascent_established':False,'training_gate':'closed',
          'conclusion':'A short engineering probe cannot certify the complete book ascent, descent or four-task sequence. Do not start training or label this a learned improvement.',
          'evidence_sha256':digest(recalled),'supersedes_hypothesis':hid}
        vid=await services.write('critic',verdict);await services.read('researcher',vid)
        report.update(status='completed',proposal=proposal,results=results,verdict=verdict,
          physical_rollouts=2,services=services.report())
    except Exception as e:
        report.update(status='failed',error_type=type(e).__name__,services=services.report());raise
    finally:
        save('report',report);await services.http.aclose()


if __name__=='__main__':asyncio.run(main())
