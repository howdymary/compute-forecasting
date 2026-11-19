"""Success-boundary and real-contact tests for the terrain development study."""
import numpy as np
from mochi.richdesk.world import DeskWorld
from mochi.richdesk.verify import book_top
from mochi.richdesk.preflight import training_readiness
from mochi.richdesk.wholebody import WholeBodyWalker
from mochi.richdesk.stepping import StepParameters


def test_planned_landing_cannot_satisfy_physical_book_verifier():
    w=DeskWorld(31000)
    w.walker.swing_goal=np.array([-.375,.025,.024]);w.walker.steps=100
    r=book_top(w)
    assert not r['instant_valid']
    assert r['top_book_load_n']=={'left':0.,'right':0.}


def test_landing_check_reads_actual_foot_pads_and_terrain():
    w=DeskWorld(31000)
    assert w.landing_fits('left',0.)
    assert not w.landing_fits('left',.008)
    printer=w.id('geom','printer-contact')
    assert printer>=0


def test_inverse_dynamics_uses_limited_actuators_without_base_force():
    w=DeskWorld(31000)
    while w.d.time<.4:w.step(standing=True)
    w.walker=WholeBodyWalker(w,StepParameters())
    for _ in range(15):w.step((.025,0,0))
    assert np.all(w.d.qfrc_applied[:6]==0)
    limits=w.m.actuator_forcerange[w.walker.aids]
    assert np.all(w.d.ctrl[w.walker.aids]>=limits[:,0]-1e-6)
    assert np.all(w.d.ctrl[w.walker.aids]<=limits[:,1]+1e-6)
    assert not w.fall


def test_training_gate_rejects_missing_physical_route():
    r=training_readiness()
    assert not r['optimizer_updates_authorized_now']
    assert r['reasons']
