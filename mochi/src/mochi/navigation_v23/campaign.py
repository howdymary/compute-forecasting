"""Bounded real training, cloud physics and separate memory comparisons."""
import asyncio
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from mochi.integrations import digest, now
from mochi.navigation_v23.engine import ACTIONS, inspect, observation, decision
from mochi.navigation_v23.baselines import tune, conventional, summary
from mochi.navigation_v23.layouts import fingerprint
from mochi.navigation_v23.services import NavigationServices

ROOT = Path('/app')


async def main():
    import tinker
    from tinker_cookbook import model_info, renderers
    from tinker_cookbook.recipes.decisions import DecisionRenderer, decision_choice_datums, sample_decision
    import modal
    trial = modal.Function.from_name("mochi-navigation-v23", "trial")
    volume = modal.Volume.from_name("mochi-navigation-v23-artifacts")
    from mochi.maintenance.checkpoints_by_date import inventory
    cfg = json.loads((ROOT / 'configs/navigation-v23/protocol.json').read_text())
    bounds, run_id = cfg['bounds'], cfg['run_id']
    directory = Path('/artifacts') / run_id
    directory.mkdir(parents=True, exist_ok=True)
    assert not (directory / 'progress.json').exists(), 'Inspect an existing campaign before resuming; never overwrite it'
    frozen = json.loads((ROOT / 'configs/navigation-v23/source-freeze.json').read_text())
    for name, expected in frozen['sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    usage = {k: 0 for k in bounds if k != 'modal_concurrency'}
    usage.update(cfg.get('carried_usage', {}))
    lock, slots = asyncio.Lock(), asyncio.Semaphore(bounds['modal_concurrency'])
    report = {'study': cfg['study'], 'run_id': run_id, 'created_at': now(), 'status': 'running',
        'phase': 'provider setup', 'protocol': cfg, 'source_freeze': frozen,
        'optimizer_updates_completed': 0, 'training_log': [], 'checkpoints': [],
        'training_trials': [], 'development': {}, 'final': {}, 'adaptation': [],
        'physics_receipts': [], 'held_out_opened': False, 'sequence_final_opened': False,
        'native_gait_weights_trained': False, 'privileged_state': True}

    def save(name, value):
        path = directory / (name + '.json')
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(value, indent=2) + '\n')
        temp.replace(path)

    async def charge(kind, amount):
        async with lock:
            assert 0 <= usage[kind] + amount <= bounds[kind], 'Budget ceiling: ' + kind
            usage[kind] += amount
        return usage[kind]

    services = NavigationServices(run_id, directory, charge, volume.commit.aio)

    async def publish():
        report['services'] = services.report()
        report['usage_actual_or_reserved'] = dict(usage)
        save('progress', report)
        await volume.commit.aio()
        print(json.dumps({'phase': report['phase'], 'updates': report['optimizer_updates_completed'],
            'rollouts': usage['physical_rollouts'], 'cpu_hours': usage['simulation_cpu_hours']}), flush=True)

    async def physical(layout, seed, action, selection, ident, memories=None):
        async with slots:
            reserved = 360. / 3600
            await charge('physical_rollouts', 1)
            await charge('simulation_cpu_hours', reserved)
            await charge('modeled_provider_usd', .02)
            await publish()
            row = await trial.remote.aio(layout, seed, action, selection, ident, memories)
            await charge('simulation_cpu_hours', row['receipt']['duration_seconds'] / 3600 - reserved)
            report['physics_receipts'].append({'id': ident, **row['receipt'], 'artifact': row['artifact']})
            await publish()
            return row

    def observed(layout, seed, memories=None):
        w, envelope, obstacles, paths = inspect(layout, seed)
        return observation(w, envelope, obstacles, paths, memories)

    samplers, paths, renderer = {}, {}, None

    async def select(update, obs):
        rendering = renderer.render(decision(obs))
        await charge('inference_input_plus_max_output_tokens', len(rendering.tokens) + 1)
        await charge('modeled_provider_usd', (len(rendering.tokens) + 1) * 1.01 / 1_000_000)
        started = time.perf_counter()
        distribution = await sample_decision(samplers[update], rendering)
        return {'action': max(distribution, key=distribution.get), 'distribution': distribution,
            'checkpoint_id': digest(paths[str(update)]['optimizer']), 'optimizer_updates': update,
            'observation_sha256': digest(obs), 'inference_seconds': time.perf_counter() - started,
            'source': 'Actual Tinker saved navigation LoRA checkpoint'}

    async def evaluate(update, layouts, group):
        async def one(i, layout, seed):
            obs = observed(layout, seed)
            picked = await select(update, obs)
            return await physical(layout, seed, picked['action'], picked, f'{group}-{i}-{seed}-u{update}')
        return await asyncio.gather(*(one(i, l, s) for i, l in enumerate(layouts) for s in cfg['physics_seeds']))

    try:
        assert len(await inventory(tinker.RestClient())) + len(cfg['updates']) + 1 <= 100, 'Checkpoint storage capacity; prior checkpoints are protected'
        await services.setup()
        await charge('modeled_provider_usd', 1.)
        canary = await services.write('critic', {'kind': 'synthetic-private-canary', 'experiment_id': run_id,
            'value': 'MOCHI_PRIVATE_CANARY navigation-v23'}, private=True)
        await services.read('researcher', canary, allowed=False)
        engineering = json.loads((ROOT / 'configs/navigation-v23/engineering-summary.json').read_text())
        failure = await services.write('experimenter', {'kind': 'measured-navigation-observation', 'experiment_id': run_id,
            'observations': engineering, 'qualification': 'Development-only engineering observations; no final layouts opened.'})
        recalled = await services.read('researcher', failure)
        search = await services.search(cfg.get('research_query', 'humanoid navigation footprint swept volume turning clearance motion planning tracking error obstacle inflation'))
        research = await services.write('researcher', {'kind': 'sourced-hypothesis', 'experiment_id': run_id,
            'question': cfg.get('research_question', 'How much clearance is needed before a dynamically executed turn?'), 'sources': search['sources'],
            'hypothesis': cfg.get('research_hypothesis', 'Geometry-aware clearance selection may trade path length against tracking error and contact risk.'),
            'evidence_sha256': digest(recalled)})
        evidence = await services.read('designer', research)
        allocation = await services.decide('designer', 'Choose replay emphasis for the new-layout navigation curriculum.',
            evidence, ['recent_failures', 'balanced_replay'], [research])
        plan_id = await services.write('designer', {'kind': 'training-plan', 'experiment_id': run_id,
            'allocation': allocation, 'source_record': research, 'source_sha256': digest(evidence),
            'constraints': 'Fresh layouts each iteration; fixed controller and navigation verifier; no final evidence.'})
        await services.read('experimenter', plan_id)
        if cfg.get('restore_untrained_parent_from'):
            previous_paths = json.loads((Path('/artifacts') / cfg['restore_untrained_parent_from'] / 'private-checkpoint-paths.json').read_text())
            trainer = await services.service.create_training_client_from_state_with_optimizer(previous_paths['0']['optimizer'])
            report['parent_origin'] = {'untrained_checkpoint_id': digest(previous_paths['0']['optimizer']),
                'qualification': 'The exact untrained parent is restored after the controller repair. The interrupted update is not promoted.'}
        else:
            trainer = await services.service.create_lora_training_client(base_model=cfg['model'], rank=cfg['lora_rank'], seed=231123)
        renderer = DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(cfg['model']), trainer.get_tokenizer()))
        training = json.loads((ROOT / 'configs/navigation-v23/training.json').read_text())
        development = json.loads((ROOT / 'configs/navigation-v23/development.json').read_text())
        datums, probe, initial_distribution = [], None, None

        async def checkpoint(update):
            saved = await trainer.save_state(f'{run_id.replace(chr(45), chr(95))}_{update}')
            paths[str(update)] = {'optimizer': saved.path}
            save('private-checkpoint-paths', paths)
            samplers[update] = await trainer.save_weights_and_get_sampling_client(kind='snapshot')
            entry = {'update': update, 'checkpoint_id': digest(saved.path), 'created_at': now()}
            if probe:
                entry['probe_distribution'] = (await select(update, probe))['distribution']
            report['checkpoints'].append(entry)
            report['phase'] = 'fixed development u' + str(update)
            await publish()
            rows = await evaluate(update, development, 'dev')
            report['development'][str(update)] = {'rows': rows, 'summary': summary(rows)}
            save('development-' + str(update), rows)
            await publish()

        await checkpoint(0)
        for index, layout in enumerate(training):
            update = report['optimizer_updates_completed'] + 1
            report['phase'] = 'new training layout ' + str(index + 1)
            obs = observed(layout, cfg['physics_seeds'][index % 2])
            if probe is None:
                probe = obs
                initial_distribution = (await select(0, probe))['distribution']
                report['parent_probe_distribution'] = initial_distribution
            candidates = await asyncio.gather(*(physical(layout, cfg['physics_seeds'][index % 2], a, {},
                f'train-{index}-{a}') for a in ACTIONS))
            outcomes = {r['action']: r for r in candidates}
            valid = [r for r in candidates if r['qualified']]
            trial_record = {'observation': obs, 'layout_sha256': layout['layout_sha256'], 'outcomes': outcomes,
                'target': max(valid, key=lambda r: r['reward'])['action'] if valid else None}
            report['training_trials'].append(trial_record)
            if not valid:
                trial_record['skip_reason'] = 'No qualified physical candidate; retained as negative training evidence without inventing a supervised label.'
                await publish()
                continue
            generated = decision_choice_datums(renderer, [(decision(obs), trial_record['target'])])
            datums.extend(generated)
            rng = np.random.default_rng(231000 + update)
            indices = rng.integers(0, len(datums), 16).tolist()
            if allocation == 'recent_failures':
                indices[:8] = [len(datums) - 1] * 8
            batch = [datums[i] for i in indices]
            tokens = sum(d.model_input.length for d in batch)
            await charge('training_token_presentations', tokens)
            await charge('modeled_provider_usd', tokens * .737 / 1_000_000)
            await charge('optimizer_updates', 1)
            backward = trainer.forward_backward(batch, loss_fn='cross_entropy')
            optimizer = trainer.optim_step(tinker.AdamParams(learning_rate=1e-4))
            loss = await backward
            await optimizer
            report['optimizer_updates_completed'] = update
            report['training_log'].append({'update': update, 'fresh_layout_sha256': layout['layout_sha256'],
                'target': trial_record['target'], 'batch_indices_sha256': digest(indices), 'tokens': tokens,
                'forward_backward_completed': True, 'optimizer_completed': True, 'metrics': loss.metrics, 'at': now()})
            await publish()
            if update in cfg['updates']:
                await checkpoint(update)
                changed = report['checkpoints'][-1]['probe_distribution']
                report['maximum_probe_probability_change'] = max(abs(changed[a] - initial_distribution[a]) for a in ACTIONS)
                assert report['maximum_probe_probability_change'] > 1e-7, 'Optimizer updates did not change the intended policy probe'
            if update in [4, cfg['updates'][-1]]:
                record = await services.write('experimenter', {'kind': 'training-results', 'experiment_id': run_id,
                    'optimizer_updates': update, 'targets': dict(Counter(t['target'] for t in report['training_trials'])),
                    'qualified_candidate_counts': [sum(r['qualified'] for r in t['outcomes'].values()) for t in report['training_trials']],
                    'result_sha256': digest(report['training_log'])})
                context = await services.read('critic', record)
                verdict = await services.decide('critic', 'Qualify this measured navigation training result.', context,
                    ['limited_training_evidence', 'no_generalization_claim'], [record])
                rid = await services.write('critic', {'kind': 'qualified-verdict', 'experiment_id': run_id,
                    'verdict': verdict, 'result_record': record, 'qualification': 'Development evidence only; final layouts remain unopened.'})
                await services.read('researcher', rid)
            if update >= cfg['updates'][-1]:
                break
        # If the bounded dataset has unlabelled cases, save the actual endpoint
        # rather than pretending the requested number of updates was reached.
        actual = report['optimizer_updates_completed']
        if actual not in samplers:
            await checkpoint(actual)
            changed = report['checkpoints'][-1]['probe_distribution']
            report['maximum_probe_probability_change'] = max(abs(changed[a] - initial_distribution[a]) for a in ACTIONS)
            assert report['maximum_probe_probability_change'] > 1e-7
        selected = max(report['checkpoints'], key=lambda cp: (
            report['development'][str(cp['update'])]['summary']['qualified'],
            -(report['development'][str(cp['update'])]['summary']['qualified_mean_steps'] or float('inf')),
            -cp['update']))
        report['selected_checkpoint'] = selected
        baselines = tune(report['training_trials'])
        report['baselines'] = baselines
        training_rid = await services.write('experimenter', {'kind': 'frozen-training-memory', 'experiment_id': run_id,
            'qualified_training_action_counts': dict(Counter(t['target'] for t in report['training_trials'])),
            'training_baselines': baselines,
            'qualification': 'Training layouts only. Margin feasibility depends on geometry; no final outcomes are included.'})
        frozen_memory = await services.read('designer', training_rid)
        memory_context = [frozen_memory]
        report['phase'] = 'selection frozen before final layouts'
        selection_freeze = {'selected_checkpoint': selected, 'source_freeze': frozen,
            'split_manifest': json.loads((ROOT / 'configs/navigation-v23/split-manifest.json').read_text()),
            'at': now(), 'frozen_memory_record_id': training_rid, 'frozen_memory_sha256': digest(memory_context),
            'memory_training_records': [r['id'] for r in services.records.values() if r['audience'] == services.audience]}
        save('selection-freeze', selection_freeze)
        await publish()
        final_file = directory / 'sealed/final_navigation.json'
        final = json.loads(final_file.read_text())
        expected = selection_freeze['split_manifest']['final_navigation']['sha256']
        assert fingerprint(final) == expected
        report['held_out_opened'] = True
        report['phase'] = 'unopened-layout primary comparisons'
        await publish()
        u = selected['update']
        report['final']['parent'] = await evaluate(0, final, 'final-parent')
        report['final']['selected'] = await evaluate(u, final, 'final-selected')
        for label in ['planner', 'conventional', 'fixed']:
            async def baseline(i, layout, seed):
                obs = observed(layout, seed)
                a = 'planner' if label == 'planner' else baselines['fixed'] if label == 'fixed' else conventional(obs, baselines['contextual_tuning'])
                return await physical(layout, seed, a, {}, f'final-{label}-{i}-{seed}')
            report['final'][label] = await asyncio.gather(*(baseline(i, l, s) for i, l in enumerate(final) for s in cfg['physics_seeds']))
            await publish()
        report['phase'] = 'frozen training-memory comparison'
        async def memory_case(i, layout, seed):
            obs = observed(layout, seed, memory_context)
            picked = await select(u, obs)
            return await physical(layout, seed, picked['action'], picked, f'final-memory-{i}-{seed}', memory_context)
        report['final']['selected_memory_enabled'] = await asyncio.gather(*(memory_case(i, l, s) for i, l in enumerate(final) for s in cfg['physics_seeds']))
        report['phase'] = 'per-layout isolated three-attempt adaptation'
        # Each case has separate ACL audiences. A failed attempt's exact source
        # is accessible only to that case's reader. No global final memory writes.
        for i, layout in enumerate(final):
            for name, update in [('parent', 0), ('selected', u)]:
                for enabled in [False, True]:
                    seed = cfg['physics_seeds'][0]
                    firsts = report['final']['selected_memory_enabled'] if name == 'selected' and enabled else report['final'][name]
                    first = next(r for r in firsts if r['layout_sha256'] == layout['layout_sha256'] and r['seed'] == seed)
                    if name == 'parent' and enabled:
                        obs = observed(layout, seed, memory_context)
                        pick = await select(update, obs)
                        first = await physical(layout, seed, pick['action'], pick, f'adapt-{name}-{i}-on-0', memory_context)
                    attempts = [first]
                    local_context = list(memory_context) if enabled else []
                    shared = services.audience
                    shared_actors = dict(services.actors)
                    case_audience = f'{run_id}-c{i}-{name[:1]}-{int(enabled)}'
                    if enabled and not first['qualified']:
                        case_actors = {role: case_audience + '-' + role[0] for role in shared_actors}
                        for role, actor in case_actors.items():
                            await services.request('PUT', '/identities/' + actor,
                                {'traits': {'project': run_id, 'case': str(i), 'role': role}})
                        await services.request('PUT', '/audiences/' + case_audience,
                            {'kind': 'fixed', 'name': 'Isolated navigation evaluation case', 'identities': list(case_actors.values())})
                        services.actors = case_actors
                    for retry in range(1, cfg['retry_budget']):
                        if attempts[-1]['qualified']:
                            break
                        previous = attempts[-1]
                        # Both conditions retain the immediately observed last
                        # failure in working context. Memory-off is not amnesia.
                        local_context.append({'kind': 'working-context-failure', 'action': previous['action'],
                            'failure': previous['failure'], 'checks': previous['checks']})
                        if enabled:
                            services.audience = case_audience
                            rid = await services.write('experimenter', {'kind': 'case-local-failure', 'experiment_id': run_id,
                                'layout_sha256': layout['layout_sha256'], 'attempt': retry - 1,
                                'action': previous['action'], 'failure': previous['failure'], 'checks': previous['checks'],
                                'qualification': 'This evaluation case only; inaccessible to other cases.'})
                            services.actors = shared_actors
                            await services.read('researcher', rid, allowed=False)
                            services.actors = case_actors
                            local_context.append(await services.read('designer', rid))
                            services.audience = shared
                        obs = observed(layout, seed, local_context)
                        picked = await select(update, obs)
                        row = await physical(layout, seed, picked['action'], picked,
                            f'adapt-{name}-{i}-{int(enabled)}-{retry}', local_context)
                        attempts.append(row)
                    services.audience = shared
                    services.actors = shared_actors
                    report['adaptation'].append({'layout_sha256': layout['layout_sha256'], 'model': name,
                        'memory_enabled': enabled, 'attempts': attempts,
                        'success_within_budget': any(r['qualified'] for r in attempts)})
                    await publish()
        report['final_summaries'] = {k: summary(v) for k, v in report['final'].items()}
        gate = report['development'][str(u)]['summary']
        report['phase_b_gate_met'] = bool(gate['qualified'] / gate['n'] >= cfg['gate']['development_first_attempt_fraction']
            and gate['falls'] == 0 and gate['contacts'] == 0)
        report['sequence_final_opened'] = False
        report['phase_b_status'] = 'requires separate object-relative task validation and a bounded extension' if report['phase_b_gate_met'] else 'navigation reliability gate not met; four-task extension not launched'
        report['status'], report['phase'] = 'completed', 'navigation evaluation complete'
        record = await services.write('experimenter', {'kind': 'final-results', 'experiment_id': run_id,
            'summaries': report['final_summaries'], 'selected_update': u, 'phase_b_gate_met': report['phase_b_gate_met'],
            'qualification': 'Navigation on eight unseen layouts. Exact geometry is privileged. Native gait weights unchanged.'})
        ctx = await services.read('critic', record)
        verdict = await services.decide('critic', 'Assess this bounded final navigation study without claiming universal generalization.',
            ctx, ['limited_generalization_evidence', 'improvement_not_established'], [record])
        rid = await services.write('critic', {'kind': 'final-qualified-verdict', 'experiment_id': run_id,
            'result_record': record, 'verdict': verdict, 'qualification': 'Numerical comparisons determine gains; this verbal judgment is not a success verifier.'})
        await services.read('researcher', rid)
        await publish()
        return report
    except BaseException as error:
        import os
        message = str(error)
        for key in ['TINKER_API_KEY', 'EXA_API_KEY', 'PAST_API_KEY']:
            if os.environ.get(key):
                message = message.replace(os.environ[key], '[redacted]')
        report.update(status='incomplete', error_type=type(error).__name__, error=message[:400])
        await publish()
        raise
    finally:
        await services.http.aclose()
