"""Read-only progress monitor; the actual campaign runs detached on Modal."""
import datetime
import json
from pathlib import Path
import time
import argparse

import modal

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--continuation', default='adaptation-resume-2')
args = parser.parse_args()
volume = modal.Volume.from_name('mochi-navigation-v23-artifacts')
directory = ROOT / '.cache/navigation-v23'
directory.mkdir(parents=True, exist_ok=True)
previous = None
while True:
    try:
        raw = b''.join(volume.read_file('mochi-nav23-20261121c/progress.json'))
        report = json.loads(raw)
        observed = datetime.datetime.now(datetime.timezone.utc).isoformat()
        snapshot = {'observed_at': observed, 'status': report['status'], 'phase': report['phase'],
            'completed_retry_cases': len(report['adaptation']), 'physics_receipts': len(report['physics_receipts']),
            'error_type': report.get('error_type'), 'continuations': report.get('continuations', [])}
        (directory / 'live-progress-c.json').write_bytes(raw)
        (directory / 'live-monitor.json').write_text(json.dumps(snapshot, indent=2)+'\n')
        key = (snapshot['status'], snapshot['phase'], snapshot['completed_retry_cases'], snapshot['physics_receipts'])
        if key != previous:
            print(json.dumps(snapshot), flush=True)
            previous = key
        resumed = any(c['id'] == args.continuation for c in report.get('continuations', []))
        if report['status'] == 'completed':
            out = ROOT / 'artifacts/navigation-v23/completed'
            out.mkdir(parents=True, exist_ok=True)
            (out / 'progress.json').write_bytes(raw)
            break
        if resumed and report['status'] == 'incomplete':
            break
    except Exception as error:
        print(json.dumps({'monitor_error_type': type(error).__name__}), flush=True)
    time.sleep(45)
