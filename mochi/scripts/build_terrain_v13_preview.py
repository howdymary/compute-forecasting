"""Publish a completed V13 study as a separate page, preserving the V12 demo."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True)
    a = p.parse_args()
    report = json.loads((Path(a.source) / 'report.json').read_text())
    assert report['study'] == 'mochi-terrain-v13-fresh-states'
    assert report['status'] == 'completed' and report['held_out_opened']
    folder = ROOT / 'web/desk/terrain-v13-training'
    subprocess.run([sys.executable, str(ROOT / 'scripts/build_terrain_training_preview.py'),
                    '--source', a.source, '--output', str(folder)], check=True)
    web = ROOT / 'web/desk'
    html = (web / 'terrain-trained.html').read_text().replace('terrain-trained', 'terrain-v13-trained').replace('terrain-training/', 'terrain-v13-training/')
    html = html.replace('RESUMED TINKER WEIGHTS', 'FRESH PHYSICAL TRAINING DATA')
    (web / 'terrain-v13-trained.html').write_text(html)
    js = (web / 'terrain-trained.js').read_text().replace("folder='terrain-training/'", "folder='terrain-v13-training/'")
    (web / 'terrain-v13-trained.js').write_text(js)


if __name__ == '__main__':
    main()
