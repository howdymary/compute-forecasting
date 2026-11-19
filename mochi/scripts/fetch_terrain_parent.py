"""Read two parent metadata files without extracting gigabytes of replays."""
import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def main():
    cfg = json.loads((ROOT / 'configs/terrain-v13-training.json').read_text())
    run = str(cfg['source_run'])
    repo = 'repos/howdymary/mochi-demo'
    result = subprocess.run(['gh', 'api', f'{repo}/actions/runs/{run}/artifacts'],
                            capture_output=True, text=True, check=True)
    matches = [a for a in json.loads(result.stdout)['artifacts']
               if a['name'] == 'mochi-terrain-v12-finalization-' + run and not a['expired']]
    assert len(matches) == 1
    out = Path(os.environ['MOCHI_PARENT_SOURCE'])
    out.mkdir(parents=True, exist_ok=True)
    archive = out / 'source-download.zip'
    try:
        with archive.open('wb') as stream:
            subprocess.run(['gh', 'api', f"{repo}/actions/artifacts/{matches[0]['id']}/zip"],
                           stdout=stream, stderr=subprocess.PIPE, check=True)
        sha = hashlib.sha256()
        with archive.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                sha.update(chunk)
        with zipfile.ZipFile(archive) as zipped:
            for name in ['report.json', 'checkpoint-paths.json']:
                members = [i for i in zipped.infolist() if PurePosixPath(i.filename).name == name]
                assert len(members) == 1 and members[0].file_size < 50_000_000
                (out / name).write_bytes(zipped.read(members[0]))
        (out / 'source-artifact.json').write_text(json.dumps({
            'run': run, 'artifact_id': matches[0]['id'], 'download_sha256': sha.hexdigest(),
            'extracted_files': ['report.json', 'checkpoint-paths.json']}, indent=2) + '\n')
        print('Restored completed report and private optimizer references; replay archives remain preserved.')
    finally:
        archive.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
