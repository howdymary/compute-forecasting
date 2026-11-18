"""Observe a retained training failure; never changes frozen V8 code or test seeds."""
import json,collections,dataclasses,argparse,hashlib
from pathlib import Path
import mujoco,numpy as np
from mochi.control_v8.recovery import restore
from mochi.control_v8.manipulation import PRESSES
p=argparse.ArgumentParser();p.add_argument('--x',type=float,default=.263);p.add_argument('--shift-x',type=float,default=0.);a=p.parse_args();source=next(Path('mochi/.cache/control-source-audit').rglob('teacher-23000.json'));r=json.load(open(source));trial=next(t for t in r['trials'] if t['task']=='laptop');w=restore(trial['snapshot'],True);w.d.qpos[0]+=a.shift_x;mujoco.mj_forward(w.m,w.d);w.frames=[];w.capture();original=w.step;pairs=collections.Counter();first={}
def observe(*args,**kwargs):
 original(*args,**kwargs)
 for i,c in enumerate(w.d.contact):
  ga,gb=int(c.geom1),int(c.geom2);ba,bb=int(w.m.geom_bodyid[ga]),int(w.m.geom_bodyid[gb])
  if (ba in w.robot_bodies)==(bb in w.robot_bodies):continue
  if w.id('geom','desk') in [ga,gb]:continue
  f=np.zeros(6);mujoco.mj_contactForce(w.m,w.d,i,f)
  if f[0]<.01:continue
  body=lambda b:mujoco.mj_id2name(w.m,mujoco.mjtObj.mjOBJ_BODY,b)
  key=body(ba)+' / '+body(bb);pairs[key]+=1;first.setdefault(key,{'t':float(w.d.time),'phase':w.phase,'force_n':float(f[0]),'angle':w.value('laptop')})
w.step=observe;result=w.do_task('laptop',dataclasses.replace(PRESSES[0],contact_x=a.x));out=Path('mochi/artifacts/control-v8');data={'scope':'Engineering diagnosis on known training seed23000. Not a held-out trial or trained-policy result. Frozen V8 code unchanged.','contact_x':a.x,'initial_robot_shift_x':a.shift_x,'result':result,'contact_steps_by_body_pair':dict(pairs),'first_contacts':first,'episode':w.episode()};(out/f'training-contact-x-{a.x:.3f}-shift-{a.shift_x:.3f}.json').write_text(json.dumps(data,separators=(',',':')));print(json.dumps({k:v for k,v in data.items() if k!='episode'}),flush=True)
