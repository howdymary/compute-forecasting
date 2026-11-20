"""Show and measure lifted steps from the retained forward-descent endpoint."""
import argparse,json,pickle,time
from pathlib import Path
from mochi.contact_v18.world import restore
from mochi.contact_v18.footsteps import execute_flat
from mochi.smooth_v16.remote import physical_hash
from mochi.balanced.sequence import PhysicalStop

p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--shift',type=float,default=.55);p.add_argument('--swing',type=float,default=.60);a=p.parse_args()
out=Path('mochi/artifacts/contact-v18-engineering')/(a.id+'.json');assert not out.exists()
out.write_text(json.dumps({'status':'started','physical_attempts':1}));start=time.perf_counter()
saved=pickle.loads(Path('mochi/artifacts/smooth-v16-engineering/book-forward-descent-3.pickle').read_bytes())
w=restore(saved,True);initial=physical_hash(w);t=float(w.d.time)
for name in ['frames','events','measurements','control_telemetry']:setattr(w,name,[])
result=None;failure=None
try:result=execute_flat(w,[(-.30,-.18,0.)],shift=a.shift,swing=a.swing,timeout=80.)
except PhysicalStop as exc:failure=str(exc)
e=w.episode();samples=getattr(w,'flat_step_samples',[])
peaks={side:max((x['clearance_m'][side] or 0. for x in samples),default=0.) for side in ['left','right']}
summary={'status':'completed','physical_attempts':1,'wall_seconds':time.perf_counter()-start,
 'initial_state_sha256':initial,'success':bool(result and result['success']),'failure':failure,
 'fall':w.fall,'invalid_contact':w.invalid_contact,'duration_s':float(w.d.time)-t,
 'measured_peak_minimum_sole_clearance_m':peaks,'steps':w.step_counter.summary(since=t),
 'maximum_applied_base_force':e['maximum_applied_base_force'],'contact_failures':w.contact_failures,
 'parameters':vars(a),'scope':'Post-descent walking engineering branch, not a trained-model result or complete demo.'}
out.write_text(json.dumps({**summary,'result':result,'clearance_samples':samples,'episode':e},separators=(',',':')))
meta=out.parent/'metadata';meta.mkdir(exist_ok=True);(meta/out.name).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary),flush=True)
