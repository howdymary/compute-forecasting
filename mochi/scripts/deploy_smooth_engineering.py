"""Independent physical-route preview while checkpoint training runs."""
import os
from pathlib import Path

import modal

WEB=Path(__file__).resolve().parents[1]/'web/desk'
image=(modal.Image.debian_slim(python_version='3.11').pip_install('fastapi==0.121.1')
    .env({'MOCHI_RELEASE':os.environ.get('GITHUB_SHA','local')}))
for name in ['curriculum-stage.js','g1-stage.js','vintage-clock.js','realism.js','richdesk-stage.js','richdesk.css','balanced.css']:
    image=image.add_local_file(WEB/name,remote_path='/web/'+name,copy=True)
image=(image.add_local_file(WEB/'smooth-engineering.html',remote_path='/web/index.html',copy=True)
    .add_local_dir(WEB/'assets',remote_path='/web/assets',copy=True)
    .add_local_dir(WEB/'smooth-v16-engineering',remote_path='/web/smooth-v16-engineering',copy=True,ignore=['*.json']))
# The viewer reads gzip recordings. Its manifest is deliberately not required.
app=modal.App('mochi-smooth-v16-engineering')


@app.function(image=image,serialized=True,cpu=.25,memory=512,max_containers=1,scaledown_window=120)
@modal.asgi_app()
def web():
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    api=FastAPI()
    @api.get('/api/health')
    def health():
        return {'status':'ok','release':os.environ.get('MOCHI_RELEASE'),
            'mode':'Recorded physical controller engineering','new_tinker_updates':0,
            'training_run':44669222147,'recordings':['continuous-route-7','continuous-route-8']}
    api.mount('/',StaticFiles(directory='/web',html=True))
    return api
