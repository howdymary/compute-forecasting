"""Contact-gated backward clearance before resuming a turn near fixtures."""
import math
import numpy as np

from mochi.balanced.onnx_walk import HoldWalker
from mochi.balanced.sequence import PhysicalStop
from mochi.terrain_v12.contact import ContactWalker


class RetreatWalker(ContactWalker):
    def begin(self, velocity):
        self.anchors = [self.foot(i).copy() for i in [0, 1]]
        self.yaw = self.w.yaw()
        self.body_z = float(self.d.qpos[2])
        self.root_start = self.d.qpos[:3].copy()
        self.com_offset = self.d.xmat[1].reshape(3, 3).T @ (self.d.subtree_com[1] - self.d.qpos[:3])
        self.com_target = self.d.subtree_com[1].copy()
        if not hasattr(self.w, 'terrain_neutral_clearance'):
            self.w.terrain_neutral_clearance = self.body_z - float(np.mean([p[2] for p in self.anchors]))
        self.base_clearance = self.w.terrain_neutral_clearance - self.p.crouch
        # Lift the right foot first, transferring onto the left support away
        # from the globe on the robot's right. This changes references only.
        self.swing = 1
        self.start_shift(velocity)


def clear_globe_turn(w, distance=.08):
    from .approaches import pose_corridor_clear
    start = [*w.d.qpos[:2].tolist(), w.yaw()]
    forward = np.array([math.cos(start[2]), math.sin(start[2])])
    target = [*(np.asarray(start[:2]) - distance * forward).tolist(), start[2]]
    if not pose_corridor_clear(w, start, target):
        raise PhysicalStop('no-clear-backward-departure')
    feet = {s: (w.d.xpos[w.id('body', s + '_ankle_roll_link')]
        + w.d.xmat[w.id('body', s + '_ankle_roll_link')].reshape(3, 3) @ np.array([.005, 0, -.00585]))
        for s in ['left', 'right']}
    landings = []
    for displacement in [distance / 2, distance]:
        for side in ['right', 'left']:
            point = feet[side].copy()
            point[:2] -= displacement * forward
            point[2] = w.terrain_height(*point[:2]) - .00015
            landings.append({'side': side, 'position': point.tolist()})
    w.task, w.phase = None, 'walk'
    w.path_origin, w.path_heading = w.d.qpos[:2].copy(), start[2] + math.pi
    w.efficiency_segment = 'fixture_clearance'
    w.walker = RetreatWalker(w, landings=landings, width=.04, balance_feedback=.5, crouch=.012,
        descent_lift=.006, descent_height_fraction=1., shift_seconds=1.8)
    begin = float(w.d.time)
    while w.d.time - begin < 45:
        w.step((-.02, 0., 0.))
        if w.walker.completed:
            break
    else:
        raise PhysicalStop('contact-retreat-timeout')
    description = w.walker.description()
    w.walker = HoldWalker(w, neutral=True)
    dwell = 0.
    finish = float(w.d.time)
    while w.d.time - finish < 3:
        w.step()
        good = (all(w.foot_touching(s) and w.loads()[s] > .05 for s in ['left', 'right'])
            and np.linalg.norm(w.d.qvel[:3]) < .015 and w.d.qpos[2] > .125)
        dwell = dwell + w.m.opt.timestep if good else 0.
        if dwell >= .4:
            break
    else:
        raise PhysicalStop('contact-retreat-support-dwell')
    row = {'label': 'globe-departure-clearance', 'success': True, 'duration_s': float(w.d.time)-begin,
        'start': start, 'root': w.d.qpos[:3].tolist(), 'requested_backward_distance_m': distance,
        'controller': description, 'scope': 'Shared contact-controller engineering, fixed native weights; all retreat steps and time count.'}
    w.events.append({'phase': 'arrival', 't': float(w.d.time), **row})
    return row
