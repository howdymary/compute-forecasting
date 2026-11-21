"""Execute the predeclared fresh pairs only after a hashed selection freeze."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/visual-motion-v22'
freeze = json.loads((OUT / 'selection-freeze.json').read_text())
for file, expected in freeze['source_sha256'].items():
    assert hashlib.sha256((ROOT / file).read_bytes()).hexdigest() == expected, file
assert freeze['held_out_seeds'] == list(range(226000, 226004))
ledger = json.loads((OUT / 'physics/ledger.json').read_text())
assert not any(v['arguments']['seed'] in freeze['held_out_seeds'] for v in ledger['attempts'].values())
assert not any(v['status'] == 'running' for v in ledger['attempts'].values())
assert len(ledger['attempts']) + 8 <= 32
env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}


def attempt(item):
    seed, side = item
    ident = f'full-{side}-fresh-{seed}'
    args = [sys.executable, '-u', '-m', 'mochi.visual_motion_v22.experiment', '--id', ident,
        '--mode', 'full', '--seed', str(seed)]
    if side == 'mink':
        args += ['--candidate', str(ROOT / 'configs/visual-motion-v22/mink-recovery-only.json')]
    with (OUT / 'physics' / (ident + '.log')).open('w') as log:
        result = subprocess.run(args, cwd=ROOT.parent, env=env, stdout=log, stderr=subprocess.STDOUT)
    print(json.dumps({'id': ident, 'exit_code': result.returncode}), flush=True)
    return result.returncode


with ThreadPoolExecutor(max_workers=4) as pool:
    status = list(pool.map(attempt, [(s, v) for s in freeze['held_out_seeds'] for v in ['parent', 'mink']]))
assert not any(status), status
