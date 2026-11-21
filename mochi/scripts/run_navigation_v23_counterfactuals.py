"""Post-selection diagnostic; no new training or tuning of final results."""
import json
from pathlib import Path

import modal

from mochi.navigation_v23.remote import image as frozen_image, existing_secrets

ROOT = Path(__file__).resolve().parents[1]
RUN = json.loads((ROOT / 'configs/navigation-v23/protocol.json').read_text())['run_id']
image = frozen_image.add_local_file(ROOT / 'configs/navigation-v23-counterfactuals.json', '/app/diagnostic-layouts.json', copy=True)
volume = modal.Volume.from_name('mochi-navigation-v23-artifacts')
app = modal.App('mochi-navigation-v23-counterfactuals')


@app.function(image=image, secrets=existing_secrets, serialized=True, cpu=1, memory=4096,
              timeout=1800, max_containers=1, retries=0, volumes={'/artifacts': volume})
async def run_diagnostic(run):
    import asyncio
    import copy
    import hashlib
    import time
    import tinker
    from tinker_cookbook import model_info, renderers
    from tinker_cookbook.recipes.decisions import DecisionRenderer, sample_decision
    from mochi.integrations import digest, now
    from mochi.navigation_v23.engine import inspect, observation, decision
    directory = Path('/artifacts') / run
    progress = json.loads((directory / 'progress.json').read_text())
    assert progress['status'] == 'completed'
    target = directory / 'counterfactual-results.json'
    assert not target.exists(), 'Preserve the first diagnostic'
    config_bytes = Path('/app/diagnostic-layouts.json').read_bytes()
    config = json.loads(config_bytes)
    paths = json.loads((directory / 'private-checkpoint-paths.json').read_text())
    usage = copy.deepcopy(progress['usage_actual_or_reserved'])
    bounds = progress['protocol']['bounds']
    lock, slots = asyncio.Lock(), asyncio.Semaphore(4)
    async def charge(key, amount):
        async with lock:
            assert 0 <= usage[key] + amount <= bounds[key], 'Shared campaign ceiling: ' + key
            usage[key] += amount
    selected = progress['selected_checkpoint']['update']
    service = tinker.ServiceClient(display_name=run + '-counterfactuals')
    samplers = {}
    for u in sorted(set([0, selected])):
        restored = await service.create_training_client_from_state(paths[str(u)]['optimizer'])
        samplers[u] = await restored.save_weights_and_get_sampling_client(kind='snapshot')
    renderer = DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(progress['protocol']['model']), samplers[0].get_tokenizer()))
    trial = modal.Function.from_name('mochi-navigation-v23', 'trial')
    result = {'run_id': run, 'created_at': now(), 'scope': config['scope'],
        'config_sha256': hashlib.sha256(config_bytes).hexdigest(), 'optimizer_updates_in_diagnostic': 0,
        'selected_checkpoint_frozen': progress['selected_checkpoint'], 'cases': [], 'receipts': [],
        'initial_usage': copy.deepcopy(usage), 'status': 'running'}
    async def save():
        result['cumulative_usage_actual_or_reserved'] = copy.deepcopy(usage)
        target.write_text(json.dumps(result, indent=2) + '\n')
        await volume.commit.aio()
    async def one(pair_index, variant, layout, seed, name, update):
        async with slots:
            if name == 'planner':
                action, selection = 'planner', {}
            else:
                w, envelope, obstacles, plans = inspect(layout, seed)
                obs = observation(w, envelope, obstacles, plans)
                rendering = renderer.render(decision(obs))
                await charge('inference_input_plus_max_output_tokens', len(rendering.tokens) + 1)
                await charge('modeled_provider_usd', (len(rendering.tokens) + 1) * 1.01 / 1_000_000)
                started = time.perf_counter()
                distribution = await sample_decision(samplers[update], rendering)
                action = max(distribution, key=distribution.get)
                selection = {'action': action, 'distribution': distribution, 'optimizer_updates': update,
                    'checkpoint_id': digest(paths[str(update)]['optimizer']), 'observation_sha256': digest(obs),
                    'inference_seconds': time.perf_counter() - started, 'source': 'Frozen Tinker checkpoint; exploratory counterfactual diagnostic'}
            await charge('physical_rollouts', 1)
            await charge('simulation_cpu_hours', .1)
            await charge('modeled_provider_usd', .02)
            ident = f'counterfactual-p{pair_index}-{variant}-{name}'
            await save()
            row = await trial.remote.aio(layout, seed, action, selection, ident)
            await charge('simulation_cpu_hours', row['receipt']['duration_seconds'] / 3600 - .1)
            result['receipts'].append({'id': ident, **row['receipt'], 'artifact': row['artifact']})
            await save()
            return row
    try:
        for index, pair in enumerate(config['pairs']):
            for variant in ['base', 'mug_in_turning_area']:
                rows = await asyncio.gather(*(one(index, variant, pair[variant], pair['physics_seed'], name, update)
                    for name, update in [('parent', 0), ('selected', selected), ('planner', None)]))
                result['cases'].append({'pair': index, 'variant': variant,
                    'runs': dict(zip(['parent', 'selected', 'planner'], rows))})
        result['behavior_audit'] = []
        for index in range(len(config['pairs'])):
            base = next(c for c in result['cases'] if c['pair'] == index and c['variant'] == 'base')
            changed = next(c for c in result['cases'] if c['pair'] == index and c['variant'] == 'mug_in_turning_area')
            for name in ['parent', 'selected', 'planner']:
                a, b = base['runs'][name], changed['runs'][name]
                result['behavior_audit'].append({'pair': index, 'model': name,
                    'action_changed': a['action'] != b['action'],
                    'planned_route_changed': digest(a['plans'][a['action']].get('points')) != digest(b['plans'][b['action']].get('points')),
                    'base_qualified': a['qualified'], 'moved_mug_qualified': b['qualified'],
                    'base_invalid_contact': a['invalid_contact'], 'moved_mug_invalid_contact': b['invalid_contact'],
                    'interpretation': 'Planner rerouting with an unchanged selected profile does not establish learned layout-specific strategy.'})
        result['status'] = 'completed'
        await save()
        return result
    except BaseException as error:
        result.update(status='incomplete', error_type=type(error).__name__)
        await save()
        raise


@app.local_entrypoint()
def main():
    result = run_diagnostic.remote(RUN)
    p = ROOT / 'evidence/navigation-v23/counterfactual-results.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'physical_attempts': len(result['receipts']), 'behavior_audit': result.get('behavior_audit')}))
