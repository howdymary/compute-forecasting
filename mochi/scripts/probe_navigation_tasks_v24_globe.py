"""One measured globe-approach branch; never a complete sequence replay."""
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import signal
import time
import argparse

from mochi.balanced.sequence import PhysicalStop
from mochi.navigation_tasks_v24.snapshot import restore
from mochi.navigation_tasks_v24.approaches import task_pose, candidate_approach, transit
from mochi.navigation_tasks_v24 import policy

ROOT = Path(__file__).resolve().parents[1]
directory = ROOT / 'artifacts/navigation-tasks-v24'
parser = argparse.ArgumentParser()
parser.add_argument('--id', default='globe-hold-arms-r2')
args = parser.parse_args()
ident = args.id
assert ident.replace('-', '').isalnum()
ledger_path = directory / 'engineering-ledger.json'
metadata = directory / (ident + '.metadata.json')
assert not metadata.exists()
started = time.perf_counter()


def account(record):
    with (directory / 'engineering.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads(ledger_path.read_text())
        if ident not in ledger['attempts']:
            diagnostics = [json.loads(p.read_text()) for p in directory.glob('snapshot-*-probe.json')]
            assert len(ledger['attempts']) + sum(d['physical_attempts'] for d in diagnostics) < 12
            total = sum(v.get('wall_seconds', v['reserved_seconds']) for v in ledger['attempts'].values())
            total += sum(v.get('wall_seconds', v.get('wall_seconds_reserved', 0)) for v in diagnostics)
            assert total + 150 <= 3600
        ledger['attempts'][ident] = record
        ledger_path.write_text(json.dumps(ledger, indent=2) + '\n')


record = {'id': ident, 'status': 'running', 'reserved_seconds': 150,
    'scope': 'Restored physical component branch, not an uninterrupted four-task demonstration.',
    'eligible_as_continuous_sequence': False}
account(record)
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Globe probe wall limit')))
signal.setitimer(signal.ITIMER_REAL, 150)
try:
    original = json.loads((directory / 'physical-r3-full.metadata.json').read_text())
    entry = next(s for s in original['snapshots'] if s['domain'] == 'navigation' and s['task'] == 'globe')
    payload = (directory / 'physical-r3-full-states' / entry['file']).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == entry['sha256']
    w = restore(pickle.loads(payload), record=True)  # Own, SHA-verified snapshot.
    goal = task_pose(w, 'globe')
    approach = candidate_approach(w, goal)
    arrivals = transit(w, approach['pose'], 'globe', fine_goal=None if approach.get('direct_fine') else goal,
        fine_mode=approach['alignment_mode'], direct_fine=approach.get('direct_fine', False))
    result = policy.execute(w, 'globe', 'globe', 'G0')
    recovery = policy.execute(w, 'recovery', 'globe', 'R4') if result['success'] else None
    episode = w.episode()
    raw = gzip.compress(json.dumps({'result': result, 'recovery': recovery, 'episode': episode}, separators=(',', ':')).encode(), mtime=0)
    (directory / (ident + '.json.gz')).write_bytes(raw)
    record.update(status='completed', result=result, recovery=recovery,
        artifact_sha256=hashlib.sha256(raw).hexdigest(), snapshot_sha256=entry['sha256'],
        fall=w.fall, invalid_contact=w.invalid_contact, goal=goal, approach=approach)
except PhysicalStop as error:
    record.update(status='completed', physical_failure=str(error))
    if 'w' in locals():
        episode = w.episode()
        raw = gzip.compress(json.dumps({'episode': episode, 'failure': str(error)}, separators=(',', ':')).encode(), mtime=0)
        (directory / (ident + '.json.gz')).write_bytes(raw)
        record.update(artifact_sha256=hashlib.sha256(raw).hexdigest(), contact_failures=episode['contact_failures'])
except BaseException as error:
    record.update(status='incomplete', error_type=type(error).__name__)
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    record['wall_seconds'] = time.perf_counter() - started
    account(record)
    metadata.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record), flush=True)
