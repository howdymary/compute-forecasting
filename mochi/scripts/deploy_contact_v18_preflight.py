"""Publish the actual fixed preflight while checkpoint evaluation continues."""
import os
from pathlib import Path
import modal

WEB=Path(__file__).resolve().parents[1]/'web/desk'
image=(modal.Image.debian_slim(python_version='3.11')
       .pip_install('fastapi==0.121.1')
       .env({'MOCHI_RELEASE':os.environ.get('GITHUB_SHA','local')}))
for name in ['contact-v18-preflight.html','contact-v18-preflight.js','contact-v18.css',
             'efficient-evidence.mjs','smooth-stage.js','g1-stage.js','vintage-clock.js',
             'realism.js','richdesk-stage.js','richdesk.css','balanced.css']:
    image=image.add_local_file(WEB/name,remote_path='/web/'+name,copy=True)
image=(image.add_local_file(WEB/'contact-v18-preflight.html',remote_path='/web/index.html',copy=True)
       .add_local_dir(WEB/'assets',remote_path='/web/assets',copy=True)
       .add_local_dir(WEB/'contact-v18',remote_path='/web/contact-v18',copy=True))
app=modal.App('mochi-contact-v18-demo')

@app.function(image=image,serialized=True,cpu=.25,memory=512,max_containers=2,scaledown_window=120)
@modal.asgi_app()
def web():
    import json
    from fastapi import FastAPI
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.staticfiles import StaticFiles
    api=FastAPI();api.add_middleware(GZipMiddleware,minimum_size=1000)
    @api.get('/api/health')
    def health():
        meta=json.loads(Path('/web/contact-v18/preflight-manifest.json').read_text())
        return {'status':'ok','release':os.environ.get('MOCHI_RELEASE'),'study':meta['study'],
                'mode':meta['mode'],'new_tinker_updates':0,'recorded_source_sha':meta['source_sha'],
                'seed':meta['seed'],'complete':meta['complete'],'qualified':meta['qualified'],
                'execution_workflow_run':meta['execution_workflow_run']}
    api.mount('/',StaticFiles(directory='/web',html=True));return api
