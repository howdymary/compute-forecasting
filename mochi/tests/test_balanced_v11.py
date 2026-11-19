"""Regression checks using real MuJoCo contacts, without running a campaign."""
from types import SimpleNamespace

import mujoco
import numpy as np

from mochi.balanced.balance import support
from mochi.balanced.recovery import fixture_contact


def contact_world(hand=True):
    model=mujoco.MjModel.from_xml_string('''
    <mujoco><option gravity="0 0 -9.81"/>
    <worldbody>
      <geom name="book" type="box" size=".2 .2 .01" pos="0 0 -.01"/>
      <body name="left_ankle_roll_link" pos="0 0 .0099"><freejoint/>
        <geom type="box" size=".02 .01 .01" mass="1"/></body>
      <body name="right_hand" pos=".08 0 .0099"><freejoint/>
        <geom type="box" size=".01 .01 .01" mass=".1"/></body>
    </worldbody></mujoco>''')
    data=mujoco.MjData(model)
    if not hand:
        data.qpos[9]=.1
    mujoco.mj_forward(model,data)
    return SimpleNamespace(m=model,d=data,support_geoms={0},robot_bodies={1,2})


def test_real_hand_contact_stays_invalid_while_book_foot_support_is_allowed():
    w=contact_world(hand=False)
    assert w.d.ncon>=4
    assert fixture_contact(w)==(0,0.)
    w=contact_world(hand=True)
    count,peak=fixture_contact(w)
    assert count>=1 and peak>.01


def test_capture_check_rejects_velocity_that_carries_com_outside_real_contacts():
    w=contact_world(hand=False)
    static=support(w)
    assert static['capture_margin_m']>0
    w.d.qvel[0]=1.
    moving=support(w)
    assert moving['capture_margin_m']<0
    assert np.allclose(static['support_polygon_xy'],moving['support_polygon_xy'])
