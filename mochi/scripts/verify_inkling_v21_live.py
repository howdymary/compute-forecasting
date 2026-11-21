"""Verify the deployed release and every public recording against local hashes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web/desk'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://howdymary--mochi-inkling-v21-demo-web.us-east.modal.run')
    parser.add_argument('--release')
    args = parser.parse_args()
    base = args.url.rstrip('/')

    def get(path):
        request = Request(base + path, headers={'Accept-Encoding': 'identity'})
        with urlopen(request, timeout=90) as response:
            return response.read()

    health = json.loads(get('/api/health'))
    assert health['status'] == 'ok' and health['scenarios'] == 6 and health['new_tinker_updates'] == 0
    if args.release:
        assert health['release'] == args.release
    manifest = json.loads((WEB / 'inkling-v21/manifest.json').read_text())
    assert health['controller_source_sha256'] == manifest['controller_source_sha256']
    paths = {'/': WEB / 'inkling-v21.html', '/inkling-v21.js': WEB / 'inkling-v21.js',
        '/inkling-v21/manifest.json': WEB / 'inkling-v21/manifest.json',
        '/inkling-v21/report.json': WEB / 'inkling-v21/report.json'}
    paths.update({'/inkling-v21/' + name: WEB / 'inkling-v21' / name for name in manifest['recordings']})

    def verify(item):
        path, local = item
        data = get(path)
        fingerprint = hashlib.sha256(data).hexdigest()
        assert fingerprint == hashlib.sha256(local.read_bytes()).hexdigest(), path
        if local.name in manifest['recordings']:
            assert fingerprint == manifest['recordings'][local.name]['sha256']
        return {'path': path, 'bytes': len(data), 'sha256': fingerprint, 'matches_local': True}

    with ThreadPoolExecutor(max_workers=4) as pool:
        files = list(pool.map(verify, paths.items()))
    proof = {'url': base, 'health': health, 'files': files, 'recordings_verified': len(manifest['recordings'])}
    (ROOT / 'evidence/inkling-v21/live-health.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'release': health['release'], 'files_verified': len(files), 'recordings_verified': proof['recordings_verified']}))


if __name__ == '__main__':
    main()
