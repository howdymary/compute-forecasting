"""Read completed development archives while the training workflow is running."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', default='mochi-p19r1-44847672231')
    p.add_argument('--output', default=str(ROOT / '.cache/paperfree-v19r1-preview'))
    a = p.parse_args()
    report = modal.Dict.from_name('mochi-paperfree-v19r1-progress').get(a.run)
    assert report['status'] == 'running' and not report.get('held_out')
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    volume = modal.Volume.from_name('mochi-paperfree-v19r1-artifacts')
    exported = []
    for cp in report['checkpoints']:
        if cp['development'] is None:
            continue
        update = cp['update']
        if update == 0:
            raw = (ROOT / '.cache/paperfree-v19-stopped/checkpoint-0.json').read_bytes()
            (out / 'checkpoint-0.json').write_bytes(raw)
            continue
        rows = []
        for seed in report['protocol']['development_seeds']:
            archive_path = f'{a.run}/dev-{update}-{seed}-policy.json.gz'
            target = ROOT / f'.cache/paperfree-v19r1-dev-{update}-{seed}.json.gz'
            if not target.exists():
                with target.open('wb') as stream:
                    for chunk in volume.read_file(archive_path):
                        stream.write(chunk)
            raw = gzip.decompress(target.read_bytes())
            row = json.loads(raw)
            assert row['seed'] == seed
            row['archive'] = {'volume': 'mochi-paperfree-v19r1-artifacts', 'path': archive_path,
                'uncompressed_sha256': sha(raw)}
            clip_path = f'{a.run}/public/dev-{update}-{seed}-policy.json.gz'
            clip = ROOT / f'web/desk/paperfree-v19/development-{seed}-{update}.json.gz'
            if not clip.exists():
                with clip.open('wb') as stream:
                    for chunk in volume.read_file(clip_path):
                        stream.write(chunk)
            packed = clip.read_bytes()
            decoded = gzip.decompress(packed)
            episode = json.loads(decoded)
            assert episode['scenario']['seed'] == seed
            assert episode['steps']['attempts'] == row['episode']['steps']['attempts']
            assert abs(episode['duration'] - row['episode']['duration']) < .0000011
            assert not episode['paper_geometry_present']
            row['public_recording'] = {'volume': 'mochi-paperfree-v19r1-artifacts', 'path': clip_path,
                'sha256': sha(packed), 'uncompressed_sha256': sha(decoded), 'bytes': len(packed)}
            for name in ['trajectory', 'balance_measurements', 'control_telemetry']:
                row['episode'].pop(name, None)
            rows.append(row)
        (out / f'checkpoint-{update}.json').write_text(json.dumps(rows, indent=2) + '\n')
        exported.append(update)
    report['preview_export'] = {'source': 'Authenticated immutable Modal archives and their public trajectory exports',
        'scope': 'Development evidence only. Official workflow descriptors will be checked again after completion.',
        'completed_development_updates': exported}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'updates': exported, 'source': str(out), 'held_out_opened': report['held_out_opened']}))


if __name__ == '__main__':
    main()
