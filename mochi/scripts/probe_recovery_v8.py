import json,math,uuid
from pathlib import Path
import mujoco
from mochi.control_v8.manipulation import ControlWorld,PRESSES
from mochi.control_v8.recovery import snapshot,restore,recover,RECOVERIES
from mochi.curriculum.world import PROFILES,STATIONS
out=Path('mochi/artifacts/control-v8');out.mkdir(parents=True,exist_ok=True);rows=[]
for t,c in [('alarm','B'),('drawer','A'),('laptop','P1'),('globe','A')]:
 w=ControlWorld(19000,False,start_task=t)
 if t=='alarm':w.d.qpos[1]=.025
 if t=='laptop':w.d.qpos[:2]=[.30,.16];w.d.qpos[3:7]=[math.cos(math.pi/4),0,0,math.sin(math.pi/4)]
 mujoco.mj_forward(w.m,w.d);r=w.do_task(t,next(p for p in (PRESSES if t=='laptop' else PROFILES) if p.code==c));s=snapshot(w);result={'task':r,'recoveries':[]}
 for p in RECOVERIES:
  b=restore(s);result['recoveries'].append(recover(b,t,p))
 rows.append(result);print(t,json.dumps(result),flush=True);(out/'recovery-calibration.json').write_text(json.dumps(rows,indent=2))
