"""Validate production action dispatch at retained physical regression states."""
import argparse,gzip,hashlib,json,pickle,time
from pathlib import Path
from mochi.contact_v18.world import restore
from mochi.contact_v18.policy import execute,observation
from mochi.smooth_v16.remote import physical_hash
from mochi.smooth_v16.objective import branch_metrics,valid_branch
from mochi.balanced.sequence import PhysicalStop

p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--state',required=True);p.add_argument('--action',required=True);a=p.parse_args()
out=Path('mochi/artifacts/contact-v18-engineering')/('production-'+a.id+'.json');assert not out.exists()
out.write_text(json.dumps({'status':'started','physical_attempts':1}));start=time.perf_counter()
raw=Path(a.state).read_bytes();saved=pickle.loads(gzip.decompress(raw));w=restore(saved.get('state',saved),False)
initial=physical_hash(w);observed=observation(w,'laptop','laptop');t=float(w.d.time);index=len(w.measurements)
detail={};withdrawal=None;failure=None
try:
 detail=execute(w,'laptop','laptop',a.action)
 success=detail['success']
 if success:withdrawal=execute(w,'recovery','laptop','R4');success=success and withdrawal['success']
except PhysicalStop as exc:success=False;failure=str(exc)
e=w.episode()
r={'status':'completed','physical_attempts':1,'wall_seconds':time.perf_counter()-start,'domain':'laptop','task':'laptop',
   'observation':observed,'action':a.action,'success':bool(success),'initial_state_sha256':initial,
   'source_state_sha256':hashlib.sha256(raw).hexdigest(),'failure':failure,'result':detail,'coupled_recovery':withdrawal,
   'fall':w.fall,'invalid_contact':w.invalid_contact,'duration_s':float(w.d.time)-t,
   'metrics':branch_metrics(w.measurements[index:]),'native_smoothness':e['native_smoothness'],
   'longest_unsupported_seconds':e['longest_unsupported_seconds'],'maximum_applied_base_force':e['maximum_applied_base_force']}
r['valid_branch']=valid_branch(r)
out.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:r[k] for k in ['action','success','valid_branch','failure','fall','invalid_contact','duration_s','maximum_applied_base_force']}),flush=True)
