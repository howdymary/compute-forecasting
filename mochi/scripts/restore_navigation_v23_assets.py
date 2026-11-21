"""Restore missing pinned upstream assets; refuse to replace existing files."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--verify-only', action='store_true')
args = parser.parse_args()
mesh_root, gait_root = ROOT / 'assets/robot/g1', ROOT / 'assets/robot/g1-v11-policy'
mesh = json.loads((mesh_root / 'source.json').read_text())
gait = json.loads((gait_root / 'source.json').read_text())
items = [(mesh_root, name, sha,
    'https://raw.githubusercontent.com/' + mesh['repository'] + '/' + mesh['revision'] + '/' + mesh['path'] + '/' + name)
    for name, sha in mesh['files'].items()]
items += [(gait_root, name, value['sha256'],
    'https://huggingface.co/' + gait['repository'] + '/resolve/' + gait['revision'] + '/' + name)
    for name, value in gait['files'].items()]


def restore(item):
    root, name, expected, url = item
    relative = Path(name)
    assert not relative.is_absolute() and '..' not in relative.parts
    target = root / relative
    existed = target.exists()
    if existed:
        content = target.read_bytes()
    else:
        assert not args.verify_only, 'Missing pinned asset: ' + name
        with urlopen(Request(url, headers={'User-Agent': 'Mochi-reproduction/23'}), timeout=60) as response:
            content = response.read()
    assert hashlib.sha256(content).hexdigest() == expected, 'Asset checksum mismatch: ' + name
    if not existed:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as file:
            file.write(content)
    return {'file': str(target.relative_to(ROOT)), 'downloaded': not existed, 'bytes': len(content)}


with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(restore, items))
print(json.dumps({'verified': len(results), 'downloaded': sum(r['downloaded'] for r in results),
    'bytes': sum(r['bytes'] for r in results), 'native_gait_trained': False}))
