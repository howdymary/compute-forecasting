"""Verify published comparison data, preserved demo and revised assets."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://howdymary--mochi-visual-motion-v22-demo-web.us-east.modal.run/'
OLD = 'https://howdymary--mochi-inkling-v21-demo-web.us-east.modal.run/'
WEB = ROOT / 'web/desk'


def get(path):
    with urlopen(BASE + path, timeout=120) as response:
        return response.read()


def verify(item):
    file, sha = item
    payload = get(file)
    assert hashlib.sha256(payload).hexdigest() == sha, file
    return {'file': file, 'bytes': len(payload), 'sha256': sha}


health = json.loads(get('api/health'))
expected = json.loads((WEB / 'visual-motion-v22/report.json').read_text())
assert health['study'] == expected['study']
assert health['physical_attempts'] == expected['physical_attempts']
targets = {}
for mode in ['appearance', 'motion']:
    path = 'visual-motion-v22/' + mode + '-manifest.json'
    manifest = json.loads(get(path))
    assert manifest == json.loads((WEB / path).read_text())
    for scenario in manifest['scenarios']:
        for side in ['before', 'after']:
            file = scenario[side]
            normalized = 'inkling-v21/' + file.split('/')[-1] if file.startswith('../') else 'visual-motion-v22/' + file
            targets[normalized] = scenario[side + '_meta']['sha256']
    if mode == 'appearance':
        assert all(s['before_meta']['sha256'] == s['after_meta']['sha256'] for s in manifest['scenarios'])
for name in ['g1-studio.glb', 'meshopt_decoder.mjs']:
    file = 'assets/visual-motion-v22/' + name
    targets[file] = hashlib.sha256((WEB / file).read_bytes()).hexdigest()
with ThreadPoolExecutor(max_workers=4) as pool:
    files = list(pool.map(verify, targets.items()))
with urlopen(OLD + 'api/health', timeout=120) as response:
    old_health = json.load(response)
assert old_health['release'] == '55b8be47656f76b4cc0ece87e69d4c764c6a63a1'
report = {'health': health, 'preserved_demo_health': old_health, 'verified_files': files,
    'appearance_uses_identical_clips': True, 'old_release_unchanged': True}
(ROOT / 'evidence/visual-motion-v22/live-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'verified': True, 'files': len(files), 'release': health['release'], 'old_release_unchanged': True}))
