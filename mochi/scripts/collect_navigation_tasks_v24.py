"""Collect real, clone-verified component labels after navigation finishes."""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import time

from mochi.balanced.sequence import PhysicalStop
from mochi.navigation_tasks_v24 import policy
from mochi.navigation_tasks_v24.branches import evaluate
from mochi.navigation_tasks_v24.sequence import run
from mochi.navigation_tasks_v24.snapshot import capture_and_verify, state
from mochi.navigation_tasks_v24.layouts import task_layout

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--index', type=int, required=True)
args = parser.parse_args()
assert args.index in [0, 1], 'Two bounded training-layout collections'
parent = json.loads((ROOT / 'artifacts/navigation-v23/completed/progress.json').read_text())
assert parent['status'] == 'completed' and parent['phase_b_gate_met']
gate_file = ROOT / 'artifacts/navigation-tasks-v24/task-validation-gate.json'
assert gate_file.exists() and json.loads(gate_file.read_text()).get('qualified_complete_prefixes', 0) > 0, \
    'Task collection is disabled: the bounded preflight has not validated a complete four-task prefix.'
layout = task_layout(json.loads((ROOT / 'configs/navigation-v23/training.json').read_text())[args.index])
directory = ROOT / 'artifacts/navigation-tasks-v24' / ('collection-' + str(args.index))
directory.mkdir(parents=True, exist_ok=False)
progress = {'scope': 'Actual teacher prefix and isolated candidate branches. No trained-checkpoint evaluation.',
    'layout_sha256': layout['layout_sha256'], 'trials': [], 'examples': [],
    'physical_attempts': 1, 'status': 'running', 'clone_checks': []}
started = time.perf_counter()
pending = {}


def save():
    progress['wall_seconds'] = time.perf_counter() - started
    (directory / 'collection.json').write_text(json.dumps(progress, indent=2) + '\n')


def capture(w, domain, task):
    assert progress['physical_attempts'] < 37
    progress['physical_attempts'] += 1
    checked = capture_and_verify(w)
    progress['clone_checks'].append({'domain': domain, 'task': task, **checked['clone_check']})
    snapshot = state(w, include_history=False)
    pending.update(snapshot=snapshot, domain=domain, task=task)
    filename = str(len(progress['clone_checks'])) + '-' + domain + '-' + task + '.pickle'
    payload = pickle.dumps(snapshot, protocol=pickle.HIGHEST_PROTOCOL)
    (directory / filename).write_bytes(payload)
    progress['clone_checks'][-1].update(snapshot_file=filename, snapshot_sha256=hashlib.sha256(payload).hexdigest())
    save()


def choose(domain, task, observed, decision):
    assert (pending['domain'], pending['task']) == (domain, task)
    outcomes = []
    for action, _ in decision.choices:
        assert progress['physical_attempts'] < 37
        progress['physical_attempts'] += 1
        result = evaluate(pending['snapshot'], domain, task, action)
        outcomes.append(result)
        print(json.dumps({'layout': args.index, 'domain': domain, 'task': task,
            'action': action, 'valid': result.get('valid'), 'failure': result.get('failure')}), flush=True)
        save()
    valid = [r for r in outcomes if r.get('valid')]
    target = min(valid, key=lambda r: r['rank'])['action'] if valid else None
    trial = {'domain': domain, 'task': task, 'observation': observed, 'decision': asdict(decision),
        'outcomes': outcomes, 'target': target}
    progress['trials'].append(trial)
    if target:
        progress['examples'].append({'domain': domain, 'task': task, 'decision': asdict(decision),
            'target': target, 'outcomes_sha256': hashlib.sha256(json.dumps(outcomes, sort_keys=True).encode()).hexdigest()})
    save()
    if target is None:
        raise PhysicalStop('no-qualified-measured-training-candidate:' + domain + ':' + task)
    return {'action': target, 'source': 'Measured component teacher; not a trained selector'}


try:
    row = run(layout, parent['protocol']['physics_seeds'][args.index], choose=choose, capture=capture)
    payload = gzip.compress(json.dumps(row, separators=(',', ':')).encode(), compresslevel=1, mtime=0)
    (directory / 'teacher-prefix.json.gz').write_bytes(payload)
    progress.update(status='completed', prefix_qualified=row['qualified_complete'],
        prefix_failure=row['failure'], prefix_sha256=hashlib.sha256(payload).hexdigest())
finally:
    save()
print(json.dumps({k: progress[k] for k in ['status', 'physical_attempts', 'wall_seconds', 'prefix_qualified', 'prefix_failure']}))
