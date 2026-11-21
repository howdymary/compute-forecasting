"""Separate state-based navigation viewer; existing demos remain deployed."""
import json
import os
from pathlib import Path

import modal

WEB = Path(__file__).resolve().parents[1] / 'web/desk'
REPORT = json.loads((WEB / 'navigation-v23/report.json').read_text())
preview = os.environ.get('MOCHI_DEVELOPMENT_PREVIEW') == '1'
assert (REPORT['status'] == 'completed' and REPORT['held_out_opened']) or (preview and REPORT.get('preview') and not REPORT['held_out_opened'])
assert REPORT['optimizer_updates_completed'] > 0
image = (modal.Image.debian_slim(python_version='3.11')
    .pip_install('fastapi==0.121.1')
    .env({'MOCHI_RELEASE': os.environ.get('MOCHI_RELEASE', 'local')}))
for name in ['navigation-v23.html', 'navigation-v23.js', 'navigation-v23.css', 'navigation-v23-stage.js', 'navigation-v23-renderer.js',
             'task-preflight-v24.html', 'task-preflight-v24.js', 'task-preflight-v24.json',
             'visual-motion-v22.css', 'visual-v22-stage.js', 'g1-v22-stage.js', 'realism-v22.js',
             'efficient-evidence.mjs', 'vintage-clock.js', 'richdesk-stage.js']:
    image = image.add_local_file(WEB / name, remote_path='/web/' + name, copy=True)
image = (image.add_local_file(WEB / 'navigation-v23.html', remote_path='/web/index.html', copy=True)
    .add_local_dir(WEB / 'assets', remote_path='/web/assets', copy=True)
    .add_local_dir(WEB / 'navigation-v23', remote_path='/web/navigation-v23', copy=True,
        ignore=['*.json.gz'] if REPORT.get('recording_manifest') else []))
app = modal.App('mochi-navigation-v23-demo')
recording_mounts = {'/recordings': modal.Volume.from_name('mochi-navigation-v23-artifacts').with_mount_options(
    read_only=True, sub_path='/' + REPORT['run_id'] + '/public')} if REPORT.get('recording_manifest') else {}


@app.function(image=image, serialized=True, cpu=.25, memory=512, max_containers=2, scaledown_window=120,
              volumes=recording_mounts)
@modal.asgi_app()
def web():
    from fastapi import FastAPI
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from functools import lru_cache
    import hashlib
    api = FastAPI()
    api.add_middleware(GZipMiddleware, minimum_size=1000)
    manifest = json.loads(Path('/web/navigation-v23/report.json').read_text()).get('recording_manifest', {})
    if not manifest:
        cases = json.loads(Path('/web/navigation-v23/manifest.json').read_text())['cases']
        manifest = {run['file']: {'sha256': run['row']['public_recording']['sha256']}
            for case in cases for run in case['runs'].values()}

    @lru_cache(maxsize=512)
    def verified_recording(name):
        if name not in manifest:
            raise HTTPException(404, 'No published recording with this name')
        path = (Path('/recordings') if Path('/recordings').is_dir() else Path('/web/navigation-v23')) / name
        if not path.is_file():
            raise HTTPException(503, 'Archived recording is temporarily unavailable')
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest[name]['sha256']:
            raise HTTPException(503, 'Recording integrity check failed')
        return path

    @api.get('/navigation-v23/{name}')
    def recording(name: str):
        if name.endswith('.json.gz') and manifest:
            return FileResponse(verified_recording(name), media_type='application/gzip',
                headers={'Cache-Control': 'public, max-age=31536000, immutable'})
        path = Path('/web/navigation-v23') / name
        if name not in ['manifest.json', 'report.json', 'selection-freeze.json', 'split-manifest.json', 'recording-manifest.json'] or not path.is_file():
            raise HTTPException(404)
        return FileResponse(path, media_type='application/json', headers={'Cache-Control': 'no-cache'})

    @api.get('/api/health')
    def health():
        base = Path('/web/navigation-v23')
        manifest = json.loads((base / 'manifest.json').read_text())
        report = json.loads((base / 'report.json').read_text())
        return {'status': 'ok', 'release': os.environ.get('MOCHI_RELEASE'), 'study': report['study'],
            'run_id': report['run_id'], 'cases': len(manifest['cases']),
            'preview': bool(report.get('preview')), 'evaluation_complete': report['status'] == 'completed',
            'optimizer_updates': report['optimizer_updates_completed'],
            'physical_attempts': report['actual_physical_attempts'],
            'native_gait_weights_trained': False, 'privileged_state': True,
            'mode': 'Recorded physical simulation; layout-specific parent/checkpoint comparisons'}

    api.mount('/', StaticFiles(directory='/web', html=True))
    return api
