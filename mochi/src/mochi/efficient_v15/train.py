"""Bounded fresh-data continuation after the completed V12 assessment.

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
from .policy import decision
from .objective import summary, paired
from .objective import rank as checkpoint_rank, static_from_training, meaningful_corrections
from .remote import app, collect, evaluate, components
from .services import ContinuationServices

OUT = ROOT / 'artifacts/efficient-v15-training'


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


async def main():
    import tinker
    from tinker_cookbook.recipes.decisions import decision_choice_datums, sample_decision

    cfg = json.loads((ROOT / 'configs/efficient-v15-training.json').read_text())
    from .parent import load_parent
    previous, parent, selection = await load_parent(cfg)
    assessment_path = ROOT / 'docs/terrain-v12-assessment.json'
    assessment = json.loads(assessment_path.read_text())
    engineering_path=ROOT/'evidence/efficient-v15/engineering.json'
    assert hashlib.sha256(engineering_path.read_bytes()).hexdigest()==cfg['engineering_evidence_sha256']
    engineering=json.loads(engineering_path.read_text())
    assert hashlib.sha256((ROOT / cfg['implementation_prompt']).read_bytes()).hexdigest() == cfg['prompt_sha256']
    for path, expected in cfg['frozen_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, 'Frozen file changed: ' + path
    cfg['parent_checkpoint_sha256'] = digest(parent)
    cfg['parent_optimizer_updates'] = selection['cumulative_updates']
    partitions = [set(cfg[k]) for k in ['training_seeds','development_seeds','held_out_seeds']]
    assert not any(a & b for i,a in enumerate(partitions) for b in partitions[i+1:])
    old_seeds = set(sum([previous['protocol'][k] for k in ['training_seeds','development_seeds','held_out_seeds']], []))
    assert not old_seeds.intersection(set.union(*partitions))
    run_id = 'mochi-t15-' + os.environ['GITHUB_RUN_ID']
    progress = modal.Dict.from_name('mochi-efficient-v15-progress', create_if_missing=True)
    # Rerunning an interrupted job cannot silently repeat gradients or create
    # the same identities/artifacts. Resume must be explicitly reconciled.
    assert await progress.get.aio(run_id) is None, 'Existing run; inspect durable state before resuming'
    usage = {k: 0 for k in cfg['bounds'] if k != 'modal_concurrency'}
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
    report = {'study': cfg['study'], 'run_id': run_id, 'source_sha': os.getenv('GITHUB_SHA'),
        'created_at': now(), 'status': 'running', 'phase': 'Recall the completed V12 assessment',
        'protocol': cfg, 'protocol_sha256': digest(cfg), 'scope': cfg['scope'],
        'optimizer_updates_completed': 0, 'training_log': [], 'checkpoints': [],
        'held_out_opened': False, 'physics_receipts': [], 'campaign_modal_rollouts_completed': 0,
        'parent_selection': selection}
    report['implementation_prompt'] = {'path': cfg['implementation_prompt'], 'sha256': cfg['prompt_sha256']}

    async def change(kind, amount):
        async with lock:
            value = usage[kind] + amount
            if not 0 <= value <= cfg['bounds'][kind]:
                raise RuntimeError('V15 hard budget ceiling: ' + kind)
            usage[kind] = value
            await ledger.put.aio('usage', dict(usage))

    async def publish():
        async with publish_lock:
            report['budget_usage_or_reserved'] = dict(usage)
            report['services'] = services.report()
            snapshot=json.loads(json.dumps(report))
            save('progress', snapshot)
            await progress.put.aio(run_id, snapshot)
            await progress.put.aio('latest', snapshot)
            print('MOCHI_T15 ' + json.dumps({'phase': report['phase'], 'updates': report['optimizer_updates_completed'],
                  'physical_rollouts': report['campaign_modal_rollouts_completed'], 'usage': usage}), flush=True)

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

    async def batch(function, arguments, timeout, rollout_cap, token_cap):
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
                    await change('modal_rollouts', rollout_cap)
                    await change('modal_cpu_hours', timeout / 3600)
                    await change('inference_tokens', token_cap)
                    row = await function.remote.aio(*args)
                    receipt = row['receipt']
                    await change('modal_rollouts', receipt['physical_rollouts'] - rollout_cap)
                    await change('modal_cpu_hours', (receipt['duration_seconds'] - timeout) / 3600)
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

        await asyncio.gather(*(worker() for _ in range(min(cfg['bounds']['modal_concurrency'], len(arguments)))))
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
        ready = {r['id']: r for r in previous['services']['records']}
        prior_reads = [r for r in previous['services']['reads']
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
            'directional_reference_sha256': cfg['engineering_evidence_sha256'], 'prior_verdict_record': verdict['id'],
            'held_out': previous['held_out'], 'failures': assessment['held_out'], 'step_objective':cfg['objective'],
            'current_engineering':engineering['matched_full_routes'],
            'current_failure':engineering['failed_fast_globe'],
            'qualification': 'Previous test scenarios are now historical evidence; V15 uses separate unopened final seeds.'})
        observation = await read('researcher', eid)
        await change('exa_searches', 1)
        problems = []
        if any(v['failures'].get('fall', 0) for v in observation['failures'].values()):
            problems.append('humanoid stair ascent descent support transfer stability')
        if any(v['forbidden_contacts'] for v in observation['failures'].values()):
            problems.append('whole body collision avoidance laptop lid manipulation release arm withdrawal')
        await change('inference_tokens', 4000)
        direction = await services.decide('researcher',
            'Choose a research emphasis for measured small corrective steps and deliberate turning. This selects the actual Exa query, not a controller change during training.',
            {'observed_problems': problems, 'historical_failures': {k: v['failures'] for k, v in observation['failures'].items()},
             'measured_step_comparison':observation['current_engineering'],'globe_overshoot':observation['current_failure']},
            ['turning_steps', 'station_alignment', 'task_withdrawal'], [eid])
        focus = {'turning_steps':'humanoid velocity command tracking turning reduce corrective footsteps',
                 'station_alignment':'humanoid target approach braking avoid small corrective steps',
                 'task_withdrawal':'robot contact manipulation release efficient collision free arm withdrawal'}[direction]
        query = 'robot control research ' + focus
        sources = await services.search(query)
        hid = await write('researcher', {'kind': 'hypothesis', 'experiment_id': run_id,
            'observation_record': eid, 'sources': sources,
            'research_direction': direction,
            'mechanism': 'Use contact-derived step attempts to compare bounded forward-speed and approach-gain choices, while retaining turn-first navigation and scoring task plus safe withdrawal.',
            'prediction': 'Post-training may reduce unnecessary physical steps and task/recovery cost without lowering completion or safety. The native gait network remains fixed.',
            'supersedes': verdict['id'], 'qualification': 'Testable proposal, not an established performance gain.'})
        hypothesis = await read('designer', hid)
        await change('inference_tokens', 4000)
        allocation = await services.decide('designer',
            'Choose the six-domain training allocation: efficiency_first uses 16 walking and 8 recovery examples; balanced uses 12 walking and 12 recovery. Each of the four tasks gets four examples in either case.',
            {'mechanism': hypothesis['mechanism'], 'parent_complete': previous['held_out']['selected']['complete_successes'],
             'parent_n': previous['held_out']['selected']['n'], 'sources': sources['sources']},
            ['efficiency_first', 'balanced'], [eid, hid])
        pid = await write('designer', {'kind': 'proposal', 'experiment_id': run_id,
            'hypothesis_record': hid, 'allocation': allocation,
            'frozen_protocol_sha256': digest(cfg), 'controller_changes': 'Directional navigation and new bounded W3/W4 options integrated before baseline; fixed across all weights.'})
        proposal = await read('experimenter', pid)
        counts = {'walk': 16 if proposal['allocation'] == 'efficiency_first' else 12,
                  **{t: 4 for t in TASKS}, 'recovery': 8 if proposal['allocation'] == 'efficiency_first' else 12}
        report['domain_batch_counts'] = counts
        trainer = await services.service.create_training_client_from_state_with_optimizer(parent)
        snapshots[0] = await trainer.save_weights_and_get_sampling_client(kind='snapshot')
        checkpoint_paths['0'] = {'optimizer': parent}
        save('checkpoint-paths', checkpoint_paths)
        async with app.run():
            report['phase']='Remote fixed-controller feasibility before gradients'
            await publish()
            preflight=(await batch(evaluate,[(cfg['preflight_seed'],'fixed',None,run_id,'preflight')],1800,1,0))[0]
            report['remote_reference']=preflight['row']
            assert preflight['row']['complete_sequence_success'], 'Integrated fixed-controller reference failed; repair before training'
            report['phase']='Frozen parent baseline with directional navigation'
            await publish()
            baseline=await batch(evaluate,[(seed,'policy',sampler_payload(snapshots[0]),run_id,'dev-0')
                for seed in cfg['development_seeds']],1800,1,24000)
            development[0]=[b['row'] for b in baseline]
            report['parent_baseline']=summarize_and_save('checkpoint-0',development[0],cfg)
            base=report['parent_baseline']
            report['numerical_development_targets']={
                'steps_max':.8*base['successful_mean_steps'] if base['successful_mean_steps'] else None,
                'seconds_max':base['successful_mean_seconds'],
                'seconds_stretch':.9*base['successful_mean_seconds'] if base['successful_mean_seconds'] else None,
                'qualification':'Efficiency is compared only on matched successful scenarios; failed early episodes do not establish a cheap baseline.'}
            report['phase'] = 'Guarded student-state data generation on Modal'
            await publish()
            teacher_task=asyncio.create_task(batch(collect,[(seed,sampler_payload(snapshots[0]),run_id)
                for seed in cfg['training_seeds']],5400,37,24000))
            pair_wait=asyncio.create_task(teacher_pair_ready.wait())
            done,_=await asyncio.wait({teacher_task,pair_wait},return_when=asyncio.FIRST_COMPLETED)
            if teacher_task in done:
                teachers=await teacher_task
                pair_wait.cancel()
            else:
                teachers=list(teacher_rows)
            domains = cfg['training']['domains']

            def signal_ready(rows):
                opportunities=meaningful_corrections(rows)
                present={e['domain'] for t in rows for e in t['examples']}
                return (sum(t['valid'] for t in rows)>=2 and set(domains)<=present
                    and opportunities.get('walk',0)>0 and sum(opportunities.get(d,0) for d in TASKS)>0)

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
                save('training-observations',data)
                assert signal_ready(teachers), 'Insufficient complete data or substantial walking/task corrections'
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
                    state = await trainer.save_state(f'mochi_t15_{os.environ["GITHUB_RUN_ID"]}_{update}')
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
                        assert all(v > 1e-7 for v in delta.values()), 'Intended domain shows no measurable weight behavior change'
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
                        report['first_optimizer_physical_probe']={'parent':development[0][0],
                            'updated':early_evaluations[0]['row'],'scope':'Predeclared development scenario, retained in final development comparison.'}
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
            selected = max(report['checkpoints'], key=lambda cp: checkpoint_rank(cp['development'], development[cp['update']]))
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
            report['improvement_goal_met']=bool(report['held_out']['selected']['qualified_complete_successes']==len(cfg['held_out_seeds']) and pp['n']>=2 and pp['mean_step_reduction_fraction']>=.20 and pp['mean_time_reduction_fraction']>=0 and report['held_out']['selected']['falls']<=report['held_out']['parent']['falls'] and report['held_out']['selected']['invalid_contacts']<=report['held_out']['parent']['invalid_contacts'])
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
                run_id, reference) for task in TASKS], 3600, 6, 24000)
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
        report.update(status='completed', phase='Frozen V15 evaluation complete', completed_at=now(),
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
