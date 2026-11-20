"""Matched physical flat-gait clearance probe immediately after book descent."""
import argparse,json,pickle,time
from pathlib import Path
from mochi.contact_v18.world import restore
from mochi.balanced.onnx_walk import HubWalker
from mochi.balanced.sequence import PhysicalStop
from mochi.smooth_v16.remote import physical_hash

p=argparse.ArgumentParser();p.add_argument('--lift',action='store_true');p.add_argument('--id');p.add_argument('--navigate',action='store_true');p.add_argument('--fast-nav',action='store_true');p.add_argument('--agile-nav',action='store_true');p.add_argument('--height',type=float,default=.006);p.add_argument('--forward',type=float,default=0.);p.add_argument('--joint-limit',type=float,default=.10);a=p.parse_args()
name=a.id or ('native-lifted' if a.lift else 'native-original')
out=Path('mochi/artifacts/contact-v18-engineering')/(name+'.json');assert not out.exists()
out.write_text(json.dumps({'status':'started','physical_attempts':1}));start=time.perf_counter()
w=restore(pickle.loads(Path('mochi/artifacts/smooth-v16-engineering/book-forward-descent-3.pickle').read_bytes()),True)
initial=physical_hash(w);t=float(w.d.time)
for n in ['frames','events','measurements','control_telemetry']:setattr(w,n,[])
w.walker=HubWalker(w);w.raised_native_swing=a.lift;w.phase='walk';w.task=None;w.efficiency_segment='flat_transit'
w.swing_lift_reference=a.height;w.swing_forward_reference=a.forward;w.swing_joint_residual_limit=a.joint_limit
failure=None
try:
 if a.navigate:
  from mochi.smooth_v16.navigation import navigate
  from mochi.smooth_v16.policy import NAVIGATION
  from mochi.smooth_v17.gait import PARAMETERS
  navigate(w,(-.19,-.18,0.),timeout=25.,speed=.12 if a.agile_nav else .105 if a.fast_nav else .08,label='post-descent-flat-corridor',parameters=PARAMETERS if a.agile_nav else NAVIGATION['W5'] if a.fast_nav else None)
 else:
  while w.d.time-t<1.5:w.step((.055,0.,0.))
except PhysicalStop as exc:failure=str(exc)
e=w.episode();summary={'status':'completed','physical_attempts':1,'wall_seconds':time.perf_counter()-start,
 'initial_state_sha256':initial,'success':not failure,'failure':failure,'fall':w.fall,'invalid_contact':w.invalid_contact,
 'duration_s':float(w.d.time)-t,'steps':w.step_counter.summary(since=t),'root':w.d.qpos[:3].tolist(),
 'clearance':{k:v for k,v in e['flat_foot_clearance'].items() if k!='swings'},'maximum_applied_base_force':e['maximum_applied_base_force'],
 'parameters':vars(a),'native_smoothness':e['native_smoothness']}
out.write_text(json.dumps({**summary,'episode':e},separators=(',',':')))
meta=out.parent/'metadata';meta.mkdir(exist_ok=True);(meta/out.name).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary),flush=True)
