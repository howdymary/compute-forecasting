"""Scene-removal and anti-shortcut contracts for the new experiment."""
from copy import deepcopy
from pathlib import Path
import json

import numpy as np

from mochi.contact_v18.world import ContactWorld
from mochi.paperfree_v19.objective import INVALID_REWARD, step_reward
from mochi.paperfree_v19.policy import config
from mochi.paperfree_v19.world import PaperfreeWorld, scene_spec


def test_only_the_sticky_note_is_removed_from_the_scene():
    old = json.loads((Path(__file__).parents[1] / 'configs/richdesk-v9.json').read_text())
    new = scene_spec()
    assert new['props'] == [p for p in old['props'] if p['name'] != 'sticky-notes']
    for field in old.keys() - {'props', 'version'}:
        assert new[field] == old[field]
    assert len(old['props']) - len(new['props']) == 1


def test_paper_has_no_invisible_physics_and_other_actuation_is_unchanged():
    old, new = ContactWorld(185000, False), PaperfreeWorld(185000, False)
    assert new.id('geom', 'sticky-notes-contact') == -1
    assert new.id('body', 'sticky-notes') == -1
    assert new.terrain_height(.236, .015) == 0.
    assert old.terrain_height(.236, .015) == .0024
    assert new.m.ngeom == old.m.ngeom - 1 and new.m.nbody == old.m.nbody - 1
    assert (new.m.nq, new.m.nv, new.m.nu) == (old.m.nq, old.m.nv, old.m.nu)
    assert new.m.opt.timestep == old.m.opt.timestep
    np.testing.assert_array_equal(new.m.dof_frictionloss, old.m.dof_frictionloss)
    np.testing.assert_array_equal(new.m.actuator_forcerange, old.m.actuator_forcerange)


def test_failure_or_doing_nothing_never_earns_a_low_step_reward():
    assert step_reward(0, 0, 0, False) == INVALID_REWARD
    assert step_reward(2000, 420, 100, True) > step_reward(0, 0, 0, False)


def test_one_fewer_step_beats_every_time_and_arm_tiebreaker():
    for steps in [1, 20, 500, 2000]:
        assert step_reward(steps - 1, 420, 100, True) > step_reward(steps, 0, 0, True)


def test_laptop_route_uses_continuous_flat_transit():
    routes = config()['routes']
    assert routes['laptop'] == [[.08, .02, 0.], [.305, .02, 0.], [.305, .155, np.pi / 2]]
    assert 'postit' not in json.dumps(routes).lower()
    assert all(p['forward_reference_m'] >= 0 for p in config()['walking'].values())
