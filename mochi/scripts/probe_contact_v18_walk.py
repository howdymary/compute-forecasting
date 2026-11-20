"""One exact-state parked-arm walking development attempt."""
import gzip,json,pickle,time
from pathlib import Path
from mochi.contact_v18.world import restore
from mochi.contact_v18.policy import execute
from mochi.balanced.sequence import PhysicalStop
from mochi.smooth_v16.objective import branch_metrics
from mochi.smooth_v16.remote import physical_hash

p=Path('mochi/artifacts/contact-v18-engineering/parked-globe-101002.json')
assert not p.exists();p.write_text(json.dumps({'status':'started','physical_attempts':1}))
start=time.perf_counter();saved=pickle.loads(gzip.decompress(Path('mochi/.cache/v17-globe-101002.pickle.gz').read_bytes()))
w=restore(saved.get('state',saved),False);initial=physical_hash(w);t=float(w.d.time);index=len(w.measurements)
failure=None;arrivals=[]
try:arrivals=execute(w,'walk','globe','W7')
except PhysicalStop as exc:failure=str(exc)
e=w.episode()
r={'status':'completed','physical_attempts':1,'wall_seconds':time.perf_counter()-start,
   'scope':'Isolated walking branch; not a continuous demo or model-training gain.',
   'initial_state_sha256':initial,'success':bool(arrivals and all(a['success'] for a in arrivals)),
   'fall':w.fall,'invalid_contact':w.invalid_contact,'failure':failure,'arrivals':arrivals,
   'duration_s':float(w.d.time)-t,'steps':w.step_counter.summary(since=t),
   'metrics':branch_metrics(w.measurements[index:]),'native_smoothness':e['native_smoothness'],
   'longest_unsupported_seconds':e['longest_unsupported_seconds'],
   'intertask_arm_joint_travel_rad':e['intertask_arm_joint_travel_rad']}
p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
