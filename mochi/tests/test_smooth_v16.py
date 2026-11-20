import math
from types import SimpleNamespace

import numpy as np
import pytest

from mochi.smooth_v16.verification import fixture_violation, forward_descent_check
from mochi.smooth_v16.objective import select_checkpoint, paired


@pytest.mark.parametrize('body,normal,expected',[
    ('left_ankle_roll_link',1.,False),
    ('left_ankle_roll_link',0.,True),
    ('left_wrist_yaw_link',1.,True),
])
def test_paper_top_is_walkable_but_edges_and_nonfoot_bracing_are_rejected(monkeypatch,body,normal,expected):
    import mujoco
    contact=SimpleNamespace(geom1=0,geom2=1,frame=np.array([0.,0.,normal]))
    w=SimpleNamespace(d=SimpleNamespace(contact=[contact],time=1.),m=SimpleNamespace(geom_bodyid=[1,2]),
        robot_bodies={1},book_geoms=set(),phase='walk',task=None,
        id=lambda kind,name:{'desk':2,'sticky-notes-contact':1}[name])
    monkeypatch.setattr(mujoco,'mj_id2name',lambda model,kind,index:body if kind==mujoco.mjtObj.mjOBJ_BODY else 'sticky-notes-contact')
    monkeypatch.setattr(mujoco,'mj_contactForce',lambda model,data,index,out:out.__setitem__(0,.2))
    assert bool(fixture_violation(w))==expected


def descent_data(yaw=-math.pi/2,completed=True):
    steps=[{'category':'book_descent','completed':completed,'side':'left' if i%2==0 else 'right',
        'start_position':[0.,0.,.024],'end_position':[0.,-.03,.016],
        'touchdown_t':float(i),'end_yaw':yaw} for i in range(6)]
    samples=[{'t':float(i),'yaw':yaw} for i in range(6)]
    return steps,samples


def test_forward_descent_requires_actual_lowering_touchdowns_and_heading():
    assert forward_descent_check(*descent_data())['verified']
    assert not forward_descent_check(*descent_data(math.pi/2))['verified']
    assert not forward_descent_check(*descent_data(completed=False))['verified']
    steps,samples=descent_data()
    assert not forward_descent_check(steps[:5],samples)['verified']


def test_selection_does_not_trade_arm_regression_for_fewer_steps():
    def cp(update,steps,arms):
        return {'update':update,'development':{'qualified_complete_successes':3,'falls':0,'invalid_contacts':0,
            'successful_mean_steps':steps,'successful_mean_recovery_arm_joint_travel_rad':arms,
            'successful_mean_seconds':100.}}
    choices=[cp(0,100,10),cp(1,80,11),cp(4,89,8.4),cp(8,85,9.5),cp(16,89,8.4)]
    assert select_checkpoint(choices,{}, {'development_seeds':[1,2,3]})['update']==4


def test_failed_short_route_does_not_become_an_efficiency_gain():
    def row(seed,steps,arms,valid):
        return {'seed':seed,'qualified_complete':valid,'episode':{'steps':{'attempts':steps},'duration':100.,
            'recoveries':[{'arm_joint_travel_rad':arms}], 'intertask_arm_joint_travel_rad':{'left':arms,'right':arms}}}
    result=paired([row(1,100,10,True),row(2,100,10,True)],
        [row(1,85,8,True),row(2,1,.01,False)])
    assert result['n']==1
    assert result['mean_step_reduction_fraction']==pytest.approx(.15)
    assert result['mean_recovery_arm_travel_reduction_fraction']==pytest.approx(.2)


def test_exact_state_branch_preserves_the_new_passive_hinge_physics():
    from mochi.smooth_v16.world import EfficientWorld,state,restore
    from mochi.balanced.onnx_walk import HubWalker,HoldWalker
    from mochi.curriculum.world import scenario
    w=EfficientWorld(101000,False)
    w.walker=HubWalker(w)
    w.walker=HoldWalker(w)
    before=w.d.qpos.copy()
    expected=scenario(101000)['laptop_friction']+.015
    assert w.m.dof_frictionloss[w.v['laptop']]==pytest.approx(expected)
    cloned=restore(state(w))
    assert np.array_equal(cloned.d.qpos,before)
    assert np.array_equal(cloned.m.dof_frictionloss,w.m.dof_frictionloss)
    assert cloned.scene['version']=='richdesk-v16-open-hinge'
