import numpy as np
from mochi.desk.physics import CATALOG,PROTOCOL,observation,rollout,scenario,xml

def test_native_desktop_contact_and_determinism():
    a=rollout(CATALOG[1],7000);b=rollout(CATALOG[1],7000)
    assert a['success'] and a['contact_steps']>20
    assert a['distance_m']<.01 and a['scenario']['object_xy'][1]>.0
    assert a==b
    # Object motion is contact-driven on z=0, no raised task table.
    assert 'pos="0 0 -.02" size=".60 .40 .02"' in xml(scenario(7000))

def test_splits_and_visible_state():
    splits=[set(range(*v)) for v in PROTOCOL['seed_splits'].values()]
    assert all(not a.intersection(b) for i,a in enumerate(splits) for b in splits[i+1:])
    state=observation(scenario(71000))
    assert not {'seed','mass','friction','success'}.intersection(state)
    assert set(state)=={'surface','object_xy_mm','object_yaw_degrees','target_xy_mm'}

def test_success_requires_pose_and_settling():
    r=rollout(CATALOG[2],7000)
    assert r['inside'] and not r['success']
    assert r['yaw_error_rad']>PROTOCOL['orientation_tolerance_rad']
