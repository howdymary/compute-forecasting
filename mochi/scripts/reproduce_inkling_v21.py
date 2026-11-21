"""Run the frozen physics interface under a separate reproduction ledger."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from mochi.inkling_v21 import experiment

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--run', required=True)
    args, remaining = parser.parse_known_args()
    assert re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', args.run), 'Use a dedicated reproduction name'
    freeze = json.loads((ROOT / 'evidence/inkling-v21/selection-freeze.json').read_text())
    for name, expected in freeze['frozen_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    experiment.OUT = ROOT / 'artifacts/inkling-v21-reproduction' / args.run / 'physics'
    experiment.OUT.mkdir(parents=True, exist_ok=True)
    declaration = experiment.OUT.parent / 'budget.json'
    if not declaration.exists():
        declaration.write_text(json.dumps({'run': args.run, 'physical_attempt_cap': 24,
            'simulation_wall_seconds_cap': 10800, 'single_full_attempt_wall_seconds': 600,
            'scope': 'Independent reproduction. Does not extend or replace the archived study ledger.'}, indent=2) + '\n')
    sys.argv = [sys.argv[0], *remaining]
    experiment.main()


if __name__ == '__main__':
    main()
