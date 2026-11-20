"""Bounded Tinker post-training with completion-gated, step-first targets."""
import asyncio
from collections import Counter, defaultdict
import hashlib
import json
import os

import modal
import numpy as np

from ..curriculum.world import ROOT
from ..integrations import digest, now
from ..maintenance.checkpoints_by_date import inventory
from ..smooth_v16.objective import static_from_training
from ..smooth_v16.parent import load_parent
from ..smooth_v17.finalize_memory import ReviewServices
from ..terrain_v12.learning_remote import sampler_payload
from .objective import paired, select_checkpoint, summary, valid_branch
from .policy import decision
from .remote import app, collect, evaluate, evaluate_pair


OUT = ROOT / 'artifacts/paperfree-v19-training'


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / (name + '.json')
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


class Services(ReviewServices):
    def journal(self):
        save(self.run_id + '-memory-journal', {'pending': self.pending, 'ready': self.records})


async def main():
    import tinker
    from tinker_cookbook.recipes.decisions import decision_choice_datums, sample_decision
    cfg = json.loads((ROOT / 'configs/paperfree-v19-training.json').read_text())
    for path, expected in cfg['frozen_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    _, parent, parent_info = await load_parent(cfg)
    run_id = 'mochi-p19-' + os.environ['GITHUB_RUN_ID']
    progress = modal.Dict.from_name('mochi-paperfree-v19-progress', create_if_missing=True)
    assert await progress.get.aio(run_id) is None, 'Inspect an existing campaign before any resume'
    ledger = modal.Dict.from_name(run_id + '-budget', create_if_missing=True)
    usage = {k: 0 for k in cfg['bounds'] if k != 'modal_concurrency'}
    usage.update(cfg['engineering_usage'])
    await ledger.put.aio('usage', dict(usage))
    services = Services()
    services.run_id = run_id
    services.actors = {role: run_id + '-' + role for role in ['researcher', 'designer', 'experimenter', 'critic']}
    services.audience, services.private = run_id + '-shared', run_id + '-critic'
    report = {
        'study': cfg['study'], 'run_id': run_id, 'source_sha': os.environ['GITHUB_SHA'],
        'created_at': now(), 'protocol': cfg, 'protocol_sha256': digest(cfg),
        'status': 'running', 'phase': 'Validate source, parent and provider access',
        'scope': cfg['scope'], 'optimizer_updates_completed': 0, 'training_log': [],
        'checkpoints': [], 'physics_receipts': [], 'campaign_modal_rollouts_completed': 0,
        'held_out_opened': False, 'parent_selection': parent_info,
    }
    lock, publish_lock = asyncio.Lock(), asyncio.Lock()
    condition = asyncio.Condition(lock)
    slots = asyncio.Semaphore(cfg['bounds']['modal_concurrency'])
    reservations = 0

    async def change(kind, n):
        async with lock:
            assert 0 <= usage[kind] + n <= cfg['bounds'][kind], 'Budget limit: ' + kind
            usage[kind] += n
            await ledger.put.aio('usage', dict(usage))

    async def publish():
        async with publish_lock:
            report['services'] = services.report()
            report['budget_usage_or_reserved'] = dict(usage)
            save('progress', report)
            await progress.put.aio(run_id, report)
            await progress.put.aio('latest', report)
            print('MOCHI_PAPERFREE_V19 ' + json.dumps({
                'phase': report['phase'], 'updates': report['optimizer_updates_completed'], 'usage': usage}), flush=True)

    async def write(role, value, private=False):
        assert len(json.dumps(value)) < 7000
        await change('past_writes', 1)
        result = await services.write(role, value, private)
        await publish()
        return result

    async def read(role, rid, allowed=True):
        await change('past_recalls', 1)
        result = await services.read(role, rid, allowed)
        await publish()
        return result

    async def batch(function, args, tag, timeout, cap, token_cap):
        nonlocal reservations

        async def one(arg):
            nonlocal reservations
            async with slots:
                reserved = {'physical_rollouts': cap, 'simulation_cpu_hours': timeout / 3600., 'inference_tokens': token_cap}
                async with condition:
                    while any(usage[k] + v > cfg['bounds'][k] for k, v in reserved.items()):
                        if reservations == 0:
                            raise RuntimeError('No remaining resource reservation fits')
                        await condition.wait()
                    reservations += 1
                    for k, v in reserved.items():
                        usage[k] += v
                    await ledger.put.aio('usage', dict(usage))
                try:
                    answer = await function.remote.aio(*arg)
                except BaseException:
                    async with condition:
                        reservations -= 1
                        condition.notify_all()
                    raise
                r = answer['receipt']
                actual = {'physical_rollouts': r['physical_rollouts'],
                    'simulation_cpu_hours': r['duration_seconds'] / 3600.,
                    'inference_tokens': r.get('inference_input_plus_max_output_tokens', 0)}
                async with condition:
                    for k, v in actual.items():
                        usage[k] += v - reserved[k]
                        assert usage[k] <= cfg['bounds'][k]
                    reservations -= 1
                    await ledger.put.aio('usage', dict(usage))
                    condition.notify_all()
                report['physics_receipts'].append({'phase': report['phase'], 'seed': answer['seed'], 'receipt': r})
                report['campaign_modal_rollouts_completed'] += r['physical_rollouts']
                save(tag + '-' + str(answer['seed']), answer)
                await publish()
                return answer

        return await asyncio.gather(*(one(arg) for arg in args))

    paths, samplers, development = {}, {}, {}
    rng = np.random.default_rng(cfg['training']['seed'])
    try:
        assert len(await inventory(tinker.RestClient())) + 4 < 100, 'Checkpoint capacity; no deletion is authorized'
        await services.setup()
        await publish()
        await change('exa_searches', 1)
        sources = await services.search('humanoid locomotion reduce corrective footsteps turning command tracking foot clearance whole body contact planning')
        research = await write('researcher', {
            'kind': 'hypothesis', 'experiment_id': run_id, 'sources': sources['sources'],
            'observed_change': 'The paper and forced twelve-footplacement crossing were removed. Compare step-efficient flat commands without sacrificing foot lift or valid four-task completion.',
            'engineering_evidence': cfg['engineering_evidence'],
        })
        context = await read('designer', research)
        await change('inference_tokens', 3000)
        allocation = await services.decide('designer',
            'Choose additional walking examples or a balanced six-domain batch. The step-first score and safety gates are frozen.',
            context, ['walking_priority', 'balanced'], [research])
        plan = await write('designer', {'kind': 'experiment-plan', 'experiment_id': run_id,
            'allocation': allocation, 'reward': cfg['reward'],
            'qualification': 'Valid full completion first, then all measured step attempts. No positive label for a failed or low-clearance branch.'})
        await read('experimenter', plan)
        trainer = await services.service.create_training_client_from_state_with_optimizer(parent)
        samplers[0] = await trainer.save_weights_and_get_sampling_client(kind='snapshot')
        paths['0'] = {'optimizer': parent}
        save('checkpoint-paths', paths)
        async with app.run():
            report['phase'] = 'Verify the paper-free reference before training'
            await publish()
            reference = (await batch(evaluate,
                [(cfg['preflight_seed'], [('fixed', None, None)], run_id, 'preflight', cfg)],
                'preflight', 2400, 1, 0))[0]['rows']['fixed']
            report['preflight'] = reference
            assert reference['qualified_complete'], 'Repair physical feasibility before training'
            report['phase'] = 'New-scene parent baseline and measured teaching branches'
            await publish()
            baseline = await batch(evaluate,
                [(s, [('policy', sampler_payload(samplers[0]), None)], run_id, 'dev-0', cfg) for s in cfg['development_seeds']],
                'dev-0', 2400, 1, 30000)
            development[0] = [r['rows']['policy'] for r in baseline]
            save('checkpoint-0', development[0])
            report['parent_baseline'] = summary(development[0], cfg)
            await publish()
            teachers = await batch(collect,
                [(s, sampler_payload(samplers[0]), run_id, cfg) for s in cfg['training_seeds']],
                'teacher', 5400, 35, 30000)
            assert all(t['valid'] for t in teachers), 'Both measured teaching sequences must satisfy all gates'
            data = defaultdict(list)
            for teacher in teachers:
                for e in teacher['examples']:
                    data[e['domain']].append((e['observation'], e['action']))
            domains = cfg['training']['domains']
            assert all(data[d] for d in domains)
            informative_walk = [t for teacher in teachers for t in teacher['trials'] if t['domain'] == 'walk'
                and len({r['steps']['attempts'] for r in t['outcomes'] if valid_branch(r, 'walk')}) > 1]
            assert informative_walk, 'Walking options must have different measured step costs before training'
            report['data_audit'] = {d: {'examples': len(data[d]), 'labels': dict(Counter(a for _, a in data[d]))} for d in domains}
            report['static_preference'] = static_from_training(teachers)
            report['informative_walking_trials'] = len(informative_walk)
            save('training-observations', data)
            result = await write('experimenter', {'kind': 'training-observations', 'experiment_id': run_id,
                'data_audit': report['data_audit'], 'informative_walking_trials': len(informative_walk),
                'data_sha256': digest(data), 'qualification': 'Two completed guarded sequences; labels maximize measured step reward among valid matched branches.'})
            await read('critic', result)
            datums = {d: decision_choice_datums(services.renderer, [(decision(o), a) for o, a in data[d]]) for d in domains}
            counts = {'walk': 20 if allocation == 'walking_priority' else 12, 'recovery': 8,
                      'alarm': 4, 'drawer': 4, 'laptop': 4, 'globe': 4}
            probes = {d: min([e for t in teachers for e in t['examples'] if e['domain'] == d],
                key=lambda e: max(e['student_distribution'].values()))['observation'] for d in domains}
            initial = None
            report['phase'] = 'Actual six-domain Tinker supervised post-training'
            await publish()
            for update in range(cfg['training']['updates'] + 1):
                if update in cfg['training']['checkpoints']:
                    if update:
                        saved = await trainer.save_state(f'mochi_paperfree_v19_{os.environ["GITHUB_RUN_ID"]}_{update}')
                        paths[str(update)] = {'optimizer': saved.path, 'rng_state': rng.bit_generator.state}
                        save('checkpoint-paths', paths)
                        samplers[update] = await trainer.save_weights_and_get_sampling_client(kind='snapshot')
                    distributions = {}
                    for domain, obs in probes.items():
                        rendered = services.renderer.render(decision(obs))
                        await change('inference_tokens', len(rendered.tokens) + 1)
                        distributions[domain] = await sample_decision(samplers[update], rendered)
                    if initial is None:
                        initial = distributions
                    if update == 1:
                        report['first_optimizer_probability_change'] = {
                            d: max(abs(v - initial[d][a]) for a, v in dist.items()) for d, dist in distributions.items()}
                        assert max(report['first_optimizer_probability_change'].values()) > 1e-7
                    report['checkpoints'].append({'update': update,
                        'cumulative_updates': parent_info['cumulative_updates'] + update,
                        'checkpoint_id': digest(paths[str(update)]['optimizer']),
                        'probe_distributions': distributions, 'development': None})
                    await publish()
                if update == cfg['training']['updates']:
                    break
                indices = {d: [int(i) for i in rng.choice(len(datums[d]), counts[d], replace=True)] for d in domains}
                tokens = sum(datums[d][i].model_input.length for d in domains for i in indices[d])
                await change('training_token_presentations', tokens)
                await change('optimizer_updates', 1)
                backward = [(d, trainer.forward_backward([datums[d][i] for i in indices[d]], loss_fn='cross_entropy')) for d in domains]
                optimizer = trainer.optim_step(tinker.AdamParams(learning_rate=cfg['training']['learning_rate']))
                losses = {d: (await future).metrics for d, future in backward}
                await optimizer
                report['optimizer_updates_completed'] = update + 1
                report['training_log'].append({'update': update + 1, 'domain_loss_metrics': losses,
                    'domain_counts': counts, 'tokens': tokens, 'batch_sha256': digest(indices),
                    'optimizer_completed': True, 'forward_backward_completed': True, 'at': now()})
                await publish()
            report['phase'] = 'Matched development selection by qualified completion and fewest steps'
            await publish()
            for cp in report['checkpoints']:
                u = cp['update']
                if u:
                    answers = await batch(evaluate,
                        [(s, [('policy', sampler_payload(samplers[u]), None)], run_id, 'dev-' + str(u), cfg) for s in cfg['development_seeds']],
                        'dev-' + str(u), 2400, 1, 30000)
                    development[u] = [a['rows']['policy'] for a in answers]
                    save('checkpoint-' + str(u), development[u])
                cp['development'] = summary(development[u], cfg)
                await publish()
            selected = select_checkpoint(report['checkpoints'])
            report['selected_checkpoint'] = selected
            save('selection-freeze', report)
            report['held_out_opened'] = True
            report['phase'] = 'Fresh paired tests and fixed/static controls'
            await publish()
            pairs = await batch(evaluate_pair,
                [(s, [('parent', sampler_payload(samplers[0]), None),
                      ('selected', sampler_payload(samplers[selected['update']]), None)], run_id, 'held-out', cfg) for s in cfg['held_out_seeds']],
                'held-out', 3600, 2, 60000)
            controls = await batch(evaluate_pair,
                [(s, [('fixed', None, None), ('static', None, report['static_preference'])], run_id, 'held-out-controls', cfg) for s in cfg['control_seeds']],
                'held-out-controls', 3600, 2, 0)
            held = {label: [a['rows'][label] for a in (pairs if label in ['parent', 'selected'] else controls)]
                    for label in ['parent', 'selected', 'fixed', 'static']}
            for label, rows in held.items():
                save('held-out-' + label, rows)
            report['held_out'] = {label: summary(rows, cfg) for label, rows in held.items()}
            report['paired_held_out'] = paired(held['parent'], held['selected'])
            matched = report['paired_held_out']
            report['numerical_goal_met'] = bool(report['held_out']['selected']['qualified_complete_successes'] == 4
                and matched['n'] >= 2 and matched['mean_step_reduction_fraction'] >= .10
                and matched['mean_time_reduction_fraction'] >= 0)
            report['improvement_goal_met'] = report['numerical_goal_met'] and selected['update'] > 0
            report['phase'] = 'Source-verified final review'
            await publish()
            result = await write('experimenter', {'kind': 'final-observation', 'experiment_id': run_id,
                'selected_update': selected['update'], 'optimizer_updates': report['optimizer_updates_completed'],
                'qualified': {label: s['qualified_complete_successes'] for label, s in report['held_out'].items()},
                'paired': matched, 'goal_met': report['improvement_goal_met']})
            evidence = await read('critic', result)
            await change('inference_tokens', 5000)
            verdict = await services.decide('critic', 'Do the measurements establish a safe full-route step reduction?',
                evidence, ['qualified_step_improvement', 'reject_improvement_claim'], [result])
            conclusion = await write('critic', {'kind': 'conclusion', 'experiment_id': run_id,
                'model_verdict': verdict, 'measured_goal_met': report['improvement_goal_met'],
                'qualification': 'Deterministic measurements govern. Scene removal is shared engineering; Tinker trains selector weights, not native gait.'})
            await read('researcher', conclusion)
            canary = await write('critic', {'kind': 'isolation-test', 'canary': 'MOCHI_PRIVATE_CANARY'}, True)
            await read('designer', canary, False)
            report['status'], report['phase'], report['completed_at'] = 'completed', 'Completed bounded paper-free study', now()
            await publish()
            save('report', report)
    except BaseException as exc:
        report.update(status='incomplete', error_type=type(exc).__name__, error=str(exc))
        await publish()
        save('incomplete', report)
        raise
    finally:
        await services.http.aclose()


if __name__ == '__main__':
    asyncio.run(main())
