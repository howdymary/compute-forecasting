import math
import mujoco
import numpy as np
import pytest
from mochi.desk.tasks import RIG,scenario,xml,rollout

@pytest.mark.parametrize('task',['laptop','globe'])
def test_real_hand_contact_moves_only_the_passive_object(task):
    r=rollout(task,8000,record=True)
    assert r['success'] and r['contact_steps']>100
    assert r['other_object_contact_steps']==0
    assert r['initial_ik_error_m']<1e-5
    assert r['error_degrees']<3 and r['dwell_seconds']>=.4
    frames=r['trajectory']['frames']
    assert abs(frames[-1]['angle']-frames[0]['angle'])>math.radians(15)
    model=mujoco.MjModel.from_xml_string(xml(scenario(task,8000)))
    # Four arm actuators, no actuator connected to the task object's hinge.
    assert model.nu==4 and model.nq==5
    oid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,'object-angle')
    assert oid not in model.actuator_trnid[:,0]
    names=r['trajectory']['body_names'];first=frames[0]
    for a,b,length in [('right-shoulder','right-elbow',RIG['upper_arm']),('right-elbow','right-wrist',RIG['forearm']),('left-hip','left-knee',RIG['thigh']),('left-knee','left-ankle',RIG['shin'])]:
        assert np.linalg.norm(np.array(first['positions'][names.index(a)])-first['positions'][names.index(b)])==pytest.approx(length)
