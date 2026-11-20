"""Finish a saved V17 memory handoff without training or simulation.

The original 72k-character result document exceeded its requested recall
budget. Exact numerical evidence stays in the artifact; memory gets a compact,
hash-linked summary. Reads still require the returned source ID and real ACLs.
"""
import argparse
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

from ..integrations import digest,now
from ..desk.services import DeskServices

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'artifacts/smooth-v17-finalized'
RESULT_FIELDS=['protocol','protocol_sha256','source_sha','base_source_sha',
    'execution_source_sha','checkpoints','selected_checkpoint','training_log',
    'optimizer_updates_completed','held_out','paired_held_out',
    'improvement_goal_met','physics_receipts','component_results',
    'total_physical_attempts_accounted','total_physical_rollouts_completed',
    'campaign_modal_rollouts_completed','first_optimizer_physical_probe',
    'data_collection_provenance','first_optimizer_behavioral_probe']


def result_digest(report):
    return digest({k:report[k] for k in RESULT_FIELDS})


def compact_result(report,record,source):
    full=record['payload']['content']
    failures=[]
    case_path=source/'held-out-selected.json'
    for row in json.loads(case_path.read_text()):
        e=row['episode'];seen=set();contacts=[]
        for contact in e.get('contact_failures',[]):
            key=(contact.get('body'),contact.get('fixture'))
            if key not in seen:
                seen.add(key);contacts.append({k:contact.get(k) for k in ['body','fixture','phase','force_n']})
        failures.append({'seed':row['seed'],'failure':row['failure'],
            'verified_tasks':[task for task,r in e['results'].items() if r['success']],
            'last_station':row['arrivals'][-1]['label'] if row['arrivals'] else None,
            'last_decision_domain':row['model_decisions'][-1]['observation']['domain'],
            'contact_examples':contacts})
    assert len(failures)==4 and all(x['last_decision_domain']=='laptop' for x in failures)
    result={'kind':'compact-observation','experiment_id':report['run_id'],
        'optimizer_updates_completed':report['optimizer_updates_completed'],
        'selected_update':report['selected_checkpoint']['update'],
        'held_out':full['held_out'],'paired_step_results':full['paired_step_results'],
        'improvement_goal_met':full['improvement_goal_met'],
        'failure_localization':failures,
        'failure_source_file':'held-out-selected.json',
        'failure_source_sha256':hashlib.sha256(case_path.read_bytes()).hexdigest(),
        'component_outcomes':[{k:row.get(k) for k in
            ['task','domain','model','success','fall','invalid_contact']}
            for batch in full['components'] for row in batch['results']],
        'full_record_id':record['id'],'full_record_sha256':record['sha256'],
        'full_content_sha256':digest(full),'frozen_result_sha256':result_digest(report),
        'artifact':'mochi-smooth-v17-training-44699655265',
        'artifact_workflow_run':44699655265,
        'supersedes':record['id'],
        'qualification':'Compact representation of existing measured results. No new optimizer update or physical experiment. Exact observations and trajectories remain in the source artifact and Modal archives.'}
    assert len(json.dumps(result,sort_keys=True))<12000,'Keep this below the smallest documented evidence ceiling'
    return result


def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/(name+'.json');temporary=target.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(target)


