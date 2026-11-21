"""New Modal execution surface. Existing deployments and secrets are unchanged."""
import importlib.metadata
import os
from pathlib import Path

import modal

ROOT = Path(os.environ['MOCHI_ROOT']) if 'MOCHI_ROOT' in os.environ else Path(__file__).resolve().parents[3]
app = modal.App('mochi-navigation-v23')
volume = modal.Volume.from_name('mochi-navigation-v23-artifacts', create_if_missing=True)
base_image = (modal.Image.debian_slim(python_version='3.11')
    .apt_install('libgl1', 'libglib2.0-0')
    .pip_install('torch==2.15.0', index_url='https://download.pytorch.org/whl/cpu')
    .pip_install('mujoco==3.3.7', 'numpy==2.3.4', 'scipy==1.16.3', 'pyyaml==6.0.2',
        'onnxruntime==1.32.0', 'httpx==0.28.1', 'tinker==0.39.2',
        'tinker-cookbook==0.7.1', 'tml-renderers==0.4.2', 'transformers==5.23.0', 'threadpoolctl==3.6.0')
    .env({'MOCHI_ROOT': '/app', 'PYTHONPATH': '/app/src', 'OPENBLAS_NUM_THREADS': '1',
        'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'MUJOCO_GL': 'disable'}))
image = (base_image.add_local_dir(ROOT / 'src', remote_path='/app/src', copy=True, ignore=['**/__pycache__', '**/*.pyc'])
    .add_local_dir(ROOT / 'configs', remote_path='/app/configs', copy=True)
    .add_local_dir(ROOT / 'assets/robot', remote_path='/app/assets/robot', copy=True))
existing_secrets = [modal.Secret.from_name(name) for name in
    ['compute-forecast-signals-v6', 'compute-forecast-evidence-future-v15']]


@app.function(image=base_image, secrets=existing_secrets, cpu=1, memory=4096, timeout=300, retries=0, serialized=True)
async def access():
    keys = {name: bool(os.environ.get(name)) for name in ['TINKER_API_KEY', 'EXA_API_KEY', 'PAST_API_KEY']}
    result = {'configured': keys, 'versions': {p: importlib.metadata.version(p)
        for p in ['mujoco', 'onnxruntime', 'tinker', 'tinker-cookbook']}}
    if keys['TINKER_API_KEY']:
        import tinker
        caps = await tinker.RestClient().get_server_capabilities()
        result['models_available'] = [m.model_name for m in caps.supported_models
            if m.model_name in ['Qwen/Qwen3.5-4B', 'thinkingmachines/Inkling-2-Mini']]
    return result


@app.local_entrypoint()
def check_access():
    import json
    result = access.remote()
    target = ROOT / 'artifacts/navigation-v23/access.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


@app.function(image=image, cpu=1, memory=4096, timeout=360, max_containers=4,
              retries=0, volumes={'/artifacts': volume}, serialized=True)
def trial(layout, seed, action, selection, ident, memories=None):
    import gzip
    import hashlib
    import json
    import platform
    import time
    from pathlib import Path
    import torch
    torch.set_num_threads(1)
    from mochi.navigation_v23.engine import run
    from mochi.smooth_v16.public import rounded
    start = time.perf_counter()
    run_id = json.loads(Path('/app/configs/navigation-v23/protocol.json').read_text())['run_id']
    directory = Path('/artifacts') / run_id / 'physics'
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (ident + '.json.gz')
    assert not target.exists(), 'Preserve immutable physical attempts'

    def choose(observed):
        if selection.get('observation_sha256'):
            from mochi.integrations import digest
            assert digest(observed) == selection['observation_sha256'], 'Inference and execution observations differ'
        return selection

    row = run(layout, seed, action, choose if selection else None, memories, True)
    raw = gzip.compress(json.dumps(row, separators=(',', ':')).encode(), compresslevel=1, mtime=0)
    target.write_bytes(raw)
    episode = row['episode']
    clip = {k: v for k, v in episode.items() if k not in ['control_telemetry', 'book_motion_samples', 'balance_measurements']}
    clip['balance_measurements'] = [{k: v for k, v in m.items() if k in ['t', 'phase', 'roll_rad', 'loads_n', 'step_category']}
        for m in episode['balance_measurements']]
    clip['model_decisions'] = episode['decisions']
    payload = gzip.compress(json.dumps(rounded(clip), separators=(',', ':')).encode(), compresslevel=6, mtime=0)
    public = directory.parent / 'public' / (ident + '.json.gz')
    public.parent.mkdir(parents=True, exist_ok=True)
    public.write_bytes(payload)
    row['artifact'] = {'volume': 'mochi-navigation-v23-artifacts',
        'path': str(target.relative_to('/artifacts')), 'sha256': hashlib.sha256(raw).hexdigest()}
    row['public_recording'] = {'path': str(public.relative_to('/artifacts')),
        'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)}
    row['receipt'] = {'provider': 'Modal', 'physical_rollouts': 1, 'cpu': 1, 'memory_mib': 4096,
        'duration_seconds': time.perf_counter() - start, 'architecture': platform.machine(),
        'scope': 'Function wall time, including import/export. Not an invoice.'}
    row['balance_metrics'] = episode['balance_metrics']
    row['native_smoothness'] = episode['native_smoothness']
    row['loaded_foot_sliding_m'] = sum(episode['foot_slip_estimate_m'].values())
    row['contact_failures'] = episode['contact_failures']
    row.pop('episode')
    row.pop('tracking')
    summary = directory / (ident + '.summary.json')
    summary.write_text(json.dumps(row, indent=2) + '\n')
    volume.commit()
    return row


@app.function(image=image, secrets=existing_secrets, cpu=1, memory=4096, timeout=21600,
              max_containers=1, retries=0, volumes={'/artifacts': volume}, serialized=True)
async def campaign():
    from mochi.navigation_v23.campaign import main
    return await main()


@app.local_entrypoint()
def launch():
    import json
    result = modal.Function.from_name('mochi-navigation-v23', 'campaign').remote()
    directory = ROOT / 'artifacts/navigation-v23/completed'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'progress.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'optimizer_updates': result['optimizer_updates_completed']}))
