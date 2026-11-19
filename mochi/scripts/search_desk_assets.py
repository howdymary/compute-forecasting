"""Search the official Sand3D explorer; retain source metadata, never execute programs."""
import concurrent.futures
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://sandflow-sand3d-explorer.hf.space'
OUT = ROOT / 'assets/richdesk'
QUERIES = ['book', 'notebook', 'pencil', 'pen', 'mug', 'printer', 'stapler', 'glasses', 'desk lamp']


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mochi-desk-research/1.0'})
    return urllib.request.urlopen(req, timeout=30).read()


def search(term):
    params = {'q': term, 'mode': 'words', 'glb': 'true', 'limit': 60}
    if term in ['book', 'notebook', 'pencil', 'pen']:
        params.update(dataset='objaverse')
    return {'query': term, 'url': BASE + '/api/search?' + urllib.parse.urlencode(params),
            **json.loads(get(BASE + '/api/search?' + urllib.parse.urlencode(params)))}


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(search, QUERIES))
    (OUT / 'search.json').write_text(json.dumps({
        'retrieved_at': datetime.now(timezone.utc).isoformat(),
        'source': BASE, 'results': results,
        'scope': 'Metadata search; results are candidates, not claims of visual quality or simulation readiness.'
    }, indent=2) + '\n')
    for r in results:
        print(r['query'], r['total'], [(x['id'], x['name']) for x in r['items'][:14]])
