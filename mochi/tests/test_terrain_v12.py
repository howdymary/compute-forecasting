"""Physical contact-patch regressions; no controller campaign is launched."""
from types import SimpleNamespace
import math
import mujoco
from mochi.terrain_v12.world import TerrainWorld


def foot_contact(tilt=0.):
    xml='''<mujoco><worldbody>
    <geom name="desk" type="box" size=".2 .2 .01" pos="0 0 -.01"/>
    <body name="left_ankle_roll_link" pos="0 0 .0039"><freejoint/>
    <geom type="box" size=".018 .006 .004" mass=".2"/></body>
    </worldbody></mujoco>'''
    m=mujoco.MjModel.from_xml_string(xml);d=mujoco.MjData(m)
    if tilt:d.qpos[2]=.0041;d.qpos[3:7]=[math.cos(tilt/2),0,math.sin(tilt/2),0]
    mujoco.mj_forward(m,d)
    return SimpleNamespace(m=m,d=d,support_geoms={0},
        id=lambda kind,name:mujoco.mj_name2id(m,getattr(mujoco.mjtObj,'mjOBJ_'+kind.upper()),name))


def test_four_loaded_corners_provide_a_nonzero_support_area():
    w=foot_contact();patch=TerrainWorld.sole_patch(w,'left')
    assert patch['loaded'] and patch['contact_points']==4
    assert patch['area_m2']>.0004
    assert patch['capture_margin_m']>0


def test_light_toe_edge_does_not_become_a_full_sole_certificate():
    w=foot_contact(.01);patch=TerrainWorld.sole_patch(w,'left')
    assert patch['load_n']>0 and patch['contact_points']==2
    assert patch['area_m2']==0
    assert patch['capture_margin_m'] is None
