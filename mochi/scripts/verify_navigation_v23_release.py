"""Read-only hosted release verification, including every public recording."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--release', required=True)
parser.add_argument('--url', default='https://howdymary--mochi-navigation-v23-demo-web.us-east.modal.run')
args = parser.parse_args()
base = args.url.rstrip('/')
ROOT = Path(__file__).resolve().parents[1]


def fetch(path):
    with urllib.request.urlopen(base + path, timeout=180) as response:
        return response.read()


health = json.loads(fetch('/api/health'))
assert health['release'] == args.release and health['evaluation_complete'] and not health['preview']
assert health['cases'] == 32 and health['optimizer_updates'] == 15
assert health['privileged_state'] and not health['native_gait_weights_trained']
report_bytes = fetch('/navigation-v23/report.json')
local = ROOT / 'web/desk/navigation-v23/report.json'
assert hashlib.sha256(report_bytes).hexdigest() == hashlib.sha256(local.read_bytes()).hexdigest()
manifest = json.loads(fetch('/navigation-v23/recording-manifest.json'))
start = time.perf_counter()


def verify(item):
    name, expected = item
    content = fetch('/navigation-v23/' + name)
    assert len(content) == expected['bytes'] and hashlib.sha256(content).hexdigest() == expected['sha256'], name
    return {'name': name, 'bytes': len(content), 'sha256': expected['sha256'], 'verified': True}


with ThreadPoolExecutor(max_workers=4) as pool:
    verified = list(pool.map(verify, manifest.items()))
result = {'url': base, 'health': health, 'report_sha256': hashlib.sha256(report_bytes).hexdigest(),
    'verified_recordings': len(verified), 'verified_bytes': sum(r['bytes'] for r in verified),
    'wall_seconds': time.perf_counter() - start, 'recordings': verified}
(ROOT / 'evidence/navigation-v23/live-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ['verified_recordings', 'verified_bytes', 'wall_seconds']}))
