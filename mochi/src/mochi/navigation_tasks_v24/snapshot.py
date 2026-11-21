"""Exact branches of measured physical states; never spliced into a demo."""
import copy

import mujoco
import numpy as np

from mochi.balanced.onnx_walk import HubWalker, HoldWalker
from mochi.smooth_v16.world import state
from .world import RelativeTaskWorld


def restore(saved, record=False):
    values = saved['world']
    w = RelativeTaskWorld(values['layout'], values['s']['seed'], False)
    assert w.mechanics_sha256 == values['mechanics_sha256']
    for name, value in saved['model'].items():
        getattr(w.m, name)[:] = value
    for name, value in values.items():
        setattr(w, name, copy.deepcopy(value))
    w.d = copy.copy(saved['data'])
    control = w.d.ctrl.copy()
    w.viz = mujoco.MjData(w.m)
    w.walker = HubWalker(w)
    w.walker = HoldWalker(w)
    for name, value in saved['walker'].items():
        setattr(w.walker, name, copy.deepcopy(value))
    w.d.ctrl[:] = control
    w.record = record
    return w


def capture_and_verify(w):
    """Advance the uninterrupted prefix by one real step, check its clone."""
    saved = state(w, include_history=False)
    clone = restore(saved)
    clone.step()
    w.step()
    assert np.array_equal(w.d.qpos, clone.d.qpos)
    assert np.array_equal(w.d.qvel, clone.d.qvel)
    assert np.array_equal(w.d.ctrl, clone.d.ctrl)
    saved['clone_check'] = {'qpos_exact': True, 'qvel_exact': True, 'control_exact': True,
        'scope': 'Restored branch next step equals the real uninterrupted prefix next step. Branches remain component data, never full-sequence recordings.'}
    return saved
