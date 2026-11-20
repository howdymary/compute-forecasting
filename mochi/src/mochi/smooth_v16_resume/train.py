"""Bounded fresh-data continuation after the completed V15 assessment.

The directional navigator and action library are frozen before baseline.
Tinker updates six-domain categorical LoRA weights; the native gait stays fixed.
"""
import asyncio
import hashlib
import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

import modal
import numpy as np

from ..curriculum.world import ROOT, TASKS
from ..integrations import now, digest
from ..maintenance.checkpoints_by_date import inventory
from ..terrain_v12.learning_remote import sampler_payload
from ..smooth_v16.policy import decision
from ..smooth_v16.objective import summary, paired
from ..smooth_v16.objective import static_from_training, meaningful_corrections
from .objective import select_checkpoint
from .remote import app, staged_collect as collect, evaluate, components
from .services import ContinuationServices

OUT = ROOT / 'artifacts/smooth-v16r1-training'


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / (name + '.json')
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(target)


def summarize_and_save(name,rows,cfg):
    stats=summary(rows,cfg)
    save(name,rows)
    return stats


def probe_summary(row):
    return {**{k:row.get(k) for k in ['seed','complete_sequence_success','failure','archive','public_recording','model_decisions','direction_metrics']},
            'steps':row['episode']['steps'],'duration_s':row['episode']['duration']}


