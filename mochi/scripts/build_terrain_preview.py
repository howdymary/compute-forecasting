"""Publish one complete engineering reference; no invented trained checkpoint."""
import gzip,hashlib,json
from pathlib import Path
from build_balanced_training_preview import rounded
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'web/desk/terrain-engineering';out.mkdir(parents=True,exist_ok=True)
p=ROOT/'artifacts/terrain-v12/continuous-four-task-reference-2.json'
row=json.loads(p.read_text());assert row['complete_sequence_success']
e=row['episode'];keep=['scenario','scene','events','results','fall','invalid_contact','duration','maximum_applied_base_force','balance_metrics','foot_slip_estimate_m','final_object_states','final_object_speeds','trajectory','recoveries','decisions']
clip={k:e[k] for k in keep if k in e}
clip['balance_measurements']=[{k:v for k,v in m.items() if k in ['t','phase','gait_phase','roll_rad','loads_n','lateral_m']} for m in e['balance_measurements']]
file='reference-41001.json.gz';payload=gzip.compress(json.dumps(rounded(clip),separators=(',',':')).encode(),compresslevel=9);(out/file).write_bytes(payload)
manifest={'study':'mochi-terrain-v12','scope':'Classical controller engineering; not a trained checkpoint improvement','file':file,'sha256':hashlib.sha256(payload).hexdigest(),'original_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scene':e['scene'],'complete':True,'seed':row['seed'],'duration_s':e['duration'],'source_sha':'48f0f4f630c6632f0a0b5f1435eaa795055c75c7','local_complete_references':2,'engineering_reference_ids':['continuous-four-task-reference-0','continuous-four-task-reference-2'],'training_workflow':'https://github.com/howdymary/mochi-demo/actions/runs/44472186998','research_workflow':'https://github.com/howdymary/mochi-demo/actions/runs/44469500205','note':'Measured MuJoCo body poses, displayed at recorded time with six-decimal quantization. No unstable motion is filtered.'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Exported complete engineering run:',len(payload),'bytes')
