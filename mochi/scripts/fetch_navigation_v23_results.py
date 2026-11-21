"""Fetch completed public evidence; never fetch private checkpoint paths."""
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import json
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
RUN = json.loads((ROOT / 'configs/navigation-v23/protocol.json').read_text())['run_id']
OUT = ROOT / 'artifacts/navigation-v23/completed'
OUT.mkdir(parents=True, exist_ok=True)
fetch_lock = (OUT / '.fetch.lock').open('a')
fcntl.flock(fetch_lock, fcntl.LOCK_EX)
volume = modal.Volume.from_name('mochi-navigation-v23-artifacts')


def remote(path):
    return b''.join(volume.read_file(RUN + '/' + path))


report_bytes = remote('progress.json')
report = json.loads(report_bytes)
assert report['status'] == 'completed', 'Wait for the bounded campaign to finish'
(OUT / 'progress.json').write_bytes(report_bytes)
for name in ['selection-freeze.json', 'memory-journal.json']:
    try:
        content = remote(name)
    except FileNotFoundError:
        if name == 'selection-freeze.json':
            raise
        continue
    (OUT / name).write_bytes(content)

rows = []
for entry in report['development'].values():
    rows.extend(entry['rows'])
for cohort in report['final'].values():
    rows.extend(cohort)
for entry in report['adaptation']:
    rows.extend(entry['attempts'])
rows.extend(r for trial in report['training_trials'] for r in trial['outcomes'].values())
diagnostic = ROOT / 'evidence/navigation-v23/counterfactual-results.json'
if diagnostic.exists():
    value = json.loads(diagnostic.read_text())
    assert value['status'] == 'completed'
    rows.extend(r for case in value['cases'] for r in case['runs'].values())
unique = {r['public_recording']['path']: r['public_recording'] for r in rows}
public = OUT / 'public'
public.mkdir(exist_ok=True)


def fetch(item):
    path, receipt = item
    target = public / Path(path).name
    preview = ROOT / 'artifacts/navigation-v23/development-preview/public' / target.name
    content = target.read_bytes() if target.exists() else preview.read_bytes() if preview.exists() else b''.join(volume.read_file(path))
    assert hashlib.sha256(content).hexdigest() == receipt['sha256'], path
    assert len(content) == receipt['bytes']
    target.write_bytes(content)
    return len(content)


with ThreadPoolExecutor(max_workers=4) as pool:
    sizes = list(pool.map(fetch, unique.items()))
print(json.dumps({'completed': True, 'verified_replays': len(sizes), 'bytes': sum(sizes),
    'new_optimizer_updates': report['optimizer_updates_completed']}))
