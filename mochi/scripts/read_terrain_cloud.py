"""Read only the active Mochi terrain app's metadata and recent logs."""
import gzip,json,subprocess,sys
import modal
report=modal.Dict.from_name('mochi-terrain-v12-progress').get('latest',{})
print(json.dumps({k:report.get(k) for k in ['run_id','phase','optimizer_updates_completed','campaign_modal_rollouts_completed']}),flush=True)
for row in report.get('physics_receipts',[])[:1]:
    receipt=row['receipt']
    print(json.dumps({'first_physical_receipt':{k:receipt.get(k) for k in ['physical_rollouts','duration_seconds','architecture']},
        'numerical_threads':[p.get('num_threads') for p in receipt.get('threadpools',[])]}),flush=True)
# Inspect only completed V12 evaluation archives; never sample or simulate.
run=report.get('recovery',{}).get('evaluation_run')
if run:
 volume=modal.Volume.from_name('mochi-terrain-v12-artifacts')
 for record in [r for r in report.get('physics_receipts',[]) if r.get('model')][-3:]:
  path=f"mochi-t12-final-{run}/{record['phase']}-{record['seed']}-{record['model']}.json.gz"
  raw=b''.join(volume.read_file(path));row=json.loads(gzip.decompress(raw));episode=row['episode']
  print(json.dumps({'completed_evaluation':{'phase':record['phase'],'seed':row['seed'],
   'complete':row['complete_sequence_success'],'failure':row['failure'],'duration':episode['duration'],
   'tasks':{k:v['success'] for k,v in episode['results'].items()},'balance':episode['balance_metrics'],
   'forbidden_contacts':episode.get('contact_failures',[]),
   'chosen_controls':[{'domain':d['observation']['domain'],'station':d['observation'].get('station',d['observation'].get('task')),'action':d['action']} for d in row.get('model_decisions',[])]}}),flush=True)
result=subprocess.run([sys.executable,'-m','modal','app','list','--json'],capture_output=True,text=True,check=True)
apps=[r for r in json.loads(result.stdout) if r.get('description') in ['mochi-terrain-v12-learning','mochi-terrain-v12-weight-evaluation']]
active=[r for r in apps if r.get('state') not in ['stopped','stopping...']]
if not active:
 print(json.dumps({'active_terrain_app':False}));raise SystemExit(0)
app=max(active,key=lambda r:r.get('created_at',''))
print(json.dumps(app),flush=True)
subprocess.run([sys.executable,'-m','modal','app','logs',app['app_id'],'--tail','18','--timestamps'],check=True)
