"""Training-only engineering calibration; never claims a learned improvement."""
import argparse,json,math
from pathlib import Path
from mochi.curriculum.world import World
from mochi.curriculum.gait_control import install,GAITS
from mochi.curriculum.motion_metrics import episode_motion
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();rows=[]
for gait in GAITS:
 for i,(dx,dy,heading) in enumerate([(.09,0,0),(.07,.025,.35),(.025,0,1.57)]):
  w=World(18000+i,record=True);install(w,gait);goal=(w.d.qpos[0]+dx,w.d.qpos[1]+dy,heading);success=w.walk_to(goal,max_seconds=16);e=w.episode();row={'gait':gait,'seed':18000+i,'goal':goal,'success':success,'fall':w.fall,'end_observation':w.walk_observation(goal),'motion':episode_motion(e),'episode':e};rows.append(row);print(gait,i,success,w.fall,round(e['duration'],2),flush=True)
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps({'scope':'Training-only engineering calibration, no model learning.','rows':rows},separators=(',',':')))
