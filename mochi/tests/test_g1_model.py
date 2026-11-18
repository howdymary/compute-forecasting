"""Native kinematic equivalence and passive task delivery checks."""
import json,math
from pathlib import Path
import mujoco,numpy as np
from mochi.desk.g1_model import ARMS,METADATA,SOURCE,TEMPLATE,model_xml,ROOT
from mochi.desk.tasks import scenario

def test_miniature_retains_native_arm_kinematics():
 native=mujoco.MjModel.from_xml_path(str(SOURCE/'g1_with_hands.xml'));a=mujoco.MjData(native);mini=mujoco.MjModel.from_xml_string(TEMPLATE);b=mujoco.MjData(mini);rng=np.random.default_rng(51)
 for _ in range(5):
  mujoco.mj_resetDataKeyframe(native,a,0);b.qpos[:]=0
  for name in sum(ARMS.values(),[]):
   j=mujoco.mj_name2id(native,mujoco.mjtObj.mjOBJ_JOINT,name);k=mujoco.mj_name2id(mini,mujoco.mjtObj.mjOBJ_JOINT,name);delta=rng.uniform(-.15,.15);a.qpos[native.jnt_qposadr[j]]+=delta;b.qpos[mini.jnt_qposadr[k]]=delta
  mujoco.mj_forward(native,a);mujoco.mj_forward(mini,b)
  for name in ['left_wrist_yaw_link','right_wrist_yaw_link','torso_link']:
   j=mujoco.mj_name2id(native,mujoco.mjtObj.mjOBJ_BODY,name);k=mujoco.mj_name2id(mini,mujoco.mjtObj.mjOBJ_BODY,name);assert j>=0 and k>=0;expected=(a.xpos[j]-a.xpos[1])*METADATA['scale']+np.array([0,0,METADATA['pelvis_height_m']]);np.testing.assert_allclose(b.xpos[k],expected,atol=1e-9);np.testing.assert_allclose(b.xmat[k],a.xmat[j],atol=1e-9)

def test_task_objects_have_no_actuators_and_replays_have_real_motion():
 for task in ['laptop','globe']:
  m=mujoco.MjModel.from_xml_string(model_xml(scenario(task,9000)));j=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,'object-angle');assert m.nu==14 and j not in m.actuator_trnid[:,0]
  r=json.loads((ROOT/'web/desk/tasks'/f'{task}.json').read_text());frames=r['trajectory']['frames'];assert r['contact_steps']>0 and r['other_object_contact_steps']==0;assert abs(frames[-1]['angle']-frames[0]['angle'])>math.radians(10);assert frames[0]['t']==0 and frames[-1]['t']==7
  for frame in frames:
   np.testing.assert_allclose(np.linalg.norm(frame['quaternions'],axis=1),1,atol=1e-8)

def test_free_base_has_no_anchor_and_falls_without_ground():
 s=scenario('globe',9000);m=mujoco.MjModel.from_xml_string(model_xml(s,free_base=True));j=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,'free-base');assert m.jnt_type[j]==mujoco.mjtJoint.mjJNT_FREE and m.neq==0;assert j not in m.actuator_trnid[:,0];assert m.nu==14
 d=mujoco.MjData(m);mujoco.mj_forward(m,d);z0=float(d.qpos[2])
 for _ in range(250):mujoco.mj_step(m,d)
 assert abs(float(d.qpos[2])-z0)<.002
 # With ground contact removed, the pelvis must fall: there is no hidden tether.
 mujoco.mj_resetData(m,d);desk=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,'desk');m.geom_contype[desk]=m.geom_conaffinity[desk]=0
 for _ in range(125):mujoco.mj_step(m,d)
 assert float(d.qpos[2])<z0-.04

def test_free_globe_delivery_includes_standing_validity():
 r=json.loads((ROOT/'web/desk/tasks/free-globe.json').read_text());b=r['balance'];assert r['robot']['base']=='free' and r['success'];assert not b['fall'] and b['maximum_applied_base_generalized_force']==0;assert len(b['terminal_support_feet'])==2
 frames=r['trajectory']['frames'];assert max(f['base_tilt_degrees'] for f in frames)<1
 r=json.loads((ROOT/'web/desk/tasks/free-laptop.json').read_text());assert not r['success'] and r['balance']['fall']
