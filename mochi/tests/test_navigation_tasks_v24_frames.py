"""Check fixture-frame translation and preserve real simulator state."""
import copy
import math
import unittest

import numpy as np

from mochi.curriculum.world import PROFILES
from mochi.navigation_v23.layouts import generate
from mochi.navigation_tasks_v24.world import RelativeTaskWorld
from mochi.navigation_tasks_v24.relative_laptop import laptop_surface
from mochi.navigation_tasks_v24.approaches import pose_corridor_clear
from mochi.paperfree_v19.world import PaperfreeWorld
from mochi.navigation_tasks_v24.layouts import task_layout, articulated_workspace


class Frames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shifted = generate(230000, 'engineering', 0)
        canonical = copy.deepcopy(cls.shifted)
        canonical['scene']['station_offsets'] = {}
        cls.reference = RelativeTaskWorld(canonical, 231000, False)
        cls.moved = RelativeTaskWorld(cls.shifted, 231000, False)
        for world in [cls.reference, cls.moved]:
            world.profile = PROFILES[1]
            world.stroke = math.pi - .25
            world.hold_pose = None

    def test_same_robot_mechanics(self):
        self.assertEqual(self.reference.mechanics_sha256, self.moved.mechanics_sha256)

    def test_layout_rebuild_preserves_sampled_initial_joint_states(self):
        original = PaperfreeWorld(231000, False, scene=self.shifted['scene'])
        np.testing.assert_array_equal(self.moved.d.qpos, original.d.qpos)
        np.testing.assert_array_equal(self.moved.d.qvel, original.d.qvel)
        for task in ['alarm', 'drawer', 'laptop', 'globe']:
            self.assertAlmostEqual(self.moved.value(task), original.value(task))

    def test_canonical_hand_targets_match_archived_geometry(self):
        for task in ['drawer', 'globe']:
            for phase in ['approach', 'hover', 'push', 'hold', 'release']:
                actual, normal = self.reference.hand_target(task, phase)
                expected, old_normal = super(RelativeTaskWorld, self.reference).hand_target(task, phase)
                np.testing.assert_allclose(actual, expected, atol=1e-9)
                np.testing.assert_allclose(normal, old_normal, atol=1e-9)

    def test_moved_fixture_moves_its_hand_targets(self):
        for task in ['drawer', 'globe']:
            offset = self.shifted['scene']['station_offsets'][task]
            for phase in ['hover', 'push', 'release']:
                a, _ = self.reference.hand_target(task, phase)
                b, _ = self.moved.hand_target(task, phase)
                np.testing.assert_allclose(b - a, offset, atol=1e-9)

    def test_laptop_contact_tracks_actual_hinge(self):
        offset = self.shifted['scene']['station_offsets']['laptop-screen']
        for angle in [.1, .8, 1.4]:
            a, na = laptop_surface(self.reference, angle, .15, .263, 0.)
            b, nb = laptop_surface(self.moved, angle, .15, .263, 0.)
            np.testing.assert_allclose(b - a, offset, atol=1e-9)
            np.testing.assert_allclose(na, nb, atol=1e-9)

    def test_offline_path_check_does_not_reposition_robot(self):
        before = self.moved.d.qpos.copy()
        pose_corridor_clear(self.moved, [-.43, -.25, 0.], [-.42, -.25, 0.])
        np.testing.assert_array_equal(before, self.moved.d.qpos)
        self.assertEqual(self.moved.d.time, 0.)

    def test_lid_sweep_rejects_obstruction_without_changing_live_state(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        original = json.loads((root / 'configs/navigation-v23/training.json').read_text())[0]
        blocked = RelativeTaskWorld(original, 231000, False)
        before = blocked.d.qpos.copy()
        result = articulated_workspace(blocked)
        self.assertFalse(result['valid'])
        self.assertIn('stapler-contact', [r['fixture'] for r in result['rejections']])
        np.testing.assert_array_equal(blocked.d.qpos, before)
        clear = RelativeTaskWorld(task_layout(original), 231000, False)
        self.assertTrue(articulated_workspace(clear)['valid'])
        self.assertEqual(clear.mechanics_sha256, blocked.mechanics_sha256)


if __name__ == '__main__':
    unittest.main()
