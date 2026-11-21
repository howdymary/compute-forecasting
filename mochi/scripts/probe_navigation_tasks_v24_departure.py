"""New six-attempt departure probe, preserving the closed twelve-attempt pilot."""
import argparse
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import signal
import time

from mochi.balanced.sequence import PhysicalStop
from mochi.navigation_tasks_v24.snapshot import restore
from mochi.navigation_tasks_v24.departure import clear_globe_turn
from mochi.navigation_tasks_v24.approaches import task_pose, candidate_approach, transit
from mochi.navigation_tasks_v24 import policy

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--id', required=True)
parser.add_argument('--distance', type=float, default=.08)
args = parser.parse_args()
assert args.id.replace('-', '').isalnum() and .04 <= args.distance <= .10
directory = ROOT / 'artifacts/navigation-tasks-v24/departure-r2'
directory.mkdir(parents=True, exist_ok=True)
ledger_path = directory / 'ledger.json'
assert not (directory / (args.id + '.metadata.json')).exists()
started = time.perf_counter()


def account(record):
    with (directory / 'ledger.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {
            'id': 'mochi-task24-departure-r2', 'bounds': {'attempts': 6, 'wall_seconds': 1800}, 'attempts': {}}
        if args.id not in ledger['attempts']:
            assert len(ledger['attempts']) < 6
            spent = sum(v.get('wall_seconds', v['reserved_seconds']) for v in ledger['attempts'].values())
            assert spent + 300 <= 1800
            parent = json.loads((ROOT / '.cache/navigation-v23/live-progress-c.json').read_text())
            old = json.loads((ROOT / 'evidence/navigation-tasks-v24/preflight.json').read_text())
            # Reserve the remaining navigation study conservatively while it
            # finishes. No source or active budget of that study is changed.
            assert parent['usage_actual_or_reserved']['simulation_cpu_hours'] + old['conservative_wall_hours'] + 3 + (spent+300)/3600 <= 12
        ledger['attempts'][args.id] = record
        ledger_path.write_text(json.dumps(ledger, indent=2) + '\n')


record = {'id': args.id, 'status': 'running', 'reserved_seconds': 300,
    'scope': 'New isolated departure-controller branch; not a complete-sequence or training result.',
    'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / 'src/mochi/navigation_tasks_v24').glob('*.py'))}}
account(record)
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Departure probe wall limit')))
signal.setitimer(signal.ITIMER_REAL, 300)
try:
    old = ROOT / 'artifacts/navigation-tasks-v24'
    original = json.loads((old / 'physical-r3-full.metadata.json').read_text())
    entry = next(s for s in original['snapshots'] if s['domain'] == 'navigation' and s['task'] == 'globe')
    payload = (old / 'physical-r3-full-states' / entry['file']).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == entry['sha256']
    w = restore(pickle.loads(payload), record=True)
    retreat = clear_globe_turn(w, args.distance)
    goal = task_pose(w, 'globe')
    approach = candidate_approach(w, goal)
    arrivals = transit(w, approach['pose'], 'globe', fine_goal=None if approach.get('direct_fine') else goal,
        fine_mode=approach['alignment_mode'], direct_fine=approach.get('direct_fine', False))
    result = policy.execute(w, 'globe', 'globe', 'G0')
    recovery = policy.execute(w, 'recovery', 'globe', 'R4') if result['success'] else None
    record.update(status='completed', retreat=retreat, arrivals=arrivals, result=result, recovery=recovery)
except PhysicalStop as error:
    record.update(status='completed', physical_failure=str(error))
except BaseException as error:
    record.update(status='incomplete', error_type=type(error).__name__)
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    if 'w' in locals():
        episode = w.episode()
        raw = gzip.compress(json.dumps({'episode': episode, 'record': record}, separators=(',', ':')).encode(), mtime=0)
        (directory / (args.id + '.json.gz')).write_bytes(raw)
        record.update(artifact_sha256=hashlib.sha256(raw).hexdigest(), fall=w.fall,
            invalid_contact=w.invalid_contact, contact_failures=episode['contact_failures'])
    record['wall_seconds'] = time.perf_counter()-started
    account(record)
    (directory / (args.id + '.metadata.json')).write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({k: v for k, v in record.items() if k != 'retreat'}), flush=True)