async def main():
    import tinker
    from tinker_cookbook.recipes.decisions import decision_choice_datums, sample_decision

    cfg = json.loads((ROOT / 'configs/smooth-v16r1-training.json').read_text())
    from ..smooth_v16.parent import load_parent
    previous, parent, selection = await load_parent(cfg)
    assessment_path = ROOT / 'docs/efficient-v15-assessment.json'
    assessment = json.loads(assessment_path.read_text())
    assessment['held_out']={k:{'failures':v['failures'],'forbidden_contacts':v['statistics']['invalid_contacts']} for k,v in assessment['held_out'].items()}
    engineering_path=ROOT/'evidence/smooth-v16/engineering.json'
    assert hashlib.sha256(engineering_path.read_bytes()).hexdigest()==cfg['engineering_evidence_sha256']
    engineering=json.loads(engineering_path.read_text())
    assert hashlib.sha256((ROOT / cfg['implementation_prompt']).read_bytes()).hexdigest() == cfg['prompt_sha256']
    for path, expected in cfg['frozen_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, 'Frozen file changed: ' + path
    for path,expected in cfg['continuation_frozen_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected, 'Continuation changed: '+path
    assert hashlib.sha256((ROOT.parent/'.github/workflows/mochi-smooth-v16r1-training.yml').read_bytes()).hexdigest()==cfg['workflow_sha256']
    interrupted=await modal.Dict.from_name('mochi-smooth-v16-progress').get.aio('mochi-t16-44669222147')
    assert interrupted['status']=='incomplete' and interrupted['optimizer_updates_completed']==0
    assert interrupted['source_sha']=='795a664f98433e514b5a76e9c2c606ba6136b130'
    old_rows=json.loads((ROOT/'.cache/v16-stopped/checkpoint-0.json').read_text())
    assert summary(old_rows,cfg)==interrupted['parent_baseline']
    cfg['parent_checkpoint_sha256'] = digest(parent)
    cfg['parent_optimizer_updates'] = selection['cumulative_updates']
    partitions = [set(cfg[k]) for k in ['training_seeds','development_seeds','held_out_seeds']]
    assert not any(a & b for i,a in enumerate(partitions) for b in partitions[i+1:])
    old_seeds = set(sum([previous['protocol'][k] for k in ['training_seeds','development_seeds','held_out_seeds']], []))
    assert not old_seeds.intersection(set.union(*partitions))
    run_id = 'mochi-t16r1-' + os.environ['GITHUB_RUN_ID']
    progress = modal.Dict.from_name('mochi-smooth-v16r1-progress', create_if_missing=True)
    # Rerunning an interrupted job cannot silently repeat gradients or create
    # the same identities/artifacts. Resume must be explicitly reconciled.
    assert await progress.get.aio(run_id) is None, 'Existing run; inspect durable state before resuming'
    usage = {k: 0 for k in cfg['bounds'] if k != 'modal_concurrency'}
    usage.update(cfg['engineering_usage'])
    ledger = modal.Dict.from_name(run_id + '-budget', create_if_missing=True)
    assert await ledger.get.aio('usage') is None, 'Existing reservations require reconciliation'
    lock = asyncio.Lock()
    publish_lock = asyncio.Lock()
    simulation_slots = asyncio.Semaphore(cfg['bounds']['modal_concurrency'])
    teacher_rows=[]
    teacher_pair_ready=asyncio.Event()
    services = ContinuationServices()
    services.run_id = run_id
    services.actors = {r: run_id + '-' + r for r in ['researcher', 'designer', 'experimenter', 'critic']}
    services.audience, services.private = run_id + '-shared', run_id + '-critic'
    report = {'study': cfg['study'], 'run_id': run_id, 'source_sha': interrupted['source_sha'], 'execution_source_sha':os.getenv('GITHUB_SHA'),
        'created_at': now(), 'status': 'running', 'phase': 'Recall the interrupted V16 collection and preserved recovery evidence',
        'protocol': cfg, 'protocol_sha256': digest(cfg), 'scope': cfg['scope'],
        'optimizer_updates_completed': 0, 'training_log': [], 'checkpoints': [],
        'held_out_opened': False, 'physics_receipts': [], 'campaign_modal_rollouts_completed': 0,
        'parent_selection': selection,'engineering_usage':cfg['engineering_usage'],
        'execution_variant':'resumable V16 continuation',
        'prior_execution':{'run_id':interrupted['run_id'],'status':interrupted['status'],
            'error_type':interrupted['error_type'],'optimizer_updates_completed':0,
            'budget_usage_or_reserved':interrupted['budget_usage_or_reserved'],
            'confirmed_completed_rollouts':interrupted['total_physical_rollouts_completed'],
            'completed_branch_outcomes':await modal.Dict.from_name(interrupted['run_id']+'-branches').len.aio(),
            'accounting':json.loads((ROOT/'evidence/smooth-v16/stopped-execution.json').read_text()),
            'qualification':'Prior ledger preserved. Reserved amounts include unfinished work and are not an invoice.'},
        'continuation_prompt':{'path':'docs/smooth-v16-continuation-prompt.md',
            'sha256':hashlib.sha256((ROOT/'docs/smooth-v16-continuation-prompt.md').read_bytes()).hexdigest()}}

    report['implementation_prompt'] = {'path': cfg['implementation_prompt'], 'sha256': cfg['prompt_sha256']}

    async def change(kind, amount):
        async with lock:
            value = usage[kind] + amount
            if not 0 <= value <= cfg['bounds'][kind]:
                raise RuntimeError('V16 hard budget ceiling: ' + kind)
            usage[kind] = value
            await ledger.put.aio('usage', dict(usage))

    async def publish():
        async with publish_lock:
            report['budget_usage_or_reserved'] = dict(usage)
            report['total_physical_rollouts_completed']=cfg['engineering_usage']['physical_rollouts']+report['campaign_modal_rollouts_completed']
            report['services'] = services.report()
            snapshot=json.loads(json.dumps(report))
            save('progress', snapshot)
            await progress.put.aio(run_id, snapshot)
            await progress.put.aio('latest', snapshot)
            print('MOCHI_T16R1 ' + json.dumps({'phase': report['phase'], 'updates': report['optimizer_updates_completed'],
                  'physical_rollouts': report['total_physical_rollouts_completed'], 'usage': usage}), flush=True)

    async def write(role, content, private=False):
        await change('past_writes', 1)
        phase = report['phase']
        report['phase'] = 'past.dev write: ' + role + ' ' + content.get('kind', 'finding')
        await publish()
        try:
            return await services.write(role, content, private)
        finally:
            report['phase'] = phase
            await publish()

    async def read(role, rid, allowed=True):
        await change('past_recalls', 1)
        phase = report['phase']
        report['phase'] = 'past.dev recall: ' + role + (' source verification' if allowed else ' private-audience denial test')
        await publish()
        try:
            return await services.read(role, rid, allowed)
        finally:
            report['phase'] = phase
            await publish()

    async def batch(function, arguments, timeout, rollout_cap, token_cap, parallel_limit=None):
        batch_phase=report['phase']
        queue = asyncio.Queue()
        for index, args in enumerate(arguments):
            queue.put_nowait((index, args))
        answers = {}

        async def worker():
            while not queue.empty():
                try:
                    index, args = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                async with simulation_slots:
                    await change('physical_rollouts', rollout_cap)
                    await change('simulation_cpu_hours', timeout / 3600)
                    await change('inference_tokens', token_cap)
                    row = await function.remote.aio(*args)
                    receipt = row['receipt']
                    await change('physical_rollouts', receipt['physical_rollouts'] - rollout_cap)
                    await change('simulation_cpu_hours', (receipt['duration_seconds'] - timeout) / 3600)
                    await change('inference_tokens', receipt.get('inference_input_plus_max_output_tokens', 0) - token_cap)
                answers[index] = row
                report['campaign_modal_rollouts_completed'] += receipt['physical_rollouts']
                report['physics_receipts'].append({'phase': batch_phase, 'seed': row['seed'],
                    'label': row.get('label'), 'group': row.get('group'), 'task': row.get('task'), 'receipt': receipt})
                if function is collect:
                    save('teacher-' + str(row['seed']), row)
                    teacher_rows.append(row)
                    if len(teacher_rows)>=2:
                        teacher_pair_ready.set()
                elif function is evaluate:
                    saved = row['row']
                    save('recording-' + str(args[4]) + '-' + str(row['seed']) + '-' + row['label'], {
                        'seed': row['seed'], 'label': row['label'], 'group': args[4],
                        'archive': saved['archive'], 'failure': saved['failure'],
                        'complete_sequence_success': saved['complete_sequence_success'],
                        'storage': 'Full immutable trajectory in Modal; grouped completed results follow locally.'})
                else:
                    save('components-' + str(row['seed']) + '-' + row['task'], row)
                await publish()
                queue.task_done()

        await asyncio.gather(*(worker() for _ in range(min(parallel_limit or cfg['bounds']['modal_concurrency'], len(arguments)))))
        return [answers[k] for k in sorted(answers)]

    started = time.perf_counter()
    checkpoint_paths, snapshots, development = {}, {}, {}
    rng = np.random.default_rng(cfg['training']['seed'])
    try:
        records = await inventory(tinker.RestClient())
        assert sum(digest(r.tinker_path) == cfg['parent_checkpoint_sha256'] for r in records) == 1
        durable_updates = sorted(set(cfg['training']['checkpoints']) | set(range(4, cfg['training']['updates'] + 1, 4)))
        assert len(records) + len(durable_updates) - 1 < 100, 'No checkpoint deletions authorized'
        report['checkpoint_storage_count_before'] = len(records)
        await services.setup()
        await publish()

        # A real cross-run recall of the previous critic's shared verdict.
        ready = {r['id']: r for r in interrupted['services']['records']}
        prior_reads = [r for r in interrupted['services']['reads']
                       if r['source_id_verified'] and r['cross_agent_use'] and r['record_id'] in ready]
        assert prior_reads, 'No source-verified memory finding available'
        preferred = [r for r in prior_reads if ready[r['record_id']]['role'] == 'critic'
                     and r['reader_role'] == 'researcher']
        original_read = (preferred or prior_reads)[-1]
        verdict = ready[original_read['record_id']]
        old_memory = ContinuationServices()
        old_memory.records[verdict['id']] = verdict
        old_memory.actors[original_read['reader_role']] = original_read['reader']
        try:
            await change('past_recalls', 1)
            old_verdict = await old_memory.read(original_read['reader_role'], verdict['id'])
            report['cross_run_memory'] = {'record_id': verdict['id'], 'reads': old_memory.reads,
                'source_kind': verdict['payload']['content'].get('kind'),
                'final_critic_verdict_available': bool(preferred),
                'calls': old_memory.calls, 'content_sha256': digest(old_verdict)}
        finally:
            await old_memory.http.aclose()
        eid = await write('experimenter', {'kind': 'observation', 'experiment_id': run_id,
            'prior_execution':report['prior_execution'], 'collector_change':'Exact-state, durable per-action Modal stages replace the timed-out monolithic collector.',
            'route_reference_sha256': cfg['engineering_evidence_sha256'], 'prior_verdict_record': verdict['id'],
            'held_out': previous['held_out'], 'failures': assessment['held_out'], 'step_objective':cfg['objective'],
            'current_engineering':engineering['validated_route'],
            'current_failure':engineering['failed_attempts'],
            'qualification': 'Previous test scenarios are historical evidence; V16 uses separate unopened final seeds.'})
        observation = await read('researcher', eid)
        await change('exa_searches', 1)
        problems = []
        if any(v['failures'].get('fall', 0) for v in observation['failures'].values()):
            problems.append('humanoid stair ascent descent support transfer stability')
        if any(v['forbidden_contacts'] for v in observation['failures'].values()):
            problems.append('whole body collision avoidance laptop lid manipulation release arm withdrawal')
        await change('inference_tokens', 4000)
        direction = await services.decide('researcher',
            'Choose a research emphasis from measured support-transfer failures and excessive recovery joint travel. This chooses an Exa query, not a change to frozen physics.',
            {'observed_problems': problems, 'historical_failures': {k: v['failures'] for k, v in observation['failures'].items()},
             'measured_step_comparison':observation['current_engineering'],'engineering_failures':observation['current_failure']},
            ['turning_steps', 'forward_descent', 'task_withdrawal'], [eid])
        focus = {'turning_steps':'humanoid velocity command tracking turning reduce corrective footsteps',
                 'forward_descent':'humanoid forward stair descent full sole touchdown support transfer inverse dynamics',
                 'task_withdrawal':'robot contact manipulation release efficient collision free arm withdrawal'}[direction]
        query = 'robot control research ' + focus
        sources = await services.search(query)
        hid = await write('researcher', {'kind': 'hypothesis', 'experiment_id': run_id,
            'observation_record': eid, 'sources': sources,
            'research_direction': direction,
            'mechanism': 'Compare physically validated turn, forward-descent and Post-it routes. Prefer fewer measured steps and less recovery joint travel; retain validity and completion before cost.',
            'prediction': 'Post-training may reduce unnecessary steps and recovery joint travel without lower completion or longer successful time. The native gait network remains fixed.',
            'supersedes': verdict['id'], 'qualification': 'Testable proposal, not an established performance gain.'})
        hypothesis = await read('designer', hid)
        await change('inference_tokens', 4000)
        allocation = await services.decide('designer',
            'Choose the six-domain allocation: recovery_first uses 12 walking,16 recovery and3 examples per object task; balanced uses16 walking,16 recovery and2 per object task. Both target walking and recovery with all tasks represented.',
            {'mechanism': hypothesis['mechanism'], 'parent_complete': previous['held_out']['selected']['complete_successes'],
             'parent_n': previous['held_out']['selected']['n'], 'sources': sources['sources']},
            ['recovery_first', 'balanced'], [eid, hid])
        pid = await write('designer', {'kind': 'proposal', 'experiment_id': run_id,
            'hypothesis_record': hid, 'allocation': allocation,
            'frozen_protocol_sha256': digest(cfg), 'controller_changes': 'Physical turn, forward descent, paper-top verifier and recovery options are frozen before baseline and shared across weights.'})
        proposal = await read('experimenter', pid)
        counts = {'walk': 12 if proposal['allocation'] == 'recovery_first' else 16,
                  **{t: 3 if proposal['allocation']=='recovery_first' else 2 for t in TASKS},'recovery':16}
        report['domain_batch_counts'] = counts
        trainer = await services.service.create_training_client_from_state_with_optimizer(parent)
        snapshots[0] = await trainer.save_weights_and_get_sampling_client(kind='snapshot')
        checkpoint_paths['0'] = {'optimizer': parent}
        save('checkpoint-paths', checkpoint_paths)
        async with app.run():
            report['phase']='Verify preserved fixed reference and parent development evidence'
            report['remote_reference']=interrupted['remote_reference']
            assert report['remote_reference']['complete_sequence_success']
            report['reused_parent_evaluation']={'run_id':interrupted['run_id'],'source_sha':interrupted['source_sha'],
                'seeds':cfg['development_seeds'],'numerical_rows_sha256':digest(old_rows),
                'scope':'Historical evaluations reused without new simulation; not new receipts.'}
            baseline=[{'seed':row['seed'],'label':'policy','group':'dev-0','row':row} for row in old_rows]
            development[0]=old_rows
            report['parent_baseline']=summarize_and_save('checkpoint-0',development[0],cfg)
            await publish()
            base=report['parent_baseline']
            report['numerical_development_targets']={
                'steps_max':.9*base['successful_mean_steps'] if base['successful_mean_steps'] else None,
                'seconds_max':base['successful_mean_seconds'],
                'recovery_arm_travel_max':.85*base['successful_mean_recovery_arm_joint_travel_rad'] if base['successful_mean_recovery_arm_joint_travel_rad'] else None,
                'qualification':'Efficiency is compared only on matched successful scenarios; failed early episodes do not establish a cheap baseline.'}
            report['phase'] = 'Guarded student-state data generation on Modal'
            await publish()
            teacher_task=asyncio.create_task(batch(collect,[(seed,sampler_payload(snapshots[0]),run_id)
                for seed in cfg['training_seeds']],10800,53,30000))
            teachers=await teacher_task  # Join all physics before any model-evaluation worker.
            domains = cfg['training']['domains']

            def signal_ready(rows):
                opportunities=meaningful_corrections(rows)
                present={e['domain'] for t in rows for e in t['examples']}
                return (sum(t['valid'] for t in rows)>=2 and set(domains)<=present
                    and opportunities.get('walk',0)>0)

            if not signal_ready(teachers):
                teachers=await teacher_task

            def prepare_data():
                data=defaultdict(list)
                for teacher in teachers:
                    for e in teacher['examples']:
                        data[e['domain']].append((e['observation'],e['action']))
                report['data_audit']={d:{'examples':len(data[d]),'labels':dict(Counter(a for _,a in data[d]))} for d in domains}
                report['guarded_student_sequences_complete']=sum(t['valid'] for t in teachers)
                report['guard_interventions']=sum(e['guard_intervened'] for t in teachers for e in t['examples'])
                report['student_label_disagreements']={d:sum(max(e['student_distribution'],key=e['student_distribution'].get)!=e['action']
                    for t in teachers for e in t['examples'] if e['domain']==d) for d in domains}
                report['static_preference']=static_from_training(teachers)
                report['meaningful_correction_opportunities']=meaningful_corrections(teachers)
                report['recovery_training_scope']='Measured correction examples where available; retention examples where the parent already selects the best reachable recovery.'
                report['data_collection_provenance']={'reused_outcomes':sum(len(t['reused_outcomes']) for t in teachers),
                    'new_physical_stage_count':sum(t['receipt']['physical_rollouts'] for t in teachers),
                    'snapshot_training_only':True,'final_evaluation_uses_uninterrupted_run':True}
                save('training-observations',data)
                assert signal_ready(teachers), 'Insufficient complete data or substantial walking corrections'
                datums={d:decision_choice_datums(services.renderer,[(decision(o),a) for o,a in data[d]]) for d in domains}
                report.setdefault('data_stages',[]).append({'before_update':report['optimizer_updates_completed']+1,
                    'seeds':[t['seed'] for t in teachers],'data_sha256':digest(data)})
                return data,datums

            data,datums=prepare_data()
            probes = [data[d][0][0] for d in domains]
            early_evaluations=[]
            initial = None
            report['phase'] = 'Actual Tinker walking, task and recovery post-training'
            await publish()
            for update in range(cfg['training']['updates'] + 1):
                if update and update in durable_updates:
                    state = await trainer.save_state(f'mochi_t16r1_{os.environ["GITHUB_RUN_ID"]}_{update}')
                    checkpoint_paths[str(update)] = {'optimizer': state.path, 'rng_state': rng.bit_generator.state}
                    # Persist the optimizer reference before any sampling or
                    # diagnostic call that might fail.
                    save('checkpoint-paths', checkpoint_paths)
                    report['durable_optimizer_updates'] = sorted(map(int, checkpoint_paths))
                if update in cfg['training']['checkpoints']:
                    if update:
                        snapshots[update] = await trainer.save_weights_and_get_sampling_client(kind='snapshot')
                    distributions = []
                    for obs in probes:
                        rendering = services.renderer.render(decision(obs))
                        await change('inference_tokens', len(rendering.tokens) + 1)
                        distributions.append({'domain': obs['domain'],
                            'distribution': await sample_decision(snapshots[update], rendering)})
                    if initial is None:
                        initial = {p['domain']: p['distribution'] for p in distributions}
                    if update == 1:
                        delta = {p['domain']: max(abs(v - initial[p['domain']][a]) for a, v in p['distribution'].items()) for p in distributions}
                        report['first_optimizer_behavioral_probe'] = delta
                        assert all(delta[d] > 1e-7 for d in ['walk','recovery']), 'Walking/recovery probabilities show no measurable update'
                    report['checkpoints'].append({'update': update,
                        'cumulative_updates': cfg['parent_optimizer_updates'] + update,
                        'checkpoint_id': digest(checkpoint_paths[str(update)]['optimizer']),
                        'development': None, 'probe_distributions': distributions})
                    save('checkpoint-paths', checkpoint_paths)
                    await publish()
                    if update==1:
                        report['phase']='First optimizer end-to-end physical probe'
                        await publish()
                        early_evaluations=await batch(evaluate,[(cfg['development_seeds'][0],'policy',
                            sampler_payload(snapshots[1]),run_id,'dev-1')],1800,1,24000)
                        report['first_optimizer_physical_probe']={'parent':probe_summary(development[0][0]),
                            'updated':probe_summary(early_evaluations[0]['row']),'scope':'Predeclared development scenario, retained in final development comparison. Exact trajectories and counters are in the hash-verified archives.'}
                        report['phase']='Join remaining frozen-parent data after first optimizer probe'
                        await publish()
                        teachers=await teacher_task
                        data,datums=prepare_data()
                        report['phase']='Actual Tinker walking, task and recovery post-training'
                if update == cfg['training']['updates']:
                    break
                indices = {d: [int(i) for i in rng.choice(len(data[d]), counts[d], replace=True)] for d in domains}
                tokens = sum(datums[d][i].model_input.length for d in domains for i in indices[d])
                await change('training_token_presentations', tokens)
                await change('optimizer_updates', 1)
                pending = [(d, trainer.forward_backward([datums[d][i] for i in indices[d]], loss_fn='cross_entropy')) for d in domains]
                optimizer = trainer.optim_step(tinker.AdamParams(learning_rate=cfg['training']['learning_rate']))
                losses = {d: (await result).metrics for d, result in pending}
                await optimizer
                report['optimizer_updates_completed'] = update + 1
                report['training_log'].append({'update': update + 1, 'domain_loss_metrics': losses,
                    'domain_counts': counts, 'tokens': tokens, 'batch_sha256': digest(indices),
                    'forward_backward_completed': True, 'optimizer_completed': True, 'at': now()})
                await publish()

            report['phase'] = 'Matched directional development tests for every saved checkpoint'
            await publish()
            bundles = baseline+early_evaluations+await batch(evaluate, [(seed, 'policy', sampler_payload(snapshots[cp['update']]),
                run_id, 'dev-' + str(cp['update'])) for cp in report['checkpoints']
                for seed in cfg['development_seeds'] if cp['update']!=0 and not(cp['update']==1 and seed==cfg['development_seeds'][0])], 1800, 1, 24000)
            for cp in report['checkpoints']:
                update = cp['update']
                rows = [b['row'] for b in bundles if b['group'] == 'dev-' + str(update)]
                development[update] = rows
                cp['development'] = summarize_and_save('checkpoint-' + str(update),rows,cfg)
                await publish()
            selected = select_checkpoint(report['checkpoints'], development, cfg)
            report['selected_checkpoint'] = selected
            save('selection-freeze', report)
            report['held_out_opened'] = True
            report['phase'] = 'Unopened final tests against parent, fixed and training-only static policies'
            await publish()
            models = [('parent', sampler_payload(snapshots[0]), None),
                      ('selected', sampler_payload(snapshots[selected['update']]), None),
                      ('fixed', None, None), ('static', None, report['static_preference'])]
            bundles = await batch(evaluate, [(seed, label, payload, run_id, 'held-out', static,
                label == 'fixed') for seed in cfg['held_out_seeds']
                for label, payload, static in models], 1800, 1, 24000)
            held = {label: [b['row'] for b in bundles if b['label'] == label] for label, _, _ in models}
            report['held_out'] = {label:summarize_and_save('held-out-'+label,rows,cfg) for label,rows in held.items()}
            report['paired_held_out'] = paired(held['parent'],held['selected'])
            pp=report['paired_held_out']
            report['improvement_goal_met']=bool(report['held_out']['selected']['qualified_complete_successes']==len(cfg['held_out_seeds']) and pp['n']>=2 and pp['mean_step_reduction_fraction']>=.10 and pp['mean_recovery_arm_travel_reduction_fraction']>=.15 and pp['mean_time_reduction_fraction']>=0 and report['held_out']['selected']['falls']<=report['held_out']['parent']['falls'] and report['held_out']['selected']['invalid_contacts']<=report['held_out']['parent']['invalid_contacts'])
            # This predeclared reference rule never looks at trained outcomes.
            # All fixed failures remain in the full-cohort denominator.
            reference_row = next((r for r in held['fixed'] if r['complete_sequence_success']),
                max(held['fixed'], key=lambda r: len(r['supported_states']['keys'])))
            reference = reference_row['supported_states']
            report['component_reference_seed'] = reference_row['seed']
            report['phase'] = 'Exact shared-state walking, task and arm-recovery diagnostics'
            await publish()
            report['component_results'] = await batch(components, [(reference_row['seed'], task,
                [('parent', sampler_payload(snapshots[0])), ('selected', sampler_payload(snapshots[selected['update']]))],
                run_id, reference) for task in TASKS], 3600, 6, 24000, parallel_limit=1)
            try:
                rid = await write('experimenter', {'kind': 'observation', 'experiment_id': run_id,
                    'optimizer_updates_completed': report['optimizer_updates_completed'],
                    'selected_checkpoint': selected, 'held_out': report['held_out'],
                    'components': [{'task': x['task'], 'results': x['results']} for x in report['component_results']], 'paired_step_results':report['paired_held_out'], 'improvement_goal_met':report['improvement_goal_met'],
                    'supersedes': eid})
                measured = await read('critic', rid)
                await change('inference_tokens', 4000)
                critic_label = await services.decide('critic',
                    'Classify the bounded simulation evidence. Compare parent and selected success first. Additional optimizer steps or altered probabilities are not evidence of better control. A static preference matching the model limits claims of adaptation. Keep small cohorts qualified.',
                    {'final_test_metrics': measured['held_out'], 'selected_update': selected['update'], 'paired_step_results':measured['paired_step_results'], 'goal_met':measured['improvement_goal_met'],
                     'scope': 'Native gait fixed; full-route tests and separate exact-state component branches.'},
                    ['bounded_simulated_gain', 'no_demonstrated_gain', 'regression_or_uncertain'], [rid])
                vid = await write('critic', {'kind': 'qualified-conclusion', 'experiment_id': run_id,
                    'evidence_record': rid, 'evidence_sha256': digest(measured),
                    'model_interpretation': critic_label, 'interpretation_is_advisory': True,
                    'conclusion': 'Report full completion, successful-only paired costs and exact-state component effects separately. Training or changed probabilities alone do not establish improved physical control. Native gait weights stayed fixed.',
                    'supersedes': hid})
                await read('researcher', vid)
                canary = await write('critic', {'kind': 'private-test', 'text': 'MOCHI_PRIVATE_CANARY'}, True)
                await read('designer', canary, False)
            except TimeoutError as exc:
                report['final_memory_review_pending'] = {'error_type': type(exc).__name__,
                    'pending': services.report().get('pending_ingestions', [])}
        assert not services.report().get('pending_ingestions'), 'Final memory ingestion remains pending; retain durable evidence and reconcile before completion'
        report.update(status='completed', phase='Frozen V16 evaluation complete', completed_at=now(),
                      duration_seconds=time.perf_counter() - started)
        await publish()
        save('report', report)
    except Exception as exc:
        report.update(status='incomplete', phase='Stopped with durable evidence preserved',
                      error_type=type(exc).__name__, error=str(exc)[:240])
        save('incomplete', report)
        await publish()
        raise
    finally:
        await services.http.aclose()


if __name__ == '__main__':
    with modal.enable_output():
        asyncio.run(main())
