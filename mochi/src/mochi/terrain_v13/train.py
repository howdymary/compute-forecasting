"""Bounded fresh-data continuation after the completed V12 assessment.

No native gait weights, scene geometry, route, verifiers or V12 controllers
change. Tinker updates the six-domain categorical model's LoRA weights.
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
from ..terrain_v12.policy import decision
from ..terrain_v12.train import summary
from .objective import checkpoint_rank, static_from_training
from .remote import app, collect, evaluate, components
from .services import ContinuationServices

OUT = ROOT / 'artifacts/terrain-v13-training'


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / (name + '.json')
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(target)


async def main():
    import tinker
    from tinker_cookbook.recipes.decisions import decision_choice_datums, sample_decision

    cfg = json.loads((ROOT / 'configs/terrain-v13-training.json').read_text())
    source = Path(os.environ['MOCHI_PARENT_SOURCE'])
    previous = json.loads((source / 'report.json').read_text())
    assessment_path = ROOT / 'docs/terrain-v12-assessment.json'
    assessment = json.loads(assessment_path.read_text())
    assert previous['status'] == 'completed' and previous['held_out_opened'], 'Finish the previous run first'
    assert previous['recovery']['evaluation_run'] == str(cfg['source_run'])
    assert hashlib.sha256(assessment_path.read_bytes()).hexdigest() == cfg['assessment_sha256']
    assert hashlib.sha256((ROOT / cfg['implementation_prompt']).read_bytes()).hexdigest() == cfg['prompt_sha256']
    assert assessment['selected_checkpoint']['checkpoint_id'] == cfg['parent_checkpoint_sha256']
    assert previous['selected_checkpoint']['checkpoint_id'] == cfg['parent_checkpoint_sha256']
    assert not (set(cfg['training_seeds']) & set(cfg['development_seeds'])
                or set(cfg['training_seeds']) & set(cfg['held_out_seeds'])
                or set(cfg['development_seeds']) & set(cfg['held_out_seeds']))
    old_seeds = set(sum([previous['protocol'][k] for k in ['training_seeds', 'development_seeds', 'held_out_seeds']], []))
    assert not old_seeds.intersection(cfg['training_seeds'] + cfg['development_seeds'] + cfg['held_out_seeds'])
    for path, expected in cfg['frozen_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, 'Frozen file changed: ' + path

    paths = json.loads((source / 'checkpoint-paths.json').read_text())
    parent = paths[str(previous['selected_checkpoint']['update'])]['optimizer']
    assert digest(parent) == cfg['parent_checkpoint_sha256']
    run_id = 'mochi-t13-' + os.environ['GITHUB_RUN_ID']
    progress = modal.Dict.from_name('mochi-terrain-v13-progress', create_if_missing=True)
    # Rerunning an interrupted job cannot silently repeat gradients or create
    # the same identities/artifacts. Resume must be explicitly reconciled.
    assert await progress.get.aio(run_id) is None, 'Existing run; inspect durable state before resuming'
    usage = {k: 0 for k in cfg['bounds'] if k != 'modal_concurrency'}
    ledger = modal.Dict.from_name(run_id + '-budget', create_if_missing=True)
    assert await ledger.get.aio('usage') is None, 'Existing reservations require reconciliation'
    lock = asyncio.Lock()
    services = ContinuationServices()
    services.run_id = run_id
    services.actors = {r: run_id + '-' + r for r in ['researcher', 'designer', 'experimenter', 'critic']}
    services.audience, services.private = run_id + '-shared', run_id + '-critic'
    report = {'study': cfg['study'], 'run_id': run_id, 'source_sha': os.getenv('GITHUB_SHA'),
        'created_at': now(), 'status': 'running', 'phase': 'Recall the completed V12 assessment',
        'protocol': cfg, 'protocol_sha256': digest(cfg), 'scope': cfg['scope'],
        'optimizer_updates_completed': 0, 'training_log': [], 'checkpoints': [],
        'held_out_opened': False, 'physics_receipts': [], 'campaign_modal_rollouts_completed': 0,
        'parent_assessment': {'sha256': cfg['assessment_sha256'], 'source_run': cfg['source_run']}}
    report['implementation_prompt'] = {'path': cfg['implementation_prompt'], 'sha256': cfg['prompt_sha256']}

    async def change(kind, amount):
        async with lock:
            value = usage[kind] + amount
            if not 0 <= value <= cfg['bounds'][kind]:
                raise RuntimeError('V13 hard budget ceiling: ' + kind)
            usage[kind] = value
            await ledger.put.aio('usage', dict(usage))

    async def publish():
        report['budget_usage_or_reserved'] = dict(usage)
        report['services'] = services.report()
        save('progress', report)
        await progress.put.aio(run_id, report)
        await progress.put.aio('latest', report)
        print('MOCHI_T13 ' + json.dumps({'phase': report['phase'], 'updates': report['optimizer_updates_completed'],
              'physical_rollouts': report['campaign_modal_rollouts_completed'], 'usage': usage}), flush=True)

    async def write(role, content, private=False):
        await change('past_writes', 1)
        return await services.write(role, content, private)

    async def read(role, rid, allowed=True):
        await change('past_recalls', 1)
        return await services.read(role, rid, allowed)

    async def batch(function, arguments, timeout, rollout_cap, token_cap):
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
                report['physics_receipts'].append({'phase': report['phase'], 'seed': row['seed'],
                    'label': row.get('label'), 'group': row.get('group'), 'task': row.get('task'), 'receipt': receipt})
                if function is collect:
                    save('teacher-' + str(row['seed']), row)
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
            'assessment_sha256': cfg['assessment_sha256'], 'prior_verdict_record': verdict['id'],
            'held_out': previous['held_out'], 'failures': assessment['held_out'],
            'qualification': 'Previous test scenarios are now historical evidence; V13 uses separate unopened final seeds.'})
        observation = await read('researcher', eid)
        await change('exa_searches', 1)
        problems = []
        if any(v['failures'].get('fall', 0) for v in observation['failures'].values()):
            problems.append('humanoid stair ascent descent support transfer stability')
        if any(v['forbidden_contacts'] for v in observation['failures'].values()):
            problems.append('whole body collision avoidance laptop lid manipulation release arm withdrawal')
        await change('inference_tokens', 4000)
        direction = await services.decide('researcher',
            'Choose the most useful research emphasis for the recorded failures. This selects the actual Exa query, not a controller implementation.',
            {'observed_problems': problems, 'historical_failures': {k: v['failures'] for k, v in observation['failures'].items()}},
            ['stair_support', 'whole_body_release', 'coupled_efficiency'], [eid])
        focus = {'stair_support': 'contact aware support transfer and stair stability',
                 'whole_body_release': 'collision aware whole body manipulation and safe withdrawal',
                 'coupled_efficiency': 'joint task completion and arm recovery trajectory optimization'}[direction]
        query = 'robot motion policy research ' + focus + ' ' + ' '.join(problems)
        sources = await services.search(query)
        hid = await write('researcher', {'kind': 'hypothesis', 'experiment_id': run_id,
            'observation_record': eid, 'sources': sources,
            'research_direction': direction,
            'mechanism': 'A successful press may leave an unsafe withdrawal state. Evaluate task and arm withdrawal together; use guarded student visitation to cover states the student actually reaches.',
            'prediction': 'Fresh physical labels can reduce unsafe task choices and excessive recovery cost without changing the native gait network.',
            'supersedes': verdict['id'], 'qualification': 'Testable proposal, not an established performance gain.'})
        hypothesis = await read('designer', hid)
        await change('inference_tokens', 4000)
        allocation = await services.decide('designer',
            'Choose a bounded six-domain training allocation: balanced uses 12 walking and 8 recovery labels per update; recovery_first uses 8 walking and 12 recovery. Every task gets four examples in either case.',
            {'mechanism': hypothesis['mechanism'], 'parent_complete': previous['held_out']['selected']['complete_successes'],
             'parent_n': previous['held_out']['selected']['n'], 'sources': sources['sources']},
            ['balanced', 'recovery_first'], [eid, hid])
        pid = await write('designer', {'kind': 'proposal', 'experiment_id': run_id,
            'hypothesis_record': hid, 'allocation': allocation,
            'frozen_protocol_sha256': digest(cfg), 'controller_changes': 'none'})
        proposal = await read('experimenter', pid)
        counts = {'walk': 12 if proposal['allocation'] == 'balanced' else 8,
                  **{t: 4 for t in TASKS}, 'recovery': 8 if proposal['allocation'] == 'balanced' else 12}
        report['domain_batch_counts'] = counts
        trainer = await services.service.create_training_client_from_state_with_optimizer(parent)
        snapshots[0] = await trainer.save_weights_and_get_sampling_client(kind='snapshot')
        checkpoint_paths['0'] = {'optimizer': parent}
        save('checkpoint-paths', checkpoint_paths)
        async with app.run():
            report['phase'] = 'Guarded student-state data generation on Modal'
            await publish()
            teachers = await batch(collect, [(seed, sampler_payload(snapshots[0]), run_id)
                                   for seed in cfg['training_seeds']], 4500, 37, 24000)
            data = defaultdict(list)
            for teacher in teachers:
                for e in teacher['examples']:
                    data[e['domain']].append((e['observation'], e['action']))
            domains = cfg['training']['domains']
            report['data_audit'] = {d: {'examples': len(data[d]), 'labels': dict(Counter(a for _, a in data[d]))} for d in domains}
            report['guarded_student_sequences_complete'] = sum(t['valid'] for t in teachers)
            report['guard_interventions'] = sum(e['guard_intervened'] for t in teachers for e in t['examples'])
            report['student_label_disagreements'] = {d: sum(max(e['student_distribution'], key=e['student_distribution'].get) != e['action']
                for t in teachers for e in t['examples'] if e['domain'] == d) for d in domains}
            report['static_preference'] = static_from_training(teachers)
            save('training-observations', data)
            assert report['guarded_student_sequences_complete'] >= 2, 'Insufficient physically valid complete data'
            assert all(data[d] for d in domains), 'Missing training domain'
            assert report['student_label_disagreements']['walk'] > 0, 'No measured walking correction to learn'
            assert sum(report['student_label_disagreements'][d] for d in TASKS) > 0, 'No measured task correction to learn'
            datums = {d: decision_choice_datums(services.renderer, [(decision(o), a) for o, a in data[d]]) for d in domains}
            probes = [data[d][0][0] for d in domains]
            initial = None
            report['phase'] = 'Actual Tinker walking, task and recovery post-training'
            await publish()
            for update in range(cfg['training']['updates'] + 1):
                if update and update in durable_updates:
                    state = await trainer.save_state(f'mochi_t13_{os.environ["GITHUB_RUN_ID"]}_{update}')
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

            report['phase'] = 'Fresh development tests for every saved comparison checkpoint'
            await publish()
            bundles = await batch(evaluate, [(seed, 'policy', sampler_payload(snapshots[cp['update']]),
                run_id, 'dev-' + str(cp['update'])) for cp in report['checkpoints']
                for seed in cfg['development_seeds']], 1500, 1, 24000)
            for cp in report['checkpoints']:
                update = cp['update']
                rows = [b['row'] for b in bundles if b['group'] == 'dev-' + str(update)]
                development[update] = rows
                save('checkpoint-' + str(update), rows)
                cp['development'] = summary(rows, cfg)
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
                for label, payload, static in models], 1500, 1, 24000)
            held = {label: [b['row'] for b in bundles if b['label'] == label] for label, _, _ in models}
            for label, rows in held.items():
                save('held-out-' + label, rows)
            report['held_out'] = {label: summary(rows, cfg) for label, rows in held.items()}
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
                run_id, reference) for task in TASKS], 3000, 6, 24000)
            try:
                rid = await write('experimenter', {'kind': 'observation', 'experiment_id': run_id,
                    'optimizer_updates_completed': report['optimizer_updates_completed'],
                    'selected_checkpoint': selected, 'held_out': report['held_out'],
                    'components': [{'task': x['task'], 'results': x['results']} for x in report['component_results']],
                    'supersedes': eid})
                measured = await read('critic', rid)
                await change('inference_tokens', 4000)
                critic_label = await services.decide('critic',
                    'Classify the bounded simulation evidence. Compare parent and selected success first. Additional optimizer steps or altered probabilities are not evidence of better control. A static preference matching the model limits claims of adaptation. Keep small cohorts qualified.',
                    {'final_test_metrics': measured['held_out'], 'selected_update': selected['update'],
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
        report.update(status='completed', phase='Frozen V13 evaluation complete', completed_at=now(),
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
