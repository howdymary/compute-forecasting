"""Package uninterrupted engineering attempts without implying task training."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

from mochi.smooth_v16.public import rounded

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--upload-only', action='store_true')
args = parser.parse_args()
WEB = ROOT / 'web/desk'
folder = ROOT / '.cache/navigation-tasks-v24/public'
folder.mkdir(parents=True, exist_ok=True)
manifest_path = WEB / 'task-preflight-v24.json'
if not args.upload_only:
    labels = [('physical-r0-books', 'Book prefix', 'Book traversal and clock only.'),
        ('physical-r0-full', 'Initial complete-route attempt', 'Failed at the drawer; sampled joint initialization was reset.'),
        ('physical-r1-full', 'Restored initial state', 'Clock and drawer completed; printer contact on transit.'),
        ('physical-r2-full', 'Wider staging', 'Reached the laptop; the stapler obstructed its lid.'),
        ('physical-r3-full', 'Cleared laptop workspace', 'Clock, drawer and laptop completed; wrist contact on the globe transition.')]
    cases, recordings = [], {}
    for ident, label, description in labels:
        source = ROOT / 'artifacts/navigation-tasks-v24' / (ident + '.json.gz')
        raw = source.read_bytes()
        row = json.loads(gzip.decompress(raw))
        episode = row['episode']
        clip = {k: v for k, v in episode.items() if k not in ['control_telemetry', 'book_motion_samples', 'balance_measurements']}
        clip['balance_measurements'] = [{k: v for k, v in m.items() if k in ['t', 'phase', 'roll_rad', 'loads_n', 'step_category']}
            for m in episode['balance_measurements']]
        clip['model_decisions'] = episode['decisions']
        payload = gzip.compress(json.dumps(rounded(clip), separators=(',', ':')).encode(), compresslevel=6, mtime=0)
        name = 'task-preflight-' + ident + '.json.gz'
        (folder / name).write_bytes(payload)
        shutil.copyfile(folder / name, WEB / 'navigation-v23' / name)
        recordings[name] = {'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload),
            'source_trajectory': {'local_artifact': str(source.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest()},
            'scope': row['scope']}
        cases.append({'id': ident, 'label': label, 'description': description, 'file': name,
            'scene': episode['scene'], 'duration': episode['duration'], 'steps': episode['steps']['attempts'],
            'failure': row['failure'], 'qualified_complete': row['qualified_complete'],
            'tasks': {task: value['success'] for task, value in episode['results'].items()},
            'fall': episode['fall'], 'invalid_contact': episode['invalid_contact'],
            'requested_end': row['requested_end'], 'public_sha256': recordings[name]['sha256']})
    manifest = {'study': 'navigation-tasks-v24-preflight', 'task_optimizer_updates': 0,
        'default_case': 'physical-r3-full', 'cases': cases, 'recordings': recordings,
        'scope': 'Separate engineering attempts, not matched checkpoint comparisons. Every recording is uninterrupted. No concatenation, native gait training or complete four-task success is claimed.'}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    (ROOT / 'evidence/navigation-tasks-v24/recordings.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'continuous_attempts': len(cases), 'public_bytes': sum(v['bytes'] for v in recordings.values())}), flush=True)
else:
    import modal
    manifest = json.loads(manifest_path.read_text())
    volume = modal.Volume.from_name('mochi-navigation-v23-artifacts')
    with volume.batch_upload() as batch:
        for name, entry in manifest['recordings'].items():
            target = folder / name
            assert hashlib.sha256(target.read_bytes()).hexdigest() == entry['sha256']
            batch.put_file(target, '/mochi-nav23-20261121c/public/' + name)
    print(json.dumps({'uploaded': len(manifest['recordings']), 'existing_recordings_overwritten': False}))
