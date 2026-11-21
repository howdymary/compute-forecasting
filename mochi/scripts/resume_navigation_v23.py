"""Resume only the interrupted adaptation tail, using immutable saved states."""
import json
from pathlib import Path

import modal

from mochi.navigation_v23.remote import image as frozen_image, existing_secrets

ROOT = Path(__file__).resolve().parents[1]
app = modal.App('mochi-navigation-v23-recovery')
volume = modal.Volume.from_name('mochi-navigation-v23-artifacts')
image = frozen_image.add_local_file(Path(__file__), '/app/resume_navigation_v23.py', copy=True)


@app.function(image=image, secrets=existing_secrets, serialized=True, cpu=1, memory=4096,
    timeout=21600, max_containers=1, retries=0, volumes={'/artifacts': volume})
async def resume(run, continuation):
    import asyncio
    import copy
    import hashlib
    import time
    import tinker
    from tinker_cookbook import model_info, renderers
    from tinker_cookbook.recipes.decisions import DecisionRenderer, sample_decision
    from mochi.integrations import digest, now
    from mochi.navigation_v23.engine import inspect, observation, decision
    from mochi.navigation_v23.baselines import summary
    from mochi.navigation_v23.layouts import fingerprint
    from mochi.navigation_v23.services import NavigationServices
    directory = Path('/artifacts') / run
    original_bytes = (directory / 'progress.json').read_bytes()
    report = json.loads(original_bytes)
    assert report['status'] == 'incomplete' and report['error_type'] in ['CancelledError', 'AssertionError', 'BadRequestError']
    assert report['optimizer_updates_completed'] == 15 and report['held_out_opened']
    assert len(report['final']) == 6 and len(report['adaptation']) == 9
    frozen_fields = ['source_freeze', 'protocol', 'checkpoints', 'training_log', 'training_trials',
        'development', 'selected_checkpoint', 'baselines', 'final']
    frozen = digest({k: report[k] for k in frozen_fields})
    for name, expected in report['source_freeze']['sha256'].items():
        assert hashlib.sha256((Path('/app') / name).read_bytes()).hexdigest() == expected, name
    archive = directory / 'interruptions'
    archive.mkdir(exist_ok=True)
    original_sha = hashlib.sha256(original_bytes).hexdigest()
    saved_original = archive / ('adaptation-' + original_sha + '.json')
    if saved_original.exists():
        assert saved_original.read_bytes() == original_bytes
    else:
        saved_original.write_bytes(original_bytes)
    journal_bytes = (directory / 'memory-journal.json').read_bytes()
    (archive / ('memory-' + hashlib.sha256(journal_bytes).hexdigest() + '.json')).write_bytes(journal_bytes)
    journal = json.loads(journal_bytes)
    assert not journal['pending']
    marker = directory / ('continuation-' + continuation + '.json')
    assert not marker.exists(), 'Inspect an existing continuation; never restart training'
    provenance = {'id': continuation, 'at': now(), 'original_status': report['status'],
        'original_error_type': report['error_type'], 'original_progress_sha256': original_sha,
        'frozen_numerical_fields_sha256': frozen,
        'script_sha256': hashlib.sha256(Path('/app/resume_navigation_v23.py').read_bytes()).hexdigest(),
        'optimizer_updates_added': 0, 'recovered_completed_physical_inputs': [], 'status': 'running'}
    marker.write_text(json.dumps(provenance, indent=2) + '\n')
    report.setdefault('continuations', []).append(provenance)
    report.update(status='running', phase='Resume isolated adaptation from saved artifacts')
    report.pop('error', None)
    report.pop('error_type', None)
    usage = copy.deepcopy(report['usage_actual_or_reserved'])
    cfg, bounds = report['protocol'], report['protocol']['bounds']
    lock = asyncio.Lock()

    async def persist_usage():
        report['usage_actual_or_reserved'] = copy.deepcopy(usage)
        temp = directory / 'progress.resume.tmp'
        temp.write_text(json.dumps(report, indent=2) + '\n')
        temp.replace(directory / 'progress.json')
        await volume.commit.aio()

    async def charge(kind, amount):
        async with lock:
            assert 0 <= usage[kind] + amount <= bounds[kind], 'Original budget ceiling: ' + kind
            usage[kind] += amount
            await persist_usage()

    services = NavigationServices(run, directory, charge, volume.commit.aio)
    services.records, services.pending = journal['records'], journal['pending']
    # Reads append to the live report but the old client does not immediately
    # journal them. Merge preserved snapshots instead of losing the last real
    # frozen-memory recall when restoring the ingestion journal.
    snapshots = [report] + [json.loads(p.read_text()) for p in archive.glob('adaptation-*.json')]
    assert all(digest({k: snapshot[k] for k in frozen_fields}) == frozen for snapshot in snapshots)
    for key in ['reads', 'calls', 'sources', 'decisions']:
        rows = [*journal[key], *(row for snapshot in snapshots for row in snapshot['services'][key])]
        unique = {digest(row): copy.deepcopy(row) for row in rows}
        setattr(services, key, sorted(unique.values(), key=lambda row: row.get('at', '')))
    base_actors = dict(services.actors)
    shared = services.audience
    async def publish():
        assert digest({k: report[k] for k in frozen_fields}) == frozen, 'Frozen comparison changed'
        report['services'] = services.report()
        marker.write_text(json.dumps(provenance, indent=2) + '\n')
        await persist_usage()
        print(json.dumps({'status': report['status'], 'phase': report['phase'],
            'completed_cases': len(report['adaptation']), 'physics_receipts': len(report['physics_receipts'])}), flush=True)

    def observed(layout, seed, memories):
        w, envelope, obstacles, paths = inspect(layout, seed)
        return observation(w, envelope, obstacles, paths, memories)

    try:
        await publish()
        # Recover the child that finished after its caller was cancelled. It
        # already consumed a reserved rollout; it must not be run or billed twice.
        known = {r['id'] for r in report['physics_receipts']}
        for p in sorted((directory / 'physics').glob('*.summary.json')):
            ident = p.name.removesuffix('.summary.json')
            if ident in known:
                continue
            row = json.loads(p.read_text())
            for entry, key in [(row['artifact'], 'path'), (row['public_recording'], 'path')]:
                payload = (Path('/artifacts') / entry[key]).read_bytes()
                assert hashlib.sha256(payload).hexdigest() == entry['sha256']
            report['physics_receipts'].append({'id': ident, **row['receipt'], 'artifact': row['artifact']})
            await charge('simulation_cpu_hours', row['receipt']['duration_seconds']/3600 - .1)
            provenance['recovered_completed_physical_inputs'].append({'id': ident,
                'summary_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'new_physical_execution': False})
        assert usage['physical_rollouts'] == cfg['carried_usage']['physical_rollouts'] + len(report['physics_receipts'])
        selection = json.loads((directory / 'selection-freeze.json').read_text())
        rid = selection['frozen_memory_record_id']
        assert any(r['record_id'] == rid and r['source_id_verified'] and r['at'] <= selection['at'] for r in services.reads)
        memory_context = [services.records[rid]['payload']['content']]
        assert digest(memory_context) == selection['frozen_memory_sha256']
        final = json.loads((directory / 'sealed/final_navigation.json').read_text())
        assert fingerprint(final) == selection['split_manifest']['final_navigation']['sha256']
        paths = json.loads((directory / 'private-checkpoint-paths.json').read_text())
        selected = report['selected_checkpoint']['update']
        services.service = tinker.ServiceClient(display_name=run + '-adaptation-resume')
        services.sampler = await services.service.create_sampling_client(base_model=cfg['model'])
        services.renderer = DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(cfg['model']), services.sampler.get_tokenizer()))
        samplers = {}
        for u in sorted(set([0, selected])):
            restored = await services.service.create_training_client_from_state(paths[str(u)]['optimizer'])
            samplers[u] = await restored.save_weights_and_get_sampling_client(kind='snapshot')
        provenance['sampling_restore'] = 'Restored the original optimizer checkpoint weights and exported sampler snapshots; zero optimizer updates.'
        renderer = DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(cfg['model']), samplers[0].get_tokenizer()))
        trial = modal.Function.from_name('mochi-navigation-v23', 'trial')
        cached = {p.name.removesuffix('.summary.json'): json.loads(p.read_text())
            for p in (directory / 'physics').glob('*.summary.json')}

        async def select_and_run(layout, seed, update, memories, ident):
            obs = observed(layout, seed, memories)
            if ident in cached:
                row = cached[ident]
                assert row['selection']['observation_sha256'] == digest(obs)
                assert row['selection']['checkpoint_id'] == digest(paths[str(update)]['optimizer'])
                return row
            rendering = renderer.render(decision(obs))
            await charge('inference_input_plus_max_output_tokens', len(rendering.tokens)+1)
            await charge('modeled_provider_usd', (len(rendering.tokens)+1)*1.01/1_000_000)
            started = time.perf_counter()
            distribution = await sample_decision(samplers[update], rendering)
            picked = {'action': max(distribution, key=distribution.get), 'distribution': distribution,
                'checkpoint_id': digest(paths[str(update)]['optimizer']), 'optimizer_updates': update,
                'observation_sha256': digest(obs), 'inference_seconds': time.perf_counter()-started,
                'source': 'Actual Tinker saved navigation LoRA checkpoint'}
            await charge('physical_rollouts', 1)
            await charge('simulation_cpu_hours', .1)
            await charge('modeled_provider_usd', .02)
            await publish()
            row = await trial.remote.aio(layout, seed, picked['action'], picked, ident, memories)
            await charge('simulation_cpu_hours', row['receipt']['duration_seconds']/3600-.1)
            report['physics_receipts'].append({'id': ident, **row['receipt'], 'artifact': row['artifact']})
            cached[ident] = row
            await publish()
            return row

        done = {(r['layout_sha256'], r['model'], r['memory_enabled']) for r in report['adaptation']}
        for i, layout in enumerate(final):
            for name, update in [('parent', 0), ('selected', selected)]:
                for enabled in [False, True]:
                    if (layout['layout_sha256'], name, enabled) in done:
                        continue
                    seed = cfg['physics_seeds'][0]
                    firsts = report['final']['selected_memory_enabled'] if name == 'selected' and enabled else report['final'][name]
                    first = next(r for r in firsts if r['layout_sha256'] == layout['layout_sha256'] and r['seed'] == seed)
                    if name == 'parent' and enabled:
                        first = await select_and_run(layout, seed, update, memory_context, f'adapt-{name}-{i}-on-0')
                    attempts = [first]
                    local_context = copy.deepcopy(memory_context) if enabled else []
                    case_audience = f'{run}-c{i}-{name[:1]}-{int(enabled)}'
                    if enabled and not first['qualified']:
                        case_actors = {role: case_audience + '-' + role[0] for role in base_actors}
                        for role, actor in case_actors.items():
                            await services.request('PUT', '/identities/' + actor, {'traits': {'project': run, 'case': str(i), 'role': role}})
                        await services.request('PUT', '/audiences/' + case_audience,
                            {'kind': 'fixed', 'name': 'Isolated navigation evaluation case', 'identities': list(case_actors.values())})
                        services.actors = case_actors
                    for retry in range(1, cfg['retry_budget']):
                        if attempts[-1]['qualified']:
                            break
                        previous = attempts[-1]
                        local_context.append({'kind': 'working-context-failure', 'action': previous['action'],
                            'failure': previous['failure'], 'checks': previous['checks']})
                        if enabled:
                            services.audience = case_audience
                            failure_id = await services.write('experimenter', {'kind': 'case-local-failure', 'experiment_id': run,
                                'layout_sha256': layout['layout_sha256'], 'attempt': retry-1,
                                'action': previous['action'], 'failure': previous['failure'], 'checks': previous['checks'],
                                'qualification': 'This evaluation case only; inaccessible to other cases.'})
                            services.actors = base_actors
                            await services.read('researcher', failure_id, allowed=False)
                            services.actors = case_actors
                            local_context.append(await services.read('designer', failure_id))
                            services.audience = shared
                        row = await select_and_run(layout, seed, update, local_context,
                            f'adapt-{name}-{i}-{int(enabled)}-{retry}')
                        attempts.append(row)
                    services.audience, services.actors = shared, base_actors
                    report['adaptation'].append({'layout_sha256': layout['layout_sha256'], 'model': name,
                        'memory_enabled': enabled, 'attempts': attempts,
                        'success_within_budget': any(r['qualified'] for r in attempts)})
                    await publish()
        assert len(report['adaptation']) == 32
        report['final_summaries'] = {k: summary(v) for k, v in report['final'].items()}
        gate = report['development'][str(selected)]['summary']
        report['phase_b_gate_met'] = bool(gate['qualified']/gate['n'] >= cfg['gate']['development_first_attempt_fraction']
            and gate['falls'] == 0 and gate['contacts'] == 0)
        report['phase_b_status'] = 'Object-relative task extension remains separately gated.'
        report['sequence_final_opened'] = False
        record = await services.write('experimenter', {'kind': 'final-results', 'experiment_id': run,
            'summaries': report['final_summaries'], 'selected_update': selected,
            'phase_b_gate_met': report['phase_b_gate_met'],
            'qualification': 'Navigation on eight unseen layouts. Exact geometry is privileged. Native gait weights unchanged.'})
        context = await services.read('critic', record)
        verdict = await services.decide('critic', 'Assess this bounded final navigation study without claiming universal generalization.',
            context, ['limited_generalization_evidence', 'improvement_not_established'], [record])
        record = await services.write('critic', {'kind': 'final-qualified-verdict', 'experiment_id': run,
            'result_record': record, 'verdict': verdict,
            'qualification': 'Numerical comparisons determine gains; this verbal judgment is not a success verifier.'})
        await services.read('researcher', record)
        report.update(status='completed', phase='navigation evaluation complete')
        provenance['status'] = 'completed'
        await publish()
        return {'status': report['status'], 'completed_cases': len(report['adaptation'])}
    except BaseException as error:
        report.update(status='incomplete', error_type=type(error).__name__, error='Continuation interrupted; preserved artifacts require inspection')
        provenance['status'] = 'incomplete'
        await publish()
        raise
    finally:
        await services.http.aclose()


@app.local_entrypoint()
def launch(continuation: str = 'adaptation-resume-3'):
    function = modal.Function.from_name('mochi-navigation-v23-recovery', 'resume')
    call = function.spawn('mochi-nav23-20261121c', continuation)
    result = {'call_id': call.object_id, 'run_id': 'mochi-nav23-20261121c',
        'continuation': continuation, 'detached': True, 'additional_optimizer_updates': 0}
    (ROOT / ('artifacts/navigation-v23/resume-launch-' + continuation + '.json')).write_text(json.dumps(result, indent=2)+'\n')
    (ROOT / 'artifacts/navigation-v23/resume-launch.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
