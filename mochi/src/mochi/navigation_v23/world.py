"""Layout changes at reset only; the existing G1 physics remains authoritative."""
import hashlib
import math

import mujoco
import numpy as np

from mochi.paperfree_v19.world import PaperfreeWorld


def bounds(w, gid):
    centre, half = w.m.geom_aabb[gid, :3], w.m.geom_aabb[gid, 3:]
    rotation = w.d.geom_xmat[gid].reshape(3, 3)
    centre = w.d.geom_xpos[gid] + rotation @ centre
    radius = abs(rotation) @ half
    return centre - radius, centre + radius


def mechanics_hash(w):
    robot = sorted(w.robot_bodies)
    joints = [j for j in range(w.m.njnt) if int(w.m.jnt_bodyid[j]) in w.robot_bodies]
    values = [w.m.body_mass[robot].tobytes(), w.m.body_inertia[robot].tobytes(),
        w.m.jnt_range[joints].tobytes(), w.m.actuator_gainprm.tobytes(),
        w.m.actuator_biasprm.tobytes(), w.m.actuator_forcerange.tobytes(),
        np.asarray([w.m.opt.timestep]).tobytes()]
    return hashlib.sha256(b''.join(values)).hexdigest()


class NavigationWorld(PaperfreeWorld):
    def __init__(self, layout, seed, record=False):
        super().__init__(seed, record, scene=layout['scene'])
        assert self.d.time == 0
        before = mechanics_hash(self)
        moved = []
        for name, offset in layout['scene'].get('station_offsets', {}).items():
            bid = self.id('body', name)
            assert bid > 0 and int(self.m.body_parentid[bid]) == 0 and bid not in self.robot_bodies, name
            self.m.body_pos[bid] += offset
            moved.append(name)
        mujoco.mj_setConst(self.m, self.d)
        mujoco.mj_forward(self.m, self.d)
        assert mechanics_hash(self) == before
        self.mechanics_sha256 = before
        self.layout = layout
        self.layout_reset_changes = moved
        self.frames = []
        self.capture()

    def obstacles(self):
        result = []
        for gid in range(self.m.ngeom):
            if int(self.m.geom_bodyid[gid]) in self.robot_bodies or gid == self.id('geom', 'desk'):
                continue
            if not self.m.geom_contype[gid] and not self.m.geom_conaffinity[gid]:
                continue
            low, high = bounds(self, gid)
            if high[2] < -.001 or low[2] > .30:
                continue
            result.append({'name': mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_GEOM, gid),
                'minimum': low.tolist(), 'maximum': high.tolist(), 'geom_id': gid})
        return result

    def envelope(self):
        root = self.d.qpos[:2]
        radius = 0.
        feet = []
        for gid in range(self.m.ngeom):
            bid = int(self.m.geom_bodyid[gid])
            if bid not in self.robot_bodies or not (self.m.geom_contype[gid] or self.m.geom_conaffinity[gid]):
                continue
            low, high = bounds(self, gid)
            if high[2] < .0005:
                continue
            for x in [low[0], high[0]]:
                for y in [low[1], high[1]]:
                    radius = max(radius, math.dist(root, [x, y]))
            name = mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_BODY, bid)
            if name.endswith('ankle_roll_link'):
                feet.append({'body': name, 'minimum': low.tolist(), 'maximum': high.tolist()})
        return {'neutral_collision_radius_m': radius, 'swing_and_tracking_allowance_m': .012,
            'planning_radius_m': radius + .012, 'foot_collision_bounds': feet,
            'scope': 'Conservative yaw-invariant disk enclosing measured neutral collision geometry plus a declared swing/tracking allowance. Physical trials remain necessary.'}
