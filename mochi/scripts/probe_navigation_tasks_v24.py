"""Bounded task preflight after the completed navigation gate, never final layouts."""
import argparse
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import signal
import time
import pickle

from mochi.navigation_tasks_v24.sequence import run

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--id', required=True)
parser.add_argument('--development-index', type=int, default=0)
parser.add_argument('--training-index', type=int)
parser.add_argument('--capture-states', action='store_true')
parser.add_argument('--clear-task-workspace', action='store_true')
parser.add_argument('--until', choices=['ascent', 'books', 'all'], default='books')
parser.add_argument('--navigation-report', type=Path, default=ROOT / 'artifacts/navigation-v23/completed/progress.json')
args = parser.parse_args()
assert args.id.replace('-', '').isalnum()
parent = json.loads(args.navigation_report.read_text())
gate = parent['protocol']['gate']
passed = any(v['summary']['qualified'] / v['summary']['n'] >= gate['development_first_attempt_fraction']
    and v['summary']['falls'] <= gate['development_falls_max'] and v['summary']['contacts'] <= gate['development_contacts_max']
    for v in parent['development'].values())
assert passed, 'Satisfy the frozen development navigation gate first. Never open sequence final layouts during engineering.'
source = ROOT / 'evidence/navigation-v23/counterfactual-results.json'
usage = json.loads(source.read_text())['cumulative_usage_actual_or_reserved'] if source.exists() else parent['usage_actual_or_reserved']
directory = ROOT / 'artifacts/navigation-tasks-v24'
directory.mkdir(parents=True, exist_ok=True)
target = directory / (args.id + '.json.gz')
assert not target.exists()
ledger_path = directory / 'engineering-ledger.json'


def account(value):
    with (directory / 'engineering.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {
            'parent_usage_actual_or_reserved': usage, 'attempts': {}, 'bounds': {'attempts': 12, 'cpu_hours': 1}}
        if args.id not in ledger['attempts']:
            diagnostics = [json.loads(p.read_text()) for p in directory.glob('snapshot-*-probe.json')]
            extra_attempts = sum(r['physical_attempts'] for r in diagnostics)
            assert len(ledger['attempts']) + extra_attempts < 12
            spent = sum(r.get('wall_seconds', r['reserved_seconds']) for r in ledger['attempts'].values()) + sum(r.get('wall_seconds', r.get('wall_seconds_reserved', 0)) for r in diagnostics)
            ledger['additional_diagnostic_attempts'] = extra_attempts
            assert spent + 900 <= 3600
            assert usage['physical_rollouts'] + len(ledger['attempts']) + 1 <= parent['protocol']['bounds']['physical_rollouts']
            assert usage['simulation_cpu_hours'] + (spent + 900) / 3600 <= parent['protocol']['bounds']['simulation_cpu_hours']
        ledger['attempts'][args.id] = value
        ledger_path.write_text(json.dumps(ledger, indent=2) + '\n')


split = 'training' if args.training_index is not None else 'development'
layouts = json.loads((ROOT / ('configs/navigation-v23/' + split + '.json')).read_text())
layout = layouts[args.training_index if args.training_index is not None else args.development_index]
if args.clear_task_workspace:
    from mochi.navigation_tasks_v24.layouts import task_layout
    layout = task_layout(layout)
meta = {'id': args.id, 'status': 'running', 'arguments': {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}, 'reserved_seconds': 900,
    'navigation_gate_evidence_sha256': hashlib.sha256(args.navigation_report.read_bytes()).hexdigest(),
    'navigation_still_running': parent['status'] != 'completed',
    'layout_sha256': layout['layout_sha256'], 'source_sha256': {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / 'src/mochi/navigation_tasks_v24').glob('*.py'))}}
account(meta)
started = time.perf_counter()
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Task engineering wall limit')))
signal.setitimer(signal.ITIMER_REAL, 900)
try:
    snapshots = []
    def capture(w, domain, task):
        from mochi.smooth_v16.world import state
        payload = pickle.dumps(state(w, include_history=False), protocol=pickle.HIGHEST_PROTOCOL)
        folder = directory / (args.id + '-states')
        folder.mkdir(exist_ok=True)
        filename = str(len(snapshots)) + '-' + domain + '-' + task + '.pickle'
        (folder / filename).write_bytes(payload)
        snapshots.append({'domain': domain, 'task': task, 'file': filename,
            'sha256': hashlib.sha256(payload).hexdigest(), 'split': split,
            'physical_time': float(w.d.time), 'scope': 'Actual uninterrupted reached state; not a generated successful trajectory.'})
    row = run(layout, parent['protocol']['physics_seeds'][0], until=args.until,
        capture=capture if args.capture_states else None)
    packed = gzip.compress(json.dumps(row, separators=(',', ':')).encode(), compresslevel=1, mtime=0)
    target.write_bytes(packed)
    episode = row['episode']
    meta.update(status='completed', failure=row['failure'], qualified_complete=row['qualified_complete'],
        artifact_sha256=hashlib.sha256(packed).hexdigest(), physical_seconds=episode['duration'],
        steps=episode['steps']['attempts'], fall=episode['fall'], invalid_contact=episode['invalid_contact'],
        tasks={k: v['success'] for k, v in episode['results'].items()},
        arrivals=[{k: a[k] for k in ['label', 'success', 'duration_s']} for a in row['arrivals']], snapshots=snapshots)
except BaseException as error:
    meta.update(status='incomplete', error_type=type(error).__name__, error=str(error)[:250])
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    meta['wall_seconds'] = time.perf_counter() - started
    account(meta)
    target.with_suffix('').with_suffix('.metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps(meta), flush=True)
