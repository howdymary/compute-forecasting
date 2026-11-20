"""Measured laptop branches from retained simulator states; never demo clips."""
import argparse
import gzip
import hashlib
import json
import pickle
import time
from dataclasses import replace
from pathlib import Path

from mochi.balanced.sequence import PhysicalStop
from mochi.control_v8.manipulation import PRESSES
from mochi.smooth_v16.world import restore
from mochi.smooth_v16.remote import physical_hash
from mochi.smooth_v16.recovery import recover

p=argparse.ArgumentParser()
p.add_argument('--id',required=True)
p.add_argument('--x',type=float,required=True)
p.add_argument('--force',type=float,default=.60)
p.add_argument('--support',action='store_true')
p.add_argument('--inverse',action='store_true')
p.add_argument('--rear',action='store_true')
p.add_argument('--radius',type=float,default=.15)
p.add_argument('--neutral',action='store_true')
p.add_argument('--stance',action='store_true')
p.add_argument('--scheduled',action='store_true')
p.add_argument('--speed',type=float,default=.16)
p.add_argument('--release',type=float,default=42.)
p.add_argument('--on',type=float,default=10.)
p.add_argument('--off',type=float,default=0.)
p.add_argument('--horizon',type=float,default=18.)
p.add_argument('--state',default='mochi/.cache/v16r1-laptop-state.pickle.gz')
a=p.parse_args()
out=Path('mochi/artifacts/contact-v18-engineering')/(a.id+'.json')
assert not out.exists(),'Preserve each physical attempt'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'status':'started','physical_attempts':1,'parameters':vars(a)}))
start=time.perf_counter()
raw=Path(a.state).read_bytes()
saved=pickle.loads(gzip.decompress(raw) if a.state.endswith('.gz') else raw)
saved=saved.get('state',saved)
if 'laptop:laptop' in saved:saved=saved['laptop:laptop']
if a.support or a.inverse or a.rear or a.scheduled:
 if a.support or a.inverse or a.rear:
  from mochi.contact_v18.development import restore as support_restore
 else:
  from mochi.contact_v18.world import restore as support_restore
 w=support_restore(saved,True)
 w.contact_lateral_support=a.support
 w.contact_inverse_dynamics=a.inverse
 w.contact_rear_face=a.rear
 w.contact_force_schedule=a.scheduled
 w.contact_closing_speed=a.speed
else:w=restore(saved,True)
initial={'physical_hash':physical_hash(w),'root':w.d.qpos[:7].tolist(),'angle':w.value('laptop'),
         'state_file_sha256':hashlib.sha256(raw).hexdigest()}
# A branch archive contains only this attempt's observations. The retained
# source snapshot and physical hash preserve the original complete prefix.
for name in ['frames','events','measurements','control_telemetry']:setattr(w,name,[])
assert physical_hash(w)==initial['physical_hash']
profile=replace(PRESSES[2],code='P5' if a.support else a.id,force=a.force,contact_x=a.x,release_degrees=a.release,pulse_on=a.on,pulse_off=a.off,radius=a.radius)
result=withdrawal=None;failure=None
try:
 if a.neutral:
  from mochi.balanced.onnx_walk import HoldWalker
  w.walker=HoldWalker(w,neutral=True)
  end=float(w.d.time)+1.4
  while w.d.time<end:w.step()
  w.walker=HoldWalker(w)
 if a.stance:
  from mochi.smooth_v16.navigation import navigate
  navigate(w,(.312,.145,2.2),timeout=20.,speed=.035,label='contact-development-stance')
 result=w.do_task('laptop',profile,max_seconds=a.horizon)
 if result['success']:withdrawal=recover(w,'laptop','R4')
except PhysicalStop as e:failure=str(e)
episode=w.episode()
row={'status':'completed','scope':'Isolated physical engineering branch. Not neural training or a continuous demo.',
     'physical_attempts':1,'initial':initial,'parameters':vars(a),'result':result,'recovery':withdrawal,
     'failure':failure,'final_angle':w.value('laptop'),'fall':w.fall,'invalid_contact':w.invalid_contact,
     'contact_failures':w.contact_failures,'wall_seconds':time.perf_counter()-start,'episode':episode}
row['probe_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
out.write_text(json.dumps(row,separators=(',',':')))
meta=out.parent/'metadata';meta.mkdir(exist_ok=True)
(meta/out.name).write_text(json.dumps({k:v for k,v in row.items() if k!='episode'},indent=2)+'\n')
brief={k:v for k,v in row.items() if k not in ['episode','result','recovery']}
brief['result']={k:v for k,v in (result or {}).items() if k!='force_schedule_log'}
brief['recovery']={k:v for k,v in (withdrawal or {}).items() if k!='observation'}
print(json.dumps(brief),flush=True)
