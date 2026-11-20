"""Summarize existing physical probes, including failures. Never runs physics."""
import json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'artifacts/smooth-v17-engineering';rows=[]
for f in sorted(out.glob('*.json')):
 if f.name=='grid-ledger.json' or f.stem.startswith('globe-'):continue
 d=json.loads(f.read_text());result=d.get('result') or {};recovery=d.get('recovery') or {}
 rows.append({'id':f.stem,'parameters':d.get('parameters'),'artifact':str(f.relative_to(root)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'physical_attempts':d['physical_attempts'],'wall_seconds':d['wall_seconds'],'status':d.get('status','completed'),'success':result.get('success'),'failure':d.get('error'),'task_duration':result.get('duration'),'peak_force':result.get('max_force_n'),'recovery_joint_travel':recovery.get('arm_joint_travel_rad')})
f=out/'full-reference/result.json';r=json.loads(f.read_text());rows.append({'id':'full-reference','artifact':str(f.relative_to(root)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'physical_attempts':1,'wall_seconds':r['wall_seconds'],'status':'completed','success':r['complete_sequence_success']})
assert sum(x['physical_attempts'] for x in rows)==16
base=next(x for x in rows if x['id']=='clock-matched-F');new=next(x for x in rows if x['id']=='clock-home-0007')
proof={'scope':'Controller engineering before model training. No new optimizer updates have been performed.','physical_attempts':16,'single_worker_hours':sum(x['wall_seconds'] for x in rows)/3600,'attempts':rows,
 'validated_route':{'seed':41001,'complete_sequence_success':r['complete_sequence_success'],'steps':r['episode']['steps']['attempts'],'physical_seconds':r['episode']['duration'],'recovery_joint_travel':sum(x['arm_joint_travel_rad'] for x in r['episode']['recoveries']),'all_tasks':list(r['episode']['results']),'no_applied_base_force':r['episode']['maximum_applied_base_force']==0},
 'matched_clock':{'baseline_F_R4_rad':base['recovery_joint_travel'],'home_H0_R4_rad':new['recovery_joint_travel'],'same_saved_initial_state':True},
 'selected_laptop_profile':{'code':'P4','force_n':.6,'horizon_seconds':16,'pulse':'steady','verified_global_force_limit_n':.8,'development_case':'laptop-steady-060-16s'},
 'selected_clock_profile':{'code':'H0','ik_home_regularizer_m_per_rad':.0007,'base_contact_profile':'F'},
 'failed_attempts':[{'id':x['id'],'failure':x['failure'],'success':x['success']} for x in rows if not x.get('success')],
 'limits':['Single saved-state development cases and one known complete reference, not a model or held-out result.','One early alignment failure retained only a traceback and conservative duration bound.','Native gait and task success/force/contact predicates remain unchanged.']}
p=root/'evidence/smooth-v17/engineering.json';p.parent.mkdir(exist_ok=True);assert not p.exists();p.write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({'attempts':16,'hours':proof['single_worker_hours'],'clock':proof['matched_clock'],'full_reference':proof['validated_route']}))
