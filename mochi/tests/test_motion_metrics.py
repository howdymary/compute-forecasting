"""Analytical fixtures distinguish replay motion from unrecorded actuator data."""
import math
import pytest
from mochi.curriculum.motion_metrics import episode_motion

def sample():
 frames=[]
 for i in range(26):
  t=i*.04
  frames.append({'t':t,'phase':'walk','positions':[[0,0,0],[.05*t,0,.15]],'quaternions':[[1,0,0,0],[1,0,0,0]],'base_tilt_degrees':3})
 return {'duration':1,'trajectory':{'sample_hz':25,'frames':frames},'decisions':[], 'foot_slip_estimate_m':{'left':.002,'right':.001}}

def test_straight_translation_has_no_angular_motion():
 result=episode_motion(sample())
 assert result['walking_path_m']==pytest.approx(.05)
 assert result['walking_duration_s']==pytest.approx(1)
 assert result['walking_yaw_travel_degrees']==0
 assert result['walking_torso_tilt_rms_degrees']==3
 assert result['motor_work_j'] is None and result['foot_clearance_m'] is None
 assert result['command_change_rms_m_s2'] is None

def test_time_window_does_not_reuse_whole_episode_slip():
 result=episode_motion(sample(),.4)
 assert result['walking_path_m']==pytest.approx(.02)
 assert result['loaded_foot_slip_entire_episode_m'] is None

def test_rotation_wrap_does_not_count_a_full_revolution():
 e=sample();frames=e['trajectory']['frames'][:2]
 for f,deg in zip(frames,[179,-179]):
  a=math.radians(deg)/2;f['quaternions'][1]=[math.cos(a),0,0,math.sin(a)]
 e['trajectory']['frames']=frames
 assert episode_motion(e)['walking_yaw_travel_degrees']==pytest.approx(2)
