"""Additive appearance/motion viewer. Does not replace any existing Mochi app."""
import os
import json
from pathlib import Path

import modal

WEB = Path(__file__).resolve().parents[1] / 'web/desk'
assert json.loads((WEB / 'visual-motion-v22/report.json').read_text())['evaluation_complete'], 'Finish physical evaluation before deployment'
image = (modal.Image.debian_slim(python_version='3.11')
    .pip_install('fastapi==0.121.1')
    .env({'MOCHI_RELEASE': os.environ.get('GITHUB_SHA', 'local')}))
for name in ['visual-motion-v22.html', 'visual-motion-v22.js', 'visual-motion-v22.css',
             'visual-v22-stage.js', 'g1-v22-stage.js', 'realism-v22.js',
             'efficient-evidence.mjs', 'smooth-stage.js', 'curriculum-stage.js', 'g1-stage.js',
             'vintage-clock.js', 'realism.js', 'richdesk-stage.js', 'richdesk.css', 'balanced.css']:
    image = image.add_local_file(WEB / name, remote_path='/web/' + name, copy=True)
image = (image.add_local_file(WEB / 'visual-motion-v22.html', remote_path='/web/index.html', copy=True)
    .add_local_dir(WEB / 'assets', remote_path='/web/assets', copy=True)
    .add_local_dir(WEB / 'visual-motion-v22', remote_path='/web/visual-motion-v22', copy=True)
    .add_local_dir(WEB / 'inkling-v21', remote_path='/web/inkling-v21', copy=True))
app = modal.App('mochi-visual-motion-v22-demo')


@app.function(image=image, serialized=True, cpu=.25, memory=512, max_containers=2, scaledown_window=120)
@modal.asgi_app()
def web():
    import json
    from fastapi import FastAPI
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.staticfiles import StaticFiles

    api = FastAPI()
    api.add_middleware(GZipMiddleware, minimum_size=1000)

    @api.get('/api/health')
    def health():
        base = Path('/web/visual-motion-v22')
        appearance = json.loads((base / 'appearance-manifest.json').read_text())
        motion = json.loads((base / 'motion-manifest.json').read_text())
        report = json.loads((base / 'report.json').read_text())
        return {'status': 'ok', 'release': os.environ.get('MOCHI_RELEASE'), 'study': report['study'],
            'appearance_cases': len(appearance['scenarios']), 'motion_cases': len(motion['scenarios']),
            'physical_attempts': report['physical_attempts'], 'optimizer_updates': 0,
            'evaluation_complete': report['evaluation_complete'],
            'mode': 'Recorded simulation; appearance and motion compared separately; original demo preserved'}

    api.mount('/', StaticFiles(directory='/web', html=True))
    return api
