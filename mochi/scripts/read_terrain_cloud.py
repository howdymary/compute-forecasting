"""Read only the active Mochi terrain app's metadata and recent logs."""
import json,subprocess,sys
import modal
report=modal.Dict.from_name('mochi-terrain-v12-progress').get('latest',{})
print(json.dumps({k:report.get(k) for k in ['run_id','phase','optimizer_updates_completed','campaign_modal_rollouts_completed']}),flush=True)
for row in report.get('physics_receipts',[])[:1]:
    receipt=row['receipt']
    print(json.dumps({'first_physical_receipt':{k:receipt.get(k) for k in ['physical_rollouts','duration_seconds','architecture']},
        'numerical_threads':[p.get('num_threads') for p in receipt.get('threadpools',[])]}),flush=True)
result=subprocess.run([sys.executable,'-m','modal','app','list','--json'],capture_output=True,text=True,check=True)
apps=[r for r in json.loads(result.stdout) if r.get('description')=='mochi-terrain-v12-learning']
active=[r for r in apps if r.get('state') not in ['stopped','stopping...']]
if not active:
 print(json.dumps({'active_terrain_app':False}));raise SystemExit(0)
app=max(active,key=lambda r:r.get('created_at',''))
print(json.dumps(app),flush=True)
subprocess.run([sys.executable,'-m','modal','app','logs',app['app_id'],'--tail','18','--timestamps'],check=True)
