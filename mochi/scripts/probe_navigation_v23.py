"""Immutable local engineering attempts before the study source is frozen."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

from mochi.navigation_v23.engine import run
from mochi.navigation_v23.layouts import generate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/navigation-v23/engineering'
parser = argparse.ArgumentParser()
parser.add_argument('--index', type=int, required=True)
parser.add_argument('--profile', choices=['direct', 'buffered', 'careful', 'planner'], required=True)
parser.add_argument('--id', required=True)
args = parser.parse_args()
OUT.mkdir(parents=True, exist_ok=True)
path = OUT / (args.id + '.json.gz')
assert not path.exists()
layout = generate(230000 + args.index * 101, 'engineering', args.index)
row = run(layout, 231000, args.profile)
packed = gzip.compress(json.dumps(row, separators=(',', ':')).encode(), compresslevel=1, mtime=0)
path.write_bytes(packed)
meta = {k: row[k] for k in ['qualified', 'complete', 'failure', 'fall', 'invalid_contact', 'checks',
    'action', 'steps', 'physical_seconds', 'executed_distance_m', 'minimum_envelope_clearance_m', 'wall_seconds']}
meta.update(id=args.id, layout_sha256=layout['layout_sha256'], artifact_sha256=hashlib.sha256(packed).hexdigest(),
    engine_sha256=hashlib.sha256((ROOT / 'src/mochi/navigation_v23/engine.py').read_bytes()).hexdigest())
(OUT / (args.id + '.metadata.json')).write_text(json.dumps(meta, indent=2) + '\n')
print(json.dumps(meta), flush=True)
