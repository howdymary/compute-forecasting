"""Publish actual V8 physics recordings with no invented motion or model claims."""
import argparse,copy,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--run-id',required=True);a=p.parse_args();root=Path(__file__).resolve().parents[1];out=root/'web/desk/curriculum';report=json.load(open(a.source/'report.json'));assert report['status']=='completed';selected=report['selected_checkpoint']['update'];dev=report['protocol']['development_seeds'][0]
def clean(v):
 if isinstance(v,float):return round(v,6)
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
 if isinstance(v,list):return [clean(x) for x in v]
 return v
def write(name,v):(out/name).write_text(json.dumps(clean(v),separators=(',',':')))
def export(name,row,update):
 ep=copy.deepcopy(row['episode']);ep.pop('control_telemetry',None);ep['full_sequence_verified']=row['full_success'];ep['reference_tracking']=row.get('path_trace',[])
 for f in ep['trajectory']['frames']:
  if f['phase']!='recover':continue
  event=next((e for e in ep['events'] if e.get('phase')=='recover' and e['t']-e['duration_s']-.002<=f['t']<=e['t']+.002),None)
  if event:f['recovery_task']=event['task'];f['recovery_action']=event['action']
 write(name,ep);trace=name.replace('.json','-decisions.json');write(trace,{'seed':row['seed'],'checkpoint_update':update,'decisions':row['model_decisions'],'inference':row['inference'],'scope':'Actual model-scored choices; identical encoded observations reuse the same fixed-checkpoint distribution. No heuristic fallback.'});return trace
old=json.load(open(out/'manifest.json'))
if old.get('study')=='mochi-curriculum-v7' and not(out/'manifest-v7.json').exists():shutil.copyfile(out/'manifest.json',out/'manifest-v7.json')
m={k:report[k] for k in ['study','status','source_sha','optimizer_updates_completed','held_out','rollouts','training_log','selected_checkpoint','protocol','research_allocation','data_audit','evaluation_runtime','paired_outcomes']};m.update(selected_update=selected,parent_optimizer_updates=96,development_seed=dev,default_view='checkpoints',checkpoints=[],workflow_url=f'https://github.com/howdymary/mochi-demo/actions/runs/{a.run_id}',scope=report['scope'],route_file='v8-route.json',plot_file='v8-checkpoint-results.svg',legacy_original_stack=report.get('legacy_original_stack'),training_counts={d:sum(x['domain_counts'][d] for x in report['training_log']) for d in ['walk','alarm','drawer','laptop','globe','recovery']});write('v8-route.json',json.load(open(root/'configs/desk-route-v8.json')))
for cp in report['checkpoints']:
 row=next(x for x in json.load(open(a.source/f"checkpoint-{cp['update']}.json")) if x['seed']==dev);name=f"v8-checkpoint-{cp['update']}.json";trace=export(name,row,cp['update']);m['checkpoints'].append({**cp,'file':name,'trace_file':trace})
m['fresh']={'cases':[]}
for seed in report['protocol']['held_out_seeds']:
 pair={'seed':seed}
 for key,label in [('before','starting_model'),('after','post_trained_model')]:
  row=next(x for x in json.load(open(a.source/f'held-out-{label}.json')) if x['seed']==seed);name=f'v8-held-out-{seed}-{key}.json';pair[key]=name;pair[key+'_trace']=export(name,row,0 if key=='before' else selected)
 m['fresh']['cases'].append(pair)
m['fresh'].update(m['fresh']['cases'][0]);successful=[x for x in report['paired_outcomes'] if x['trained_full']]
if successful:m['showcase']={**next(x for x in m['fresh']['cases'] if x['seed']==successful[0]['seed']),'selection':'Successful example chosen after evaluation for presentation. Every held-out attempt remains available; this is not an average result.'}
services=report['services'];m['memory']=services['eligibility'];m['search_calls']=len(services['sources']);m['sources']=list({s['url']:s for r in services['sources'] for s in r['sources']}.values());records={r['id']:r for r in services['records']};m['memory_handoffs']=[]
for r in services['reads']:
 if not r['cross_agent_use'] or not r['source_id_verified'] or r['record_id'] not in records:continue
 record=records[r['record_id']];m['memory_handoffs'].append({'record_id':record['id'],'author_role':record['role'],'reader_role':r['reader_role'],'kind':record['payload']['content']['kind'],'decisions':[{'selected':d['selected']} for d in services['decisions'] if record['id'] in d['input_record_ids']]})
calls=services['calls'];m['memory_usage']={'writes':sum(c['method']=='POST' and c['kind']=='ingest' for c in calls),'recalls':sum(c['method']=='POST' and c['kind']=='recall' for c in calls),'ingestion_polls':sum(c['method']=='GET' and c['kind']=='ingest' for c in calls)};write('manifest-v8.json',m);write('manifest.json',m)
evidence=root/'evidence/control-v8';evidence.mkdir(parents=True,exist_ok=True);public={k:v for k,v in report.items() if k not in ['services','last_hypothesis']};public['search']=services['sources'];public['memory']={k:services[k] for k in ['audiences','reads','decisions','eligibility','calls']};public['workflow_url']=m['workflow_url'];text=json.dumps(public,indent=2);assert 'tinker://' not in text and 'api_key' not in text.lower();(evidence/'results.json').write_text(text+'\n');print(json.dumps({'selected_update':selected,'checkpoints':len(m['checkpoints']),'test_pairs':len(m['fresh']['cases']),'held_out':m['held_out']},indent=2))
