"""Regression contracts for the frozen comparison and physical state branching."""
import math
import numpy as np
from mochi.control_v8.verification import laptop_good,task_valid,sequence_success
from mochi.control_v8.manipulation import ControlWorld
from mochi.control_v8.recovery import snapshot,restore
from mochi.control_v8.decisions import encode
from mochi.planning.follower import teacher

def test_laptop_requires_closed_slow_and_actual_contact_progress():
 assert laptop_good(math.radians(4),.10,math.radians(5))
 assert not laptop_good(math.radians(6),.10,math.radians(5))
 assert not laptop_good(math.radians(4),.16,math.radians(5))
 assert not laptop_good(math.radians(4),.10,0)
 assert not task_valid(.4,1,0,False,.81)
 assert not task_valid(.4,1,1,False,.1)
 assert not task_valid(.4,0,0,False,.1)

def test_state_branch_preserves_next_physics_steps():
 w=ControlWorld(19000,False)
 for _ in range(20):w.step(standing=True)
 clone=restore(snapshot(w))
 for _ in range(10):w.step(standing=True);clone.step(standing=True)
 np.testing.assert_allclose(clone.d.qpos,w.d.qpos,rtol=0,atol=1e-6)
 np.testing.assert_allclose(clone.d.qvel,w.d.qvel,rtol=0,atol=1e-4)

def test_walk_encoding_preserves_teacher_thresholds():
 # The old distance representation hid the stopping boundary. Ensure distinct
 # labels cannot share an encoding at all relevant sign/threshold boundaries.
 seen={}
 for d in [5.9,6.,60.,60.1]:
  for h in [-25,-7.1,-7,0,7,7.1,25]:
   for f,l in [(-4.1,4),(-4,4),(4,4),(4.1,4),(4,4.1),(20,30),(30,20)]:
    o=dict(domain='walk',phase='align',distance_mm=d,heading_error_degrees=h,target_forward_mm=f,target_left_mm=l,cross_track_mm=0,velocity_forward_mm_s=0,velocity_left_mm_s=0,yaw_rate_degrees_s=0,foot_contacts={'left':True,'right':True},body_tilt_degrees=0,recent_commands=[])
    key=str(encode(o));label=teacher(o)
    assert key not in seen or seen[key]==label
    seen[key]=label
