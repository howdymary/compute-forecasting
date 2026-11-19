"""Fetch selected licensed Sand3D meshes; do not execute dataset programs."""
import concurrent.futures
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/richdesk'
BASE = 'https://sandflow-sand3d-explorer.hf.space'
REPO = 'Sandflow/sand3d-explorer-assets'
SELECTED = {
    'book': 'objaverse-6c2e5ccb27cf459892d1329ebf0b682f',
    'notebook': 'objaverse-07141ec4d54b4485be1819a52e8ce7f6',
    'pencil': 'objaverse-cf6d456a59814605a18d983ef26453d8',
    'pen': 'objaverse-8760a14500c7487d82790f18fe5c5540',
    'mug': 'objaverse-13cb5f6c327c4aeabe1f4690dbe73838',
    'printer': 'articraft-rec_all_in_one_printer_with_scanner_lid_and_paper_tray_2fa487f194524ba7b35fc345b2252469',
    'stapler': 'articraft-rec_desktop_stapler_with_hinged_top_arm_6d603e7d424e4a7095ad88946eb09294',
    'glasses': 'articraft-rec_glasses_2cc81dbe846f430a96a5444d1ef4bf55',
}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={
        'User-Agent': 'Mochi-desk-research/1.0'}), timeout=45).read()


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'source').mkdir(exist_ok=True)
    (OUT / 'previews').mkdir(exist_ok=True)
    previous = {r['key']: r for r in json.loads((OUT / 'selected.json').read_text())['records']} if (OUT / 'selected.json').exists() else {}
    def fetch(item):
        name, oid = item
        cached = previous.get(name)
        path = OUT / 'source' / (name + '.glb')
        if cached and cached['id'] == oid and path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == cached['source_sha256']:
            return cached
        record = json.loads(get(BASE + '/api/object/' + oid))
        assert record['license_status'] == 'ok' and record['glb']
        # Use the public download URL returned by the official explorer. Its
        # backing cache repository is not publicly readable through the Hub API.
        url = BASE + record['glb_url']
        mesh = get(url)
        assert mesh[:4] == b'glTF'
        (OUT / 'source' / (name + '.glb')).write_bytes(mesh)
        (OUT / 'previews' / (name + '.png')).write_bytes(get(BASE + '/r/' + oid + '.png'))
        record.pop('program', None)
        return {**record, 'key': name, 'asset_repository': REPO,
                'download_url': url, 'source_sha256': hashlib.sha256(mesh).hexdigest(),
                'source_bytes': len(mesh), 'source_page': BASE + '/o/' + oid}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(fetch, SELECTED.items()))
    (OUT / 'selected.json').write_text(json.dumps({
        'retrieved_at': datetime.now(timezone.utc).isoformat(), 'records': records,
        'execution': 'Only GLB geometry and source metadata downloaded. Dataset Python programs are not executed.'
    }, indent=2) + '\n')
    print([(r['key'], r['name'], r['source_bytes'], r['license']) for r in records])
