"""Describe executed walking decisions; never substitute teacher actions."""
import argparse, collections, json
from pathlib import Path
from mochi.curriculum.world import World
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
rows=[]
for f in sorted(a.source.glob('checkpoint-*.json'),key=lambda p:int(p.stem.split('-')[-1])):
 if f.stem=='checkpoint-paths':continue
 update=int(f.stem.split('-')[-1])
 for trial in json.loads(f.read_text()):
  decisions=[d for d in trial['episode']['decisions'] if d['observation']['domain']=='walk'];matches=sum(d['action']==World.teacher_move(d['observation']) for d in decisions)
  rows.append({'update':update,'seed':trial['seed'],'walking_decisions':len(decisions),'action_counts':dict(collections.Counter(d['action'] for d in decisions)),'agreement_with_fixed_teacher_on_visited_states':{'matches':matches,'n':len(decisions)},'stations_reached':len(trial['arrivals']),'fall':trial['episode']['fall'],'first_distance_mm':decisions[0]['observation']['distance_mm'] if decisions else None,'last_distance_mm':decisions[-1]['observation']['distance_mm'] if decisions else None})
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps({'scope':'Diagnostic on visited development states. Teacher agreement is not a robotics success metric, and no actions were replaced.','episodes':rows},indent=2))
print(json.dumps(rows,indent=2))
