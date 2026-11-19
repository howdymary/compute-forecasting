"""Read only the active Mochi terrain app's metadata and recent logs."""
import gzip,json,subprocess,sys
from pathlib import Path
import modal
mode=json.loads((Path(__file__).resolve().parents[1]/'configs/terrain-v12-inspect.json').read_text()).get('study','v12')
assert mode in ['v12','v13','v15']
namespace='mochi-efficient-v15' if mode=='v15' else 'mochi-terrain-'+mode
report=modal.Dict.from_name(namespace+'-progress').get('latest',{})
print(json.dumps({**{k:report.get(k) for k in ['run_id','status','phase','optimizer_updates_completed','campaign_modal_rollouts_completed','budget_usage_or_reserved','improvement_goal_met']},
 'selected_update':(report.get('selected_checkpoint') or {}).get('update'),
 'completed_development':[{k:c.get(k) for k in ['update','development']} for c in report.get('checkpoints',[]) if c.get('development')]}),flush=True)
for row in report.get('physics_receipts',[])[-3:]:
 print(json.dumps({'latest_runtime_receipt':{k:row.get(k) for k in ['phase','group','seed','label','task']},
  'physical_rollouts':row['receipt']['physical_rollouts'],'duration_seconds':row['receipt']['duration_seconds']}),flush=True)
for row in report.get('physics_receipts',[])[:1]:
    receipt=row['receipt']
    print(json.dumps({'first_physical_receipt':{k:receipt.get(k) for k in ['physical_rollouts','duration_seconds','architecture']},
        'numerical_threads':[p.get('num_threads') for p in receipt.get('threadpools',[])]}),flush=True)
# Inspect only completed V12 evaluation archives; never sample or simulate.
recovery=report.get('recovery',{});run=recovery.get('evaluation_run')
prefixes=([f'mochi-t12-final-{x}' for x in [run,*reversed(recovery.get('previous_evaluation_runs',[]))] if x]+[report.get('run_id')]) if mode=='v12' else [report.get('run_id')]
if any(prefixes):
 volume=modal.Volume.from_name(namespace+'-artifacts')
 for record in [r for r in report.get('physics_receipts',[]) if r.get('model') or r.get('label')][-3:]:
  label=record.get('model',record.get('label'));group=record.get('group') or record['phase'];row=None
  for prefix in dict.fromkeys(p for p in prefixes if p):
   path=f"{prefix}/{group}-{record['seed']}-{label}.json.gz"
   try:raw=b''.join(volume.read_file(path))
   except FileNotFoundError:continue
   row=json.loads(gzip.decompress(raw));break
  if row is None:
   print(json.dumps({'archive_not_found':{'group':group,'seed':record['seed'],'model':label}}),flush=True);continue
  episode=row['episode']
  print(json.dumps({'completed_evaluation':{'phase':group,'model':label,'seed':row['seed'],'archive_path':path,
   'complete':row['complete_sequence_success'],'failure':row['failure'],'duration':episode['duration'],
   'tasks':{k:v['success'] for k,v in episode['results'].items()},'balance':episode['balance_metrics'],
   'steps':episode.get('steps'),'native_smoothness':episode.get('native_smoothness'),
   'forbidden_contacts':episode.get('contact_failures',[]),
   'chosen_controls':[{'domain':d['observation']['domain'],'station':d['observation'].get('station',d['observation'].get('task')),'action':d['action']} for d in row.get('model_decisions',[])]}}),flush=True)
result=subprocess.run([sys.executable,'-m','modal','app','list','--json'],capture_output=True,text=True,check=True)
names=['mochi-efficient-v15-learning'] if mode=='v15' else ['mochi-terrain-v13-continuation'] if mode=='v13' else ['mochi-terrain-v12-learning','mochi-terrain-v12-weight-evaluation']
apps=[r for r in json.loads(result.stdout) if r.get('description') in names]
active=[r for r in apps if r.get('state') not in ['stopped','stopping...']]
if not active:
 print(json.dumps({'active_terrain_app':False}));raise SystemExit(0)
app=max(active,key=lambda r:r.get('created_at',''))
print(json.dumps(app),flush=True)
subprocess.run([sys.executable,'-m','modal','app','logs',app['app_id'],'--tail','18','--timestamps'],check=True)
