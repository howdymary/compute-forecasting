"""Independent, credential-free checkpoint replay deployment."""
from pathlib import Path
import os
import modal
WEB=Path(__file__).resolve().parents[1]/'web/desk'
image=modal.Image.debian_slim(python_version='3.11').pip_install('fastapi==0.121.1').env({'MOCHI_RELEASE':os.environ.get('GITHUB_SHA','local')})
for name in ['curriculum.html','curriculum.css','curriculum.js','curriculum-stage.js','vintage-clock.js','g1-stage.js','realism.js']:
 image=image.add_local_file(WEB/name,remote_path='/web/'+name,copy=True)
image=image.add_local_file(WEB/'curriculum.html',remote_path='/web/index.html',copy=True).add_local_dir(WEB/'curriculum',remote_path='/web/curriculum',copy=True).add_local_dir(WEB/'assets',remote_path='/web/assets',copy=True)
app=modal.App('mochi-curriculum-demo')
@app.function(image=image,serialized=True,cpu=.25,memory=512,max_containers=2,scaledown_window=120)
@modal.asgi_app()
def web():
 import json,os
 from fastapi import FastAPI
 from fastapi.staticfiles import StaticFiles
 from fastapi.middleware.gzip import GZipMiddleware
 api=FastAPI();api.add_middleware(GZipMiddleware,minimum_size=1000)
 @api.get('/api/health')
 def health():
  report=json.loads(Path('/web/curriculum/manifest.json').read_text())
  return {'status':'ok','release':os.environ.get('MOCHI_RELEASE'),'study_status':report['status'],'trained_optimizer_updates':report.get('optimizer_updates_completed',0),'mode':'recorded MuJoCo checkpoint replay','tasks':['alarm','drawer','laptop_close','globe']}
 @api.get('/api/validation')
 def validation():
  try:
   report=modal.Dict.from_name('mochi-curriculum-v6-validation-progress').get('latest',{})
   return {key:report.get(key) for key in ['status','phase','extra_optimizer_updates','remote_inference_probe_passed','modal_held_out','modal_isolated_walking','modal_rollouts_completed']}
  except Exception:return {'status':'unavailable','phase':'See the validation execution receipt'}
 @api.get('/api/training')
 def training():
  try:
   report=modal.Dict.from_name('mochi-curriculum-v7-progress').get('latest',{})
   return {'study':report.get('study'),'status':report.get('status'),'phase':report.get('phase'),'optimizer_updates_completed':report.get('optimizer_updates_completed',0),'checkpoints':[{'update':c['update'],'development':c['continuous_development']} for c in report.get('checkpoints',[])],'memory':report.get('services',{}).get('eligibility',{}),'held_out':report.get('held_out')}
  except Exception:return {'status':'unavailable','phase':'See the training execution receipt'}
 api.mount('/',StaticFiles(directory='/web',html=True));return api
