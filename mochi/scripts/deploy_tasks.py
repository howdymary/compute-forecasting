"""Credential-free, additive preview. Does not replace either existing app."""
from pathlib import Path
import modal

WEB=Path(__file__).resolve().parents[1]/'web/desk'
image=modal.Image.debian_slim(python_version='3.11').pip_install('fastapi==0.121.1')
for name in ['tasks.html','tasks.css','tasks.js','workspace-stage.js','task-objects.js','rig-spec.js','realism.js','g1-stage.js','desk.css','body.html','body-stage.js']:
    image=image.add_local_file(WEB/name,remote_path='/web/'+name,copy=True)
image=image.add_local_file(WEB/'tasks.html',remote_path='/web/index.html',copy=True).add_local_dir(WEB/'tasks',remote_path='/web/tasks',copy=True)
image=image.add_local_dir(WEB/'assets',remote_path='/web/assets',copy=True)
app=modal.App('mochi-desk-tasks')

@app.function(image=image,serialized=True,cpu=.25,memory=512,max_containers=2,scaledown_window=60)
@modal.asgi_app()
def web():
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    api=FastAPI()
    @api.get('/api/health')
    def health():return {'status':'ok','service':'mochi-desk-tasks','mode':'recorded MuJoCo free-base contact study','base':'six free DOFs; foot support; rigid leg pose','training':'not post-trained'}
    api.mount('/',StaticFiles(directory='/web',html=True))
    return api
