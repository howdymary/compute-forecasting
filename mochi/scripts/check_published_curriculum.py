"""Validate physical provenance and model decisions behind the public replay."""
import json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];public=root/'web/desk/curriculum';source=root/'artifacts/curriculum';manifest=json.loads((public/'manifest.json').read_text());report=json.loads((source/'reference-report.json').read_text());traces={};checks=[]
assert manifest['optimizer_updates_completed']==64 and len(manifest['training_log'])==64
assert all(e['optimizer_completed'] and e['forward_backward_completed'] and set(e['domain_counts'])=={'walk','alarm','drawer','laptop','globe'} for e in manifest['training_log'])
initial=None
for cp in manifest['checkpoints']:
 ep=json.loads((public/cp['file']).read_text());assert ep['scenario']['seed']==manifest['development_seed'];frame=ep['trajectory']['frames'][0]
 if initial is None:initial=frame
 else:assert frame==initial
 assert all(a['t']<b['t'] for a,b in zip(ep['trajectory']['frames'],ep['trajectory']['frames'][1:]));checks.append({'checkpoint':cp['update'],'same_development_initial_state':True,'strictly_increasing_simulation_time':True})
for case in manifest['fresh']['cases']:
 a=json.loads((public/case['before']).read_text());b=json.loads((public/case['after']).read_text());assert a['scenario']['seed']==b['scenario']['seed']==case['seed'];assert a['trajectory']['frames'][0]==b['trajectory']['frames'][0]
for label in ['starting_model','post_trained_model']:
 row=next(x for x in json.loads((source/('held-out-'+label+'.json')).read_text()) if x['seed']==14001);decisions=row['model_decisions'];assert [d['action'] for d in decisions]==row['actions']==[d['action'] for d in row['episode']['decisions']]
 assert all(max(d['distribution'],key=d['distribution'].get)==d['action'] for d in decisions);traces[label]={'update':0 if label=='starting_model' else 64,'seed':14001,'decisions':decisions,'actions_sha256':hashlib.sha256(json.dumps(row['actions']).encode()).hexdigest()}
assert traces['starting_model']['decisions'][0]['observation']==traces['post_trained_model']['decisions'][0]['observation']
iso=json.loads((source/'held-out-isolated-evaluation.json').read_text());contact=[]
for before in iso['starting_model']:
 after=next(r for r in iso['post_trained_model'] if r['seed']==before['seed'] and r['result']['task']==before['result']['task']);assert before['observation']==after['observation'];contact.append({'seed':before['seed'],'task':before['result']['task'],'same_observation':True,'starting_profile':before['result']['profile']['code'],'trained_profile':after['result']['profile']['code'],'starting_success':before['result']['success'],'trained_success':after['result']['success']})
audit={'scope':'Measured reference-run data; no model or simulation behavior was changed by these checks.','optimizer_updates':64,'gradient_domains_per_update':5,'actual_training_example_counts':manifest['training_counts'],'checkpoint_checks':checks,'fresh_scenarios_with_identical_initial_states':len(manifest['fresh']['cases']),'first_walking_decision':{k:{'action':r['decisions'][0]['action'],'distribution':r['decisions'][0]['distribution']} for k,r in traces.items()},'isolated_contact_pairs':contact,'showcase_selection':manifest['showcase']['selection']}
(public/'model-decisions-14001.json').write_text(json.dumps(traces,separators=(',',':')));(public/'provenance-checks.json').write_text(json.dumps(audit,indent=2));out=root/'evidence/curriculum-v6';out.mkdir(exist_ok=True,parents=True);(out/'provenance-checks.json').write_text(json.dumps(audit,indent=2));print(json.dumps({'checks':'passed','first_walking_decision':audit['first_walking_decision'],'laptop_profiles':[r for r in contact if r['task']=='laptop']},indent=2))
