"""Local physical initialization and exact checkpoint continuation check."""
import hashlib,json,pickle,time
from pathlib import Path
import numpy as np
from mochi.balanced.onnx_walk import HubWalker,HoldWalker
from mochi.smooth_v16.world import EfficientWorld,state,restore
from mochi.smooth_v16.remote import physical_hash
from mochi.smooth_v16_resume.remote import physical_hash_from_saved

out=Path(__file__).resolve().parents[1]/'evidence/smooth-v16/resume-state-probe.json'
assert not out.exists(),'Keep the original probe and account for another attempt separately'
start=time.perf_counter();w=EfficientWorld(101000,True)
w.terrain_controller_history=[];w.use_native_stand=True
while w.d.time<.4:w.step(standing=True)
w.walker=HubWalker(w);w.walker=HoldWalker(w)
saved=pickle.loads(pickle.dumps(state(w,include_history=True),protocol=5))
a,b=restore(saved,True),restore(saved,True)
assert physical_hash(a)==physical_hash(b)==physical_hash(w)==physical_hash_from_saved(saved)
a.step(standing=True);b.step(standing=True)
assert np.array_equal(a.d.qpos,b.d.qpos) and np.array_equal(a.d.qvel,b.d.qvel)
assert np.array_equal(a.d.ctrl,b.d.ctrl)
seconds=time.perf_counter()-start
r={'scope':'Local state probe only; not a task completion or model result.',
   'physical_attempts':3,'single_worker_seconds':seconds,'simulation_cpu_hours':seconds/3600,
   'initialization_physical_seconds':float(w.d.time),'checkpoint_physical_hash':physical_hash(w),
   'next_step_physical_hash':physical_hash(a),'serialized_state_and_next_step_exact':True,
   'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
