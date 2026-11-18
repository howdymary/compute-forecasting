"""Publish actual V8 physics recordings with no invented motion or model claims."""
import argparse,copy,json,shutil
from pathlib import Path
from control_evidence import completed_report
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--revision',choices=['v8','clearance'],default='v8');p.add_argument('--run-id',required=True);p.add_argument('--isolated-source',type=Path);a=p.parse_args();root=Path(__file__).resolve().parents[1];out=root/'web/desk/curriculum';report=completed_report(a.source);assert report['status']=='completed';revision=a.revision;selected=report['selected_checkpoint']['update'];dev=report['protocol']['development_seeds'][0]
def clean(v):
 if isinstance(v,float):return round(v,6)
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
 if isinstance(v,list):return [clean(x) for x in v]
 return v
def write(name,v):(out/name).write_text(json.dumps(clean(v),separators=(',',':')))
def export(name,row,update):
 ep=copy.deepcopy(row['episode']);ep.pop('control_telemetry',None);ep['decisions']=[{k:d[k] for k in ['t','observation','action']} for d in row['model_decisions']];ep['full_sequence_verified']=row['full_success'];ep['stop_reason']=row.get('failure');ep['stations_reached']=len(row['arrivals']);ep['reference_tracking']=row.get('path_trace',[])
 for f in ep['trajectory']['frames']:
  if f['phase']!='recover':continue
  event=next((e for e in ep['events'] if e.get('phase')=='recover' and e['t']-e['duration_s']-.002<=f['t']<=e['t']+.002),None)
  if event:f['recovery_task']=event['task'];f['recovery_action']=event['action']
 write(name,ep);trace=name.replace('.json','-decisions.json');write(trace,{'seed':row['seed'],'checkpoint_update':update,'decisions':row['model_decisions'],'inference':row['inference'],'scope':'Actual model-scored choices; identical encoded observations reuse the same fixed-checkpoint distribution. No heuristic fallback.'});return trace
isolated=json.load(open(a.isolated_source/'report.json')) if a.isolated_source else json.load(open(a.source/'isolated-report.json')) if (a.source/'isolated-report.json').exists() else None
old=json.load(open(out/'manifest.json'))
if old.get('study')=='mochi-curriculum-v7' and not(out/'manifest-v7.json').exists():shutil.copyfile(out/'manifest.json',out/'manifest-v7.json')
m={k:report[k] for k in ['study','status','source_sha','optimizer_updates_completed','held_out','rollouts','training_log','selected_checkpoint','protocol','research_allocation','data_audit','evaluation_runtime','paired_outcomes']};m.update(selected_update=selected,parent_optimizer_updates=96,development_seed=dev,default_view='checkpoints',checkpoints=[],workflow_url=f'https://github.com/howdymary/mochi-demo/actions/runs/{a.run_id}',scope=report['scope'],route_file=revision+'-route.json',plot_file=revision+'-checkpoint-results.svg',legacy_original_stack=report.get('legacy_original_stack'),training_counts={d:sum(x['domain_counts'][d] for x in report['training_log']) for d in ['walk','alarm','drawer','laptop','globe','recovery']});write(revision+'-route.json',json.load(open(root/'configs'/('desk-route-clearance.json' if revision=='clearance' else 'desk-route-v8.json'))));m.update({k:report.get(k) for k in ['training_reused','training_study','new_optimizer_updates','training_workflow_url','evaluation_workflow_url','engineering_revision','new_modal_rollouts','source_training_rollouts']})
m['development_cases']=report['protocol']['development_seeds']
for cp in report['checkpoints']:
 rows=json.load(open(a.source/f"checkpoint-{cp['update']}.json"));cases=[]
 for seed in m['development_cases']:
  row=next(x for x in rows if x['seed']==seed);name=f"{revision}-checkpoint-{cp['update']}"+('' if seed==dev else f'-seed-{seed}')+'.json';trace=export(name,row,cp['update']);cases.append({'seed':seed,'file':name,'trace_file':trace})
 m['checkpoints'].append({**cp,'file':cases[0]['file'],'trace_file':cases[0]['trace_file'],'cases':cases})
m['fresh']={'cases':[]}
for seed in report['protocol']['held_out_seeds']:
 pair={'seed':seed}
 for key,label in [('before','starting_model'),('after','post_trained_model')]:
  row=next(x for x in json.load(open(a.source/f'held-out-{label}.json')) if x['seed']==seed);name=f'{revision}-held-out-{seed}-{key}.json';pair[key]=name;pair[key+'_trace']=export(name,row,0 if key=='before' else selected)
 m['fresh']['cases'].append(pair)
