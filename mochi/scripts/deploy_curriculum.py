"""Independent, credential-free checkpoint replay deployment."""
from pathlib import Path
import os
import modal
WEB=Path(__file__).resolve().parents[1]/'web/desk'
image=modal.Image.debian_slim(python_version='3.11').pip_install('fastapi==0.121.1').env({'MOCHI_RELEASE':os.environ.get('GITHUB_SHA','local')})
for name in ['curriculum.html','curriculum.css','curriculum.js','curriculum-stage.js','vintage-clock.js','g1-stage.js','realism.js','planning.html','planning.css','planning.js','richdesk-stage.js','richdesk.html','richdesk.css','richdesk.js','balanced.html','balanced.css','balanced.js']:
 image=image.add_local_file(WEB/name,remote_path='/web/'+name,copy=True)
image=image.add_local_file(WEB/'curriculum.html',remote_path='/web/index.html',copy=True).add_local_dir(WEB/'curriculum',remote_path='/web/curriculum',copy=True).add_local_dir(WEB/'assets',remote_path='/web/assets',copy=True)
image=image.add_local_dir(WEB/'planning',remote_path='/web/planning',copy=True)
image=image.add_local_dir(WEB/'richdesk',remote_path='/web/richdesk',copy=True)
image=image.add_local_dir(WEB/'balanced-v11',remote_path='/web/balanced-v11',copy=True)
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
  return {'status':'ok','study':report.get('study'),'release':os.environ.get('MOCHI_RELEASE'),'study_status':report['status'],'trained_optimizer_updates':report.get('optimizer_updates_completed',0),'mode':'recorded MuJoCo checkpoint replay','tasks':['alarm','drawer','laptop_close','globe']}
 @api.get('/api/planning')
 def planning():
  report=json.loads(Path('/web/planning/results.json').read_text())
  return {key:report.get(key) for key in ['study','status','new_tinker_optimizer_updates','route_version','storage_text']}
 @api.get('/api/validation')
 def validation():
  try:
   report=modal.Dict.from_name('mochi-curriculum-v6-validation-progress').get('latest',{})
   return {'study':'mochi-curriculum-v6','scope':'Archived V6 replication. Current V7 results are in /api/training and the manifest.',**{key:report.get(key) for key in ['status','phase','extra_optimizer_updates','remote_inference_probe_passed','modal_held_out','modal_isolated_walking','modal_rollouts_completed']}}
  except Exception:return {'status':'unavailable','phase':'See the validation execution receipt'}
 @api.get('/api/training')
 def training():
  try:
   study=json.loads(Path('/web/curriculum/manifest.json').read_text()).get('study');store='mochi-control-clearance-progress' if study=='mochi-control-v8-clearance' else 'mochi-control-v8-progress' if study=='mochi-control-v8' else 'mochi-curriculum-v7-progress';report=modal.Dict.from_name(store).get('latest',{})
   return {'study':report.get('study'),'status':report.get('status'),'phase':report.get('phase'),'new_optimizer_updates':report.get('new_optimizer_updates'),'training_study':report.get('training_study'),'optimizer_updates_completed':report.get('optimizer_updates_completed',0),'checkpoints':[{'update':c['update'],'development':c['continuous_development']} for c in report.get('checkpoints',[])],'memory':report.get('services',{}).get('eligibility',{}),'held_out':report.get('held_out')}
  except Exception:return {'status':'unavailable','phase':'See the training execution receipt'}
 @api.get('/api/balance-training')
 def balance_training():
  try:
   report=modal.Dict.from_name('mochi-balanced-v11-progress').get('latest',{})
   usage=modal.Dict.from_name('mochi-balanced-v11-budget').get('usage',report.get('budget_usage_or_reserved',{}))
   return {**{k:report.get(k) for k in ['study','status','phase','optimizer_updates_completed','checkpoints','selected_checkpoint','held_out','isolated']},'budget_usage_or_reserved':usage,'recorded_execution_summary':json.loads(Path('/web/balanced-v11/execution-index.json').read_text())}
  except Exception:return {'study':'mochi-balanced-v11','status':'unavailable','phase':'See the recorded execution evidence','optimizer_updates_completed':0}
 api.mount('/',StaticFiles(directory='/web',html=True));return api
