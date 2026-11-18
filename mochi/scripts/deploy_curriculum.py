"""Independent, credential-free checkpoint replay deployment."""
from pathlib import Path
import modal
WEB=Path(__file__).resolve().parents[1]/'web/desk'
image=modal.Image.debian_slim(python_version='3.11').pip_install('fastapi==0.121.1')
for name in ['curriculum.html','curriculum.css','curriculum.js','curriculum-stage.js','vintage-clock.js','g1-stage.js','realism.js']:
 image=image.add_local_file(WEB/name,remote_path='/web/'+name,copy=True)
image=image.add_local_file(WEB/'curriculum.html',remote_path='/web/index.html',copy=True).add_local_dir(WEB/'curriculum',remote_path='/web/curriculum',copy=True).add_local_dir(WEB/'assets',remote_path='/web/assets',copy=True)
app=modal.App('mochi-curriculum-demo')
@app.function(image=image,serialized=True,cpu=.25,memory=512,max_containers=2,scaledown_window=120)
@modal.asgi_app()
def web():
 import json
 from fastapi import FastAPI
 from fastapi.staticfiles import StaticFiles
 from fastapi.middleware.gzip import GZipMiddleware
 api=FastAPI();api.add_middleware(GZipMiddleware,minimum_size=1000)
 @api.get('/api/health')
 def health():
  report=json.loads(Path('/web/curriculum/manifest.json').read_text())
  return {'status':'ok','study_status':report['status'],'trained_optimizer_updates':report.get('optimizer_updates_completed',0),'mode':'recorded MuJoCo checkpoint replay','tasks':['alarm','drawer','laptop_close','globe']}
 api.mount('/',StaticFiles(directory='/web',html=True));return api
