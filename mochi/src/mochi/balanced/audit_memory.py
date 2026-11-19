"""Supersede the invalid reference through real, source-verified shared memory."""
import asyncio,hashlib,json,uuid
from pathlib import Path
import modal
from ..desk.services import DeskServices

ROOT=Path(__file__).resolve().parents[3]

async def main():
    status=modal.Dict.from_name('mochi-balanced-v11-progress');report=await status.get.aio('latest')
    audit=json.loads((ROOT/'evidence/balance-v11/reference-audit.json').read_text())
    fingerprint=hashlib.sha256(json.dumps(audit,sort_keys=True).encode()).hexdigest()
    if report.get('audit_memory',{}).get('audit_sha256')==fingerprint:
        print('Audit correction already verified in memory');return
    assert report.get('optimizer_updates_completed',0)==0
    budget=modal.Dict.from_name('mochi-balanced-v11-budget');usage=await budget.get.aio('usage')
    assert usage['past_writes']+3<=20 and usage['past_recalls']+3<=40
    usage['past_writes']+=3;usage['past_recalls']+=3;await budget.put.aio('usage',usage)
    old=report['services'];s=DeskServices();s.run_id='mochi-audit-'+uuid.uuid4().hex[:8]
    s.actors=old['actors'];s.audience=old['audiences']['shared'];s.private=old['audiences']['critic_private']
    s.records={r['id']:r for r in old['records']};s.reads=list(old['reads']);s.calls=list(old['calls'])
    s.decisions=list(old['decisions']);s.sources=list(old['sources'])
    try:
        superseded=[r['id'] for r in old['records']]
        eid=await s.write('experimenter',{'kind':'observation','audit_sha256':fingerprint,'audit':audit,
                'supersedes':superseded,'optimizer_updates_completed':0})
        seen=await s.read('critic',eid)
        vid=await s.write('critic',{'kind':'qualified-conclusion','evidence_record':eid,
                'audit_sha256':seen['audit_sha256'],'verdict':'Reject the clock-assisted reference. Training gate remains closed.',
                'supersedes':superseded,'next_experiment':'strict-lower-speed-and-gait-continuity-four-probe'})
        recalled=await s.read('researcher',vid)
        canary=await s.write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},private=True)
        await s.read('designer',canary,False)
        report['services']=s.report();report['audit_memory']={'audit_sha256':fingerprint,'evidence_record':eid,
            'verdict_record':vid,'next_experiment':recalled['next_experiment'],'source_verified_cross_role_handoffs':2}
        report.update(status='invalid_reference',phase='Reference rejected; corrected verdict recalled through past.dev',training_gate_open=False)
        report['budget_usage_or_reserved']=usage;await status.put.aio('latest',report)
        out=ROOT/'artifacts/balance-v11-audit-memory';out.mkdir(parents=True,exist_ok=True)
        (out/'report.json').write_text(json.dumps({'audit_memory':report['audit_memory'],'services':s.report(),'budget_usage_or_reserved':usage},indent=2))
        print('Verified audit supersession, two cross-role handoffs and private audience isolation')
    finally:
        await s.http.aclose()

if __name__=='__main__':asyncio.run(main())
