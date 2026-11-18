"""Measure existing checkpoint trajectories without changing frozen physics."""
import argparse,json
from pathlib import Path
from mochi.curriculum.motion_metrics import episode_motion
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
rows=[];pending=[]
for path in sorted(a.source.glob('checkpoint-*.json')):
 if 'receipts' in path.name or 'paths' in path.name:continue
 raw=json.loads(path.read_text())
 if not isinstance(raw,list):continue
 for r in raw:
  if 'episode' not in r:continue
  pending.append((int(path.stem.split('-')[-1]),r))
windows={seed:min(20.,min(r['episode']['duration'] for _,r in pending if r['seed']==seed)) for seed in {r['seed'] for _,r in pending}}
for checkpoint,r in sorted(pending,key=lambda x:(x[0],x[1]['seed'])):
 e=r['episode'];rows.append({'checkpoint':checkpoint,'seed':r['seed'],'whole_episode':episode_motion(e),'matched_initial_window':episode_motion(e,windows[r['seed']]),'task_successes':{k:v['success'] for k,v in e['results'].items()},'fall':e['fall']})
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps({'scope':'Post-hoc physical diagnostics, not a frozen training reward. Per seed, compare the same initial window: the minimum of 20 seconds and the shortest recorded checkpoint episode.','rows':rows},indent=2));print(a.out,len(rows))
