"""One bounded contact hypothesis from an actual reached training state."""
import argparse
from dataclasses import replace
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import signal
import time

from mochi.contact_v18.policy import PRESSES
from mochi.navigation_tasks_v24.snapshot import restore
from mochi.navigation_tasks_v24 import policy

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--release-degrees', type=int, choices=[48, 52], required=True)
args = parser.parse_args()
directory = ROOT / 'artifacts/navigation-tasks-v24'
ident = 'laptop-release-' + str(args.release_degrees)
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
    'scope': 'Isolated contact engineering branch, not a full sequence or a training result.'}
account(record)
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Contact probe wall limit')))
signal.setitimer(signal.ITIMER_REAL, 150)
try:
    original = json.loads((directory / 'physical-r2-full.metadata.json').read_text())
    entry = next(s for s in original['snapshots'] if s['domain'] == 'laptop')
    payload = (directory / 'physical-r2-full-states' / entry['file']).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == entry['sha256']
    saved = pickle.loads(payload)  # Own local, SHA-verified simulator snapshot only.
    w = restore(saved, record=True)
    w.contact_closing_speed = .4
    p = replace(PRESSES['P5'], release_degrees=float(args.release_degrees))
    result = w.do_task('laptop', p, max_seconds=32.)
    recovery = policy.execute(w, 'recovery', 'laptop', 'R4') if result['success'] else None
    episode = w.episode()
    raw = gzip.compress(json.dumps({'result': result, 'recovery': recovery, 'episode': episode}, separators=(',', ':')).encode(), mtime=0)
    (directory / (ident + '.json.gz')).write_bytes(raw)
    record.update(status='completed', result={k: v for k, v in result.items() if k != 'force_schedule_log'},
        recovery=recovery, artifact_sha256=hashlib.sha256(raw).hexdigest(),
        snapshot_sha256=entry['sha256'], fall=w.fall, invalid_contact=w.invalid_contact)
except BaseException as error:
    record.update(status='incomplete', error_type=type(error).__name__, error=str(error)[:200])
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    record['wall_seconds'] = time.perf_counter() - started
    account(record)
    metadata.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record), flush=True)