class ReviewServices(DeskServices):
    """Reuse authenticated clients without importing a robot world or assets."""
    def __init__(self):
        super().__init__();self.pending={}

    def journal(self):
        save(self.run_id+'-memory-journal',{'pending':self.pending,'ready':self.records})

    async def write(self,role,content,private=False):
        # The existing journal-before-poll pattern, independent of world.ROOT.
        rid=self.run_id+'-r'+str(len(self.records)+len(self.pending));at=now();started=time.perf_counter()
        value={'record_id':rid,'author':self.actors[role],'occurred_at':at,'content':content}
        text=f'Mochi desk {role} record {rid}. Canonical SHA256 {digest(value)}. '+json.dumps(content,sort_keys=True)
        reply=await self.request('POST','/ingest',{'id':rid,'identity':self.actors[role],
            'audience':self.private if private else self.audience,'timestamp':at,
            'label':f'Mochi desk {content.get("kind","finding")}','content':text})
        record={'id':rid,'role':role,'author':self.actors[role],
            'audience':self.private if private else self.audience,'at':at,
            'sha256':digest(value),'ingestion_id':reply['ingestionId'],'payload':value,'status':'pending'}
        self.pending[rid]=record;self.journal()
        while time.perf_counter()-started<900:
            status=await self.request('GET','/ingest/'+record['ingestion_id'])
            record['status']=status.get('status','unknown')
            if record['status']=='completed':
                record['write_to_ready_seconds']=time.perf_counter()-started
                self.records[rid]=self.pending.pop(rid);self.journal();return rid
            self.journal()
            if record['status']=='failed':raise RuntimeError('Memory ingestion failed; journal preserved')
            await asyncio.sleep(5)
        raise TimeoutError('Memory ingestion pending; journal preserved')

    def report(self):
        return {**super().report(),'pending_ingestions':[
            {k:v for k,v in r.items() if k!='payload'} for r in self.pending.values()]}

    async def read(self,role,rid,allowed=True):
        wanted=self.records[rid];found=False;reply={};attempts=[]
        for attempt in range(5 if allowed else 1):
            # Occurrence windows are event-time filters, not source-ID lookup.
            # Keep identity/audience controls and verify the exact returned ID.
            reply=await self.request('POST','/recall',{
                'identity':self.actors[role],
                'query':f'Mochi experiment {self.run_id}. Retrieve exact source record {rid}, {wanted["payload"]["content"].get("kind","")}, written by {wanted["role"]}.',
                'maxTokens':8000,'limit':200})
            ids={s.get('sourceId') for row in reply.get('results',[]) for s in row.get('sources',[])}
            found=rid in ids
            attempts.append({'at':now(),'returned_documents':len(reply.get('results',[])),
                'used_evidence_tokens':reply.get('usedEvidenceTokens'),
                'required_source_verified':found,'returned_source_ids':sorted(x for x in ids if x)})
            if found or not allowed:break
            await asyncio.sleep(2+attempt)
        if not allowed and (found or 'MOCHI_PRIVATE_CANARY' in json.dumps(reply)):
            raise RuntimeError('Private-audience canary was visible to an unauthorized reader')
        self.reads.append({'reader':self.actors[role],'reader_role':role,'author':wanted['author'],
            'record_id':rid,'source_id_verified':found,'expected_access':allowed,
            'cross_agent_use':found and self.actors[role]!=wanted['author'],
            'sha256':wanted['sha256'] if found else None,'at':now(),
            'retrieval':'source-verified compact evidence, 8000-token budget, no occurrence window',
            'attempts':attempts})
        if allowed and not found:
            raise RuntimeError('Required compact source absent; no canonical fallback')
        return wanted['payload']['content'] if found else {'access':'denied-as-expected'}


def load(source):
    report=json.loads((source/'progress.json').read_text())
    assert report['study']=='mochi-smooth-v17' and report['run_id']=='mochi-t17-44699655265'
    assert report['status']=='incomplete' and report['error']=='Required memory source absent; no silent fallback'
    assert report['optimizer_updates_completed']==16 and len(report['training_log'])==16
    assert all(x['optimizer_completed'] and x['forward_backward_completed'] for x in report['training_log'])
    assert sum(len(x['domain_loss_metrics']) for x in report['training_log'])==96
    assert all(x['n']==4 for x in report['held_out'].values())
    assert len(report['component_results'])==8
    assert sum(len(x['results']) for x in report['component_results'])==24
    journal=json.loads((source/(report['run_id']+'-memory-journal.json')).read_text())
    assert not journal['pending']
    record=journal['ready'][report['run_id']+'-r3']
    assert record['status']=='completed' and digest(record['payload'])==record['sha256']
    assert record['payload']['content']['held_out']==report['held_out']
    return report,journal,record


