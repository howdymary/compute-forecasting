"""Measured failure → shared memory → Exa → bounded proposal → real physics.

The complete-sequence gate is closed. This code cannot create a Tinker trainer.
Its single model decision is inference and is reported separately from updates.
"""
import asyncio,json,os,uuid
from ..curriculum.world import ROOT
from ..desk.services import DeskServices
from ..integrations import now,digest
from .remote import app,reference

OUT=ROOT/'artifacts/balance-v11-remote'

def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

async def main():
    cfg=json.loads((ROOT/'configs/balance-v11.json').read_text())
    assert not cfg['training_gate_open'],'Use the separately frozen training entry point'
    services=DeskServices();services.run_id='mochi-b11-'+uuid.uuid4().hex[:8]
    services.actors={r:services.run_id+'-'+r for r in ['researcher','designer','experimenter','critic']}
    services.audience=services.run_id+'-shared';services.private=services.run_id+'-critic'
    report={'study':cfg['study'],'phase':'physical-reference-research','created_at':now(),
            'workflow_run':os.getenv('GITHUB_RUN_ID'),'source_sha':os.getenv('GITHUB_SHA'),
            'optimizer_updates_completed':0,'held_out_opened':False,
            'bounds':{'modal_rollouts':2,'cpu_hours':.1,'exa_searches':1,'past_writes':5,'past_recalls':5,'tinker_decisions':1,'optimizer_updates':0}}
    try:
        await services.setup()
        rid=await services.write('experimenter',{'kind':'observation','study':cfg['study'],
            'experiment_id':'reference-capture-1','ascent_and_alarm_passed':True,
            'failure':'Backward descent produced 1.816 N of unintended contact between the left ankle pitch link and the top book at 12.158 simulated seconds.',
            'training_gate':'closed','scope':'One engineering seed; no repeatability or training benefit established.'})
        failure=await services.read('researcher',rid)
        sources=await services.search('humanoid stair descent backward forward walking capture point support polygon touchdown transition pretrained locomotion policy')
        hid=await services.write('researcher',{'kind':'hypothesis','observation_record':rid,'sources':sources,
            'mechanism':'Forward-facing descent may clear the riser differently from backward stepping. Capturing a supported stop with a measured capture-point margin may reduce unstable support transitions.',
            'qualification':'A simplified capture point is a screening heuristic, not a full stability certificate.'})
        evidence=await services.read('designer',hid)
        options={'standard_margin':.001,'conservative_margin':.002}
        choice=await services.decide('designer','Choose the measured capture-point margin for one forward-descent trial. Both margins are in metres and use actual contact forces and COM velocity. The matched reference uses backward descent. No Tinker weights are being updated.',
            {'failure':failure,'hypothesis':evidence,'options':options},list(options),[rid,hid])
        pid=await services.write('designer',{'kind':'proposal','hypothesis_record':hid,
            'capture_margin_m':options[choice],'forward_descent':True,'tinker_operation':'inference only'})
        proposal=await services.read('experimenter',pid)
        base={'alarm_x':-.365,'alarm_y':.045,'capture_margin':.001}
        async with app.run():
            rows=[r async for r in reference.map.aio([base,{**base,'capture_margin':proposal['capture_margin_m'],'forward_descent':True,'descent_speed':.03}],order_outputs=True)]
        for label,row in zip(['reference','proposal'],rows):save(label,row)
        summaries=[{'failure':r['failure'],'complete_sequence_success':r['complete_sequence_success'],
                    'duration_s':r['episode']['duration'],'tasks':{k:v['success'] for k,v in r['episode']['results'].items()},
                    'arrivals':r['arrivals'],'receipt':r['receipt']} for r in rows]
        eid=await services.write('experimenter',{'kind':'observation','proposal_record':pid,'matched_results':summaries})
        checked=await services.read('critic',eid)
        passed=all(r['complete_sequence_success'] for r in rows)
        vid=await services.write('critic',{'kind':'qualified-conclusion','evidence_record':eid,
            'evidence_sha256':digest(checked),'repeatability_established':False,
            'all_probe_sequences_passed':passed,'training_gate':'closed pending repeated safe reference',
            'supersedes_hypothesis':hid,'optimizer_updates_completed':0})
        await services.read('researcher',vid)
        report.update(status='completed',physical_rollouts=2,proposal=proposal,results=summaries)
    except Exception as exc:
        report.update(status='failed',error_type=type(exc).__name__)
        raise
    finally:
        report['services']=services.report();save('report',report);await services.http.aclose()

if __name__=='__main__':
    asyncio.run(main())
