"""Matched engineering probe after observed final-heading phase chatter."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from mochi.navigation_v23.engine import run
from mochi.navigation_v23.layouts import generate

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--profile', choices=['direct', 'buffered', 'planner'], required=True)
parser.add_argument('--case', choices=['failed-training', 'engineering-zero'], required=True)
args = parser.parse_args()
directory = root / 'artifacts/navigation-v23/engineering'
ident = 'alignment-r1-' + args.case + '-' + args.profile
target = directory / (ident + '.json.gz')
assert not target.exists(), 'Preserve prior engineering attempts'
if args.case == 'failed-training':
    previous = json.loads((root / 'artifacts/navigation-v23/controller-feasibility-interruption.json').read_text())
    row = previous['training_trials'][-1]['outcomes']['direct']
    layout, seed = row['layout'], row['seed']
else:
    layout, seed = generate(230000, 'engineering', 0), 231000
result = run(layout, seed, args.profile)
packed = gzip.compress(json.dumps(result, separators=(',', ':')).encode(), compresslevel=1, mtime=0)
target.write_bytes(packed)
meta = {k: result[k] for k in ['qualified', 'complete', 'checks', 'failure', 'fall', 'invalid_contact',
    'action', 'steps', 'physical_seconds', 'executed_distance_m', 'minimum_envelope_clearance_m', 'wall_seconds', 'arrivals']}
meta.update(id=ident, layout_sha256=layout['layout_sha256'], artifact_sha256=hashlib.sha256(packed).hexdigest(),
    engine_sha256=hashlib.sha256((root / 'src/mochi/navigation_v23/engine.py').read_bytes()).hexdigest(),
    navigation_sha256=hashlib.sha256((root / 'src/mochi/navigation_v23/navigation.py').read_bytes()).hexdigest())
target.with_suffix('').with_suffix('.metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
print(json.dumps(meta), flush=True)
