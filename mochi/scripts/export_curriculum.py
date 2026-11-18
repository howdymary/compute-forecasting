"""Export measured checkpoint trajectories, never synthesize robot animation."""
from pathlib import Path
import argparse,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'web/desk/curriculum';OUT.mkdir(exist_ok=True)
def write(name,x):
 def rounded(v):
  if isinstance(v,float):return round(v,6)
  if isinstance(v,dict):return {k:rounded(x) for k,x in v.items()}
  if isinstance(v,list):return [rounded(x) for x in v]
  return v
 (OUT/name).write_text(json.dumps(rounded(x),separators=(',',':')))
p=argparse.ArgumentParser();p.add_argument('--calibration',action='store_true');a=p.parse_args();source=ROOT/'artifacts/curriculum'
if a.calibration:
 e=json.loads((source/'calibration-sequence.json').read_text());write('calibration.json',e);write('manifest.json',{'status':'calibration','development_seed':e['scenario']['seed'],'checkpoints':[{'update':0,'file':'calibration.json'}],'selected_update':0,'optimizer_updates_completed':0})
else:
 report=json.loads((source/'report.json').read_text());manifest={k:report[k] for k in ['status','selected_checkpoint','held_out','optimizer_updates_completed','rollouts']};manifest['selected_update']=report['selected_checkpoint']['update'];manifest['development_seed']=report['protocol']['development_seeds'][0];manifest['checkpoints']=[]
 for cp in report['checkpoints']:
  episodes=json.loads((source/f"checkpoint-{cp['update']}.json").read_text());ep=next(e for e in episodes if e['seed']==manifest['development_seed']);name=f"checkpoint-{cp['update']}.json";write(name,ep['episode']);manifest['checkpoints'].append({**cp,'file':name})
 seed=report['protocol']['held_out_seeds'][0];manifest['fresh']={'seed':seed}
 for key,label in [('before','starting_model'),('after','post_trained_model')]:
  e=next(e for e in json.loads((source/f'held-out-{label}.json').read_text()) if e['seed']==seed);name=f'held-out-{key}.json';write(name,e['episode']);manifest['fresh'][key]=name
 manifest['memory']=report['services']['eligibility'];manifest['search_calls']=len(report['services']['sources']);manifest['sources']=[s for entry in report['services']['sources'] for s in entry['sources']];manifest['training_counts']={d:sum(x['domain_counts'][d] for x in report['training_log']) for d in ['walk','alarm','drawer','laptop','globe']};write('manifest.json',manifest)
