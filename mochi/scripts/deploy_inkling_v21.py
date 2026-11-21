"""Independent Inkling controller-research demo; archived viewers stay intact."""
import os
from pathlib import Path

import modal

WEB = Path(__file__).resolve().parents[1] / 'web/desk'
image = (modal.Image.debian_slim(python_version='3.11')
         .pip_install('fastapi==0.121.1')
         .env({'MOCHI_RELEASE': os.environ.get('GITHUB_SHA', 'local')}))
for name in ['inkling-v21.html', 'inkling-v21.js', 'paperfree-v19.css', 'efficient-evidence.mjs', 'smooth-stage.js', 'curriculum-stage.js', 'g1-stage.js',
             'vintage-clock.js', 'realism.js', 'richdesk-stage.js', 'richdesk.css', 'balanced.css']:
    image = image.add_local_file(WEB / name, remote_path='/web/' + name, copy=True)
image = (image.add_local_file(WEB / 'inkling-v21.html', remote_path='/web/index.html', copy=True)
         .add_local_dir(WEB / 'assets', remote_path='/web/assets', copy=True)
         .add_local_dir(WEB / 'inkling-v21', remote_path='/web/inkling-v21', copy=True))
app = modal.App('mochi-inkling-v21-demo')


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
        report = json.loads(Path('/web/inkling-v21/manifest.json').read_text())
        return {'status': 'ok', 'release': os.environ.get('MOCHI_RELEASE'), 'study': report['study'],
                'scenarios': len(report['scenarios']), 'new_tinker_updates': report['optimizer_updates_completed'],
                'evaluation_status': report['evaluation_status'], 'selection_finalized':report['selection_finalized'],
                'selected_update':report['selected_update'] if report['selection_finalized'] else None,
                'displayed_update':report['selected_update'], 'goal_met':report['improvement_goal_met'],
                'controller_source_sha256': report['controller_source_sha256'],
                'mode': 'recorded MuJoCo controller-engineering comparison; zero new weight updates'}

    api.mount('/', StaticFiles(directory='/web', html=True))
    return api
