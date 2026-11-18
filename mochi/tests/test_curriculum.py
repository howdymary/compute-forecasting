"""Physical validity checks for the new locomotion/contact foundation."""
import math
import mujoco
import numpy as np
from mochi.curriculum.world import World,DT,PROFILES

def test_free_base_and_passive_objects():
    w=World()
    assert w.m.jnt_type[w.id('joint','free-base')]==mujoco.mjtJoint.mjJNT_FREE
    assert len(w.walker.aids)==12 and len(set(w.walker.aids))==12
    assert w.m.neq==0
    driven=set(w.m.actuator_trnid[:,0])
    assert all(j not in driven for j in w.joints.values())

def test_passive_laptop_stays_open_without_hand_contact():
    w=World(start_task='laptop');initial=w.value('laptop')
    for _ in range(round(30/DT)):w.step(standing=True)
    assert abs(w.value('laptop')-initial)<math.radians(1)
    assert not w.fall and w.base_force==0

def test_button_press_and_release_is_simulated_contact():
    w=World(12000,record=True,start_task='alarm');r=w.do_task('alarm',PROFILES[1])
    assert r['success'] and r['contacts']>0 and w.activated
    assert any(f['hand_contact'] for f in w.frames)
    assert max(f['objects']['alarm'] for f in w.frames)>.85*w.s['clock_stroke']
    assert w.value('alarm')<.2*w.s['clock_stroke']
    assert all(b['t']>a['t'] for a,b in zip(w.frames,w.frames[1:]))
    assert w.base_force==0

def test_laptop_closes_by_hand_without_base_support():
    w=World(12000,start_task='laptop');r=w.do_task('laptop',PROFILES[2])
    assert r['success'] and r['contact_progress']>math.radians(4)
    assert w.value('laptop')<math.radians(5) and w.base_force==0