async def finish(source):
    import modal
    original,journal,large_record=load(source)
    report=copy.deepcopy(original);frozen=result_digest(report)
    for path in source.glob('*.json'):
        OUT.mkdir(parents=True,exist_ok=True);shutil.copy2(path,OUT/path.name)
    save('original-memory-interruption',original)
    ledger=modal.Dict.from_name('mochi-t16r1-44686221838-budget')
    usage=await ledger.get.aio('usage')
    assert usage==original['budget_usage_or_reserved'],'Reconcile the current ledger before any retry'
    initial_usage=dict(usage);bounds=report['protocol']['bounds']
    claim_key='v17-memory-only-finalization'
    assert await ledger.get.aio(claim_key) is None,'Existing finalization: inspect its journal before resuming'
    await ledger.put.aio(claim_key,{'workflow_run':os.environ['GITHUB_RUN_ID'],'status':'started','result_sha256':frozen})
    progress=modal.Dict.from_name('mochi-smooth-v17-progress')
    services=ReviewServices();services.run_id=report['run_id']
    services.actors=report['services']['actors']
    services.audience=report['services']['audiences']['shared']
    services.private=report['services']['audiences']['critic_private']
    services.records=journal['ready'];services.pending=journal['pending']
    for name in ['reads','decisions','calls','sources']:
        setattr(services,name,copy.deepcopy(report['services'][name]))
    report['memory_finalization']={
        'workflow_run':os.environ['GITHUB_RUN_ID'],'source_sha':os.environ['GITHUB_SHA'],
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'original_status':original['status'],'original_error':original['error'],
        'original_source_id':large_record['id'],
        'pre_review_validation_failure':{'workflow_run':44734727709,
            'cause':'Inherited adapter imported unavailable robot meshes; no provider calls or budget debits occurred.'},
        'original_content_characters':len(json.dumps(large_record['payload']['content'],sort_keys=True)),
        'requested_original_evidence_tokens':16000,
        'frozen_result_sha256_before':frozen,
        'additional_optimizer_updates':0,'additional_physical_stages':0,
        'documentation':'https://past.dev/docs/memory-api/api-reference#post-api-v1-recall',
        'repair':'Compact semantic summary linked to immutable full evidence; exact-source verification and original audiences retained.'}
    report.update(status='running',phase='Complete memory review of preserved V17 results')
    report.pop('error',None);report.pop('error_type',None)

    async def change(kind,amount):
        assert kind in ['past_writes','past_recalls','inference_tokens','exa_searches']
        value=usage[kind]+amount
        assert 0<=value<=bounds[kind], 'Shared finalization budget exhausted: '+kind
        usage[kind]=value;await ledger.put.aio('usage',dict(usage))

    async def publish():
        assert result_digest(report)==frozen,'Numerical evidence changed during memory review'
        for key in ['physical_rollouts','simulation_cpu_hours','optimizer_updates','training_token_presentations']:
            assert usage[key]==initial_usage[key],'Finalization must not train or simulate'
        report['budget_usage_or_reserved']=dict(usage);report['services']=services.report()
        save('progress',report)
        await progress.put.aio(report['run_id'],report);await progress.put.aio('latest',report)
        print(json.dumps({'phase':report['phase'],'optimizer_updates':16,'additional_physical_stages':0,
            'memory_writes_accounted':usage['past_writes'],'memory_recalls_accounted':usage['past_recalls']}),flush=True)

    async def write(role,value,private=False):
        report['phase']='Memory-only finalization: write '+role+' '+value['kind']
        await change('past_writes',1);await publish()
        rid=await services.write(role,value,private);await publish();return rid

    async def read(role,rid,allowed=True):
        report['phase']='Memory-only finalization: recall '+role
        await change('past_recalls',1);await publish()
        result=await services.read(role,rid,allowed);await publish();return result

    try:
        await services.setup()  # Same fixed memberships and identities, no broader audience.
        await publish()
        packet=compact_result(original,large_record,source)
        rid=await write('experimenter',packet)
        measured=await read('critic',rid)
        assert digest(measured)==digest(packet)
        report['memory_finalization']['compact_record_id']=rid
        report['memory_finalization']['compact_content_characters']=len(json.dumps(packet,sort_keys=True))
        report['memory_finalization']['failure_localization']=packet['failure_localization']
        await change('inference_tokens',4000)
        label=await services.decide('critic',
            'Classify the measured full-route results. Zero qualified pairs has no defined efficiency gain. Changed probabilities alone do not establish better control. Keep the small simulated cohort qualified.',
            {'held_out':measured['held_out'],'paired':measured['paired_step_results'],
             'failure_localization':measured['failure_localization'],
             'goal_met':measured['improvement_goal_met'],'selected_update':measured['selected_update']},
            ['bounded_simulated_gain','no_demonstrated_gain','regression_or_uncertain'],[rid])
        vid=await write('critic',{'kind':'qualified-conclusion','experiment_id':report['run_id'],
            'evidence_record':rid,'evidence_sha256':digest(measured),
            'model_interpretation':label,'interpretation_is_advisory':True,
            'promotion_recommendation':'do_not_promote','goal_met':report['improvement_goal_met'],
            'selected_complete':report['held_out']['selected']['complete_successes'],
            'parent_complete':report['held_out']['parent']['complete_successes'],'n':4,
            'failure_localization':measured['failure_localization'],
            'conclusion':'The 16-update campaign failed its joint target. Update 1 completed zero of four fresh routes; the parent completed one. All four selected attempts completed clock and drawer and reached the laptop, then failed during laptop contact: two falls and two forbidden contacts. Preserve the earlier validated study and investigate laptop stance, force control and fixture clearance before further training. Native gait weights stayed fixed.',
            'supersedes':report['run_id']+'-r1'})
        verdict=await read('researcher',vid)
        await change('inference_tokens',4000)
        focus=await services.decide('researcher',
            'Choose the next research question from the recalled rejection. Do not change the frozen experiment or request more optimizer updates.',
            {'verdict':verdict,'failures':report['held_out']},
            ['laptop_contact_balance','printer_fixture_clearance','on_policy_laptop_states'],[vid])
        queries={
            'laptop_contact_balance':'humanoid laptop lid closing whole body balance manipulation force control support polygon research',
            'printer_fixture_clearance':'humanoid whole body collision avoidance knee clearance constrained manipulation reaching research',
            'on_policy_laptop_states':'robot imitation learning on policy data aggregation contact rich manipulation compounding errors research'}
        await change('exa_searches',1)
        found=await services.search(queries[focus])
        hid=await write('researcher',{'kind':'future-hypothesis','experiment_id':report['run_id'],
            'verdict_record':vid,'focus':focus,'sources':found,
            'qualification':'Candidate research for the next study. No new controller, training update or physical experiment was executed.',
            'supersedes':report['run_id']+'-r1'})
        hypothesis=await read('designer',hid)
        await change('inference_tokens',4000)
        next_step=await services.decide('designer',
            'Choose which prerequisite to investigate next using the recalled sourced hypothesis. All options are future work, not changes to this completed comparison.',
            hypothesis,['stabilize_laptop_contact','verify_fixture_clearance','collect_laptop_contact_states'],[hid])
        report['memory_finalization']['future_research']={'focus':focus,'record_id':hid,
            'designer_next_investigation':next_step,'implemented':False}
        canary=await write('critic',{'kind':'private-test','text':'MOCHI_PRIVATE_CANARY'},True)
        await read('designer',canary,False)
        assert not services.pending
        eligibility=services.report()['eligibility']
        assert eligibility['writers']>1 and eligibility['readers']>1
        assert eligibility['cross_agent_reads']>=5 and eligibility['isolation_passed']
        report['memory_finalization']['frozen_result_sha256_after']=result_digest(report)
        report.update(status='completed',phase='Frozen V17 evaluation and verified memory review complete',completed_at=now())
        await publish();save('report',report)
        await ledger.put.aio(claim_key,{'workflow_run':os.environ['GITHUB_RUN_ID'],'status':'completed','result_sha256':frozen})
    except Exception as exc:
        report.update(status='incomplete',phase='Memory-only finalization stopped with evidence preserved',
            error_type=type(exc).__name__,error=str(exc)[:200])
        await publish();save('memory-finalization-incomplete',report)
        raise
    finally:
        await services.http.aclose()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True);parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args();source=Path(args.source)
    if args.validate_only:
        report,journal,record=load(source);packet=compact_result(report,record,source)
        print(json.dumps({'frozen_result_sha256':result_digest(report),'optimizer_updates':16,
            'component_rows':24,'compact_characters':len(json.dumps(packet,sort_keys=True)),
            'additional_optimizer_updates':0,'additional_physical_stages':0}))
    else:
        asyncio.run(finish(source))


if __name__=='__main__':main()
