"""Remove the paper from physics and terrain without editing frozen V18 code."""
import copy
import json
import math

import mujoco
import numpy as np

from ..balanced.onnx_walk import HubWalker
from ..balanced.sequence import PhysicalStop, average_velocity
from ..balanced.world import BalancedWorld
from ..contact_v18.world import ContactWorld
from ..curriculum.world import ROOT
from ..richdesk.world import DeskWorld
from ..smooth_v16.verification import fixture_violation
from ..smooth_v16.world import EfficientWorld, restore as restore_physics


def scene_spec():
    return json.loads((ROOT / 'configs/richdesk-v19-paperfree.json').read_text())


class PaperfreeMeasurements(EfficientWorld):
    # The older override requires a paper prop. Book support is unchanged.
    terrain_height = DeskWorld.terrain_height

    def step(self, *args, **kwargs):
        if kwargs.get('standing', False) and isinstance(self.walker, HubWalker) and self.walker.mode != 'walk':
            kwargs['standing'] = False
        BalancedWorld.step(self, *args, **kwargs)
        violation = fixture_violation(self)
        if violation:
            self.invalid_contact = True
            self.contact_failures.append(violation)
        if self.stopped:
            raise PhysicalStop('fall' if self.fall else 'invalid_fixture_contact')
        if self.d.time >= self.next_direction_sample:
            self.direction_samples.append({
                't': float(self.d.time),
                'phase': 'turn-to-path' if self.phase == 'turn' else 'walk-forward',
                'native_walk': isinstance(self.walker, HubWalker) and self.walker.mode == 'walk',
                'yaw_rad': self.yaw(), 'root': self.d.qpos[:3].tolist(),
                'cycle_averaged_velocity_xy': average_velocity(self, .25).tolist(),
            })
            self.next_direction_sample = float(self.d.time) + .04
        if not self.measurements or 'feet' in self.measurements[-1]:
            return
        row = self.measurements[-1]
        feet = {}
        for side in ['left', 'right']:
            body = self.id('body', side + '_ankle_roll_link')
            rotation = self.d.xmat[body].reshape(3, 3)
            feet[side] = {
                'position': (self.d.xpos[body] + rotation @ np.array([.0058, 0, -.00585])).tolist(),
                'yaw': math.atan2(rotation[1, 0], rotation[0, 0]),
            }
        category = self.efficiency_segment
        if self.phase == 'turn':
            category = 'turning'
        elif self.phase == 'walk' and self.events and self.events[-1].get('phase') == 'task-alignment':
            category = 'alignment'
        row['feet'], row['step_category'] = feet, category
        self.step_counter.update(row['t'], feet, row['loads_n'], category)
        if category in ['book_turnaround', 'book_descent']:
            self.book_motion_samples.append({
                't': row['t'], 'category': category, 'yaw': self.yaw(),
                'root': self.d.qpos[:3].tolist(), 'loads': row['loads_n'],
            })


class PaperfreeWorld(ContactWorld, PaperfreeMeasurements):
    """Keep the force controllers and sensors, replacing paper-specific hooks."""
    def __init__(self, seed=211000, record=False, scene=None):
        spec = copy.deepcopy(scene if scene is not None else scene_spec())
        assert all(p['name'] != 'sticky-notes' for p in spec['props'])
        super().__init__(seed, record, scene=spec)
        self.scene['version'] = 'richdesk-v19-paperfree'
        self.flat_legs = []
        assert self.id('geom', 'sticky-notes-contact') == -1
        assert self.id('body', 'sticky-notes') == -1

    def episode(self):
        return {
            **super().episode(),
            'validity_revision': 'paperfree-v19: paper absent; no crossing predicate; task/contact/balance limits preserved',
            'scene_revision': 'richdesk-v19-paperfree',
            'flat_legs': copy.deepcopy(getattr(self, 'flat_legs', [])),
            'paper_geometry_present': self.id('geom', 'sticky-notes-contact') >= 0,
        }


def restore(saved, record=False):
    w = restore_physics(saved, record)
    w.__class__ = PaperfreeWorld
    w.prepare_measurements()
    assert w.id('geom', 'sticky-notes-contact') == -1
    return w