m['fresh'].update(m['fresh']['cases'][0]);successful=[x for x in report['paired_outcomes'] if x['trained_full']]
m['full_route_timing']={}
for label in ['starting_model','post_trained_model','classical_fixed']:
 rows=json.load(open(a.source/f'held-out-{label}.json'));times=[x['episode']['duration'] for x in rows if x['full_success']];m['full_route_timing'][label]={'completed':len(times),'attempted':len(rows),'mean_simulation_seconds':sum(times)/len(times) if times else None,'scope':'Completed full routes only; remote inference waiting time excluded.'}
if successful:m['default_view']='showcase';m['presentation_rule']='Default: first successful held-out seed, chosen after evaluation and explicitly labeled. All four outcomes remain visible. Checkpoint view uses the first declared development seed.';m['showcase']={**next(x for x in m['fresh']['cases'] if x['seed']==successful[0]['seed']),'selection':'Successful example chosen after evaluation for presentation. Every held-out attempt remains available; this is not an average result.'}
services=report['services'];m['memory']=services['eligibility'];m['search_calls']=len(services['sources']);m['sources']=list({s['url']:s for r in services['sources'] for s in r['sources']}.values());records={r['id']:r for r in services['records']};m['memory_handoffs']=[]
for r in services['reads']:
 if not r['cross_agent_use'] or not r['source_id_verified'] or r['record_id'] not in records:continue
 record=records[r['record_id']];m['memory_handoffs'].append({'record_id':record['id'],'author_role':record['role'],'reader_role':r['reader_role'],'kind':record['payload']['content']['kind'],'decisions':[{'selected':d['selected']} for d in services['decisions'] if record['id'] in d['input_record_ids']]})
calls=services['calls'];m['memory_usage']={'writes':sum(c['method']=='POST' and c['kind']=='ingest' for c in calls),'recalls':sum(c['method']=='POST' and c['kind']=='recall' for c in calls),'ingestion_polls':sum(c['method']=='GET' and c['kind']=='ingest' for c in calls)};
if isolated:m['held_out_isolated_contact']=isolated['task_summary'];m['isolated_control']={k:v for k,v in isolated.items() if k not in ['results','inference']};m['rollouts']=report['rollouts'] if report.get('training_reused') else report['rollouts']+isolated['rollouts']
write('manifest-'+revision+'.json',m);write('manifest.json',m)
evidence=root/'evidence'/('control-v8-clearance' if revision=='clearance' else 'control-v8');evidence.mkdir(parents=True,exist_ok=True);branches=[];training=json.load(open(a.source/'training-observations.json'));labels={d:{json.dumps(o,sort_keys=True):label for o,label in examples} for d,examples in training.items()}
for seed in report['protocol']['train_seeds']:
 row=json.load(open(a.source/f'teacher-{seed}.json'))
 for trial in row['trials']:
  e=next((e for e in row['examples'] if e['domain']==trial['domain'] and e['task']==trial['task']),None);label=labels[trial['domain']].get(json.dumps(e['model_observation'],sort_keys=True)) if e else None
  branches.append({'seed':seed,'domain':trial['domain'],'task':trial['task'],'initial_state_sha256':trial['outcomes'][0]['initial_state_sha256'],'snapshot':trial['snapshot'],'actual_behavior_action':e['action'] if e else None,'supervised_label':label,'outcomes':trial['outcomes']})
(evidence/'training-branches.json').write_text(json.dumps({'scope':'Measured training-only counterfactual branches. Supervised choices are relabeled from these outcomes; they are not claims about learned-model performance.','training_study':report.get('training_study',report['study']),'training_route_version':report['protocol'].get('training_source_route_version',report['protocol']['route_version']),'source_dataset_run':report['protocol']['source_dataset_run'],'objectives':report['protocol']['label_objective'],'trials':branches},indent=2)+'\n')
(evidence/'training-observations.json').write_text(json.dumps(training,indent=2)+'\n')
public={k:v for k,v in report.items() if k not in ['services','last_hypothesis']};public['search']=services['sources'];public['memory']={k:services[k] for k in ['audiences','reads','decisions','eligibility','calls']};public['workflow_url']=m['workflow_url'];text=json.dumps(public,indent=2);assert 'tinker://' not in text and 'api_key' not in text.lower();(evidence/'results.json').write_text(text+'\n');
if isolated:(evidence/'isolated-controls.json').write_text(json.dumps(isolated,indent=2)+'\n')
print(json.dumps({'selected_update':selected,'checkpoints':len(m['checkpoints']),'test_pairs':len(m['fresh']['cases']),'held_out':m['held_out']},indent=2))
