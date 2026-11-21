"""Compare immutable unrounded recordings; no new physics or model calls."""
import json
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
app = modal.App('mochi-navigation-v23-trajectory-audit')
volume = modal.Volume.from_name('mochi-navigation-v23-artifacts')


@app.function(image=modal.Image.debian_slim(python_version='3.11'), serialized=True,
    cpu=1, memory=4096, timeout=600, max_containers=1, retries=0,
    volumes={'/archive': volume.with_mount_options(read_only=True)})
def audit(run):
    import gzip
    import hashlib
    import time
    start = time.perf_counter()
    report = json.loads((Path('/archive') / run / 'progress.json').read_text())
    assert report['status'] == 'completed'
    rows = []
    fixed = {(r['layout_sha256'], r['seed']): r for r in report['final']['fixed']}
    parents = {(r['layout_sha256'], r['seed']): r for r in report['final']['parent']}
    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    def read(row):
        artifact = row['artifact']
        data = (Path('/archive') / artifact['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == artifact['sha256']
        return json.loads(gzip.decompress(data))['episode']
    for selected in report['final']['selected']:
        reference = fixed[(selected['layout_sha256'], selected['seed'])]
        parent = parents[(selected['layout_sha256'], selected['seed'])]
        a, b, c = read(selected), read(reference), read(parent)
        fields = ['trajectory', 'control_telemetry', 'step_events', 'balance_measurements']
        hashes = {field: {'selected': digest(a[field]), 'fixed': digest(b[field])} for field in fields}
        parent_hashes = {field: digest(c[field]) for field in fields}
        rows.append({'layout_sha256': selected['layout_sha256'], 'seed': selected['seed'],
            'same_action': selected['action'] == reference['action'], 'hashes': hashes,
            'same_parent_action': selected['action'] == parent['action'],
            'parent_hashes': parent_hashes,
            'exact_parent_recorded_fields_match': all(v['selected'] == parent_hashes[field] for field, v in hashes.items()),
            'exact_recorded_fields_match': all(v['selected'] == v['fixed'] for v in hashes.values())})
    return {'run_id': run, 'status': 'completed', 'physical_attempts_added': 0,
        'optimizer_updates_added': 0, 'model_calls_added': 0, 'cases': rows,
        'exact_recorded_matches': sum(r['exact_recorded_fields_match'] for r in rows),
        'exact_parent_recorded_matches': sum(r['exact_parent_recorded_fields_match'] for r in rows),
        'receipt': {'provider': 'Modal', 'cpu': 1, 'memory_mib': 4096, 'wall_seconds': time.perf_counter()-start},
        'scope': 'Post-selection equality check of stored unrounded body trajectories, control telemetry, footstep events and balance samples on this finite cohort. Not equivalence of policies on all possible observations.'}


@app.local_entrypoint()
def main():
    result = audit.remote('mochi-nav23-20261121c')
    out = ROOT / 'evidence/navigation-v23/trajectory-equivalence-audit.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'exact_recorded_matches': result['exact_recorded_matches'], 'cases': len(result['cases'])}))
