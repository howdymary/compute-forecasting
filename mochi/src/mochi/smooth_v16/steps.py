"""Contact-derived footstep attempts, including turns and unfinished swings."""
import math
from collections import Counter
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class StepThresholds:
    unload_n: float = .02
    touchdown_n: float = .08
    touchdown_hold_n: float = .05
    minimum_unload_s: float = .03
    touchdown_dwell_s: float = .04
    minimum_motion_m: float = .002
    minimum_rotation_rad: float = math.radians(8)


@dataclass
class StepCounter:
    thresholds: StepThresholds = field(default_factory=StepThresholds)
    feet: dict = field(default_factory=dict)
    events: list = field(default_factory=list)

    def update(self, t, feet, loads, category):
        p = self.thresholds
        for side, pose in feet.items():
            position = np.asarray(pose['position'])
            yaw = pose['yaw']
            if side not in self.feet:
                self.feet[side] = {'anchor': position.copy(), 'yaw': yaw, 'air': None,
                                   'touchdown': None, 'event': None}
            s = self.feet[side]
            load = loads[side]
            if s['air'] is None:
                if load < p.unload_n:
                    s['air'] = float(t)
                    s['category'] = category
                else:
                    s.update(anchor=position.copy(), yaw=yaw)
                continue
            displacement = float(np.linalg.norm(position - s['anchor']))
            rotation = abs((yaw - s['yaw'] + math.pi) % (2*math.pi) - math.pi)
            if s['event'] is None and t-s['air'] >= p.minimum_unload_s and (
                    displacement >= p.minimum_motion_m or rotation >= p.minimum_rotation_rad):
                s['event'] = len(self.events)
                self.events.append({'side': side, 'start_t': s['air'], 'detected_t': float(t),
                    'category': s['category'], 'completed': False,
                    'start_position': s['anchor'].tolist(),'start_yaw':s['yaw']})
            if load >= p.touchdown_n and s['touchdown'] is None:
                s['touchdown'] = float(t)
            if load < p.touchdown_hold_n:
                s['touchdown'] = None
            if s['touchdown'] is not None and t-s['touchdown'] >= p.touchdown_dwell_s:
                if s['event'] is not None:
                    self.events[s['event']].update(completed=True, touchdown_t=s['touchdown'],
                        verified_t=float(t), end_position=position.tolist(), displacement_m=displacement,end_yaw=yaw)
                s.update(anchor=position.copy(), yaw=yaw, air=None, touchdown=None, event=None)

    def summary(self, since=-math.inf):
        rows = [e for e in self.events if e['start_t'] >= since]
        return {'attempts': len(rows), 'completed': sum(e['completed'] for e in rows),
                'unfinished': sum(not e['completed'] for e in rows),
                'by_category': dict(Counter(e['category'] for e in rows)),
                'definition': 'Measured unload, at least 30 ms and 2 mm sole motion or 8 degree rotation, followed by loaded touchdown with 40 ms dwell. Unfinished attempts retained.'}


def archived_counter(episode):
    """Calibrate against existing 25-Hz poses with preceding measured loads."""
    from scipy.spatial.transform import Rotation
    counter = StepCounter()
    names = episode['trajectory']['body_names']
    indices = {s: names.index(s+'_ankle_roll_link') for s in ['left','right']}
    measurements = episode['balance_measurements']
    index = 0
    for frame in episode['trajectory']['frames']:
        while index+1 < len(measurements) and measurements[index+1]['t'] <= frame['t']:
            index += 1
        sample = measurements[index]
        feet = {}
        for side, k in indices.items():
            q = frame['quaternions'][k]
            R = Rotation.from_quat([*q[1:], q[0]]).as_matrix()
            feet[side] = {'position': np.asarray(frame['positions'][k]) + R@np.array([.0058,0,-.00585]),
                          'yaw': math.atan2(R[1,0], R[0,0])}
        counter.update(frame['t'], feet, sample['loads_n'],
            'turning' if frame['phase']=='turn' else 'walking' if frame['phase']=='walk' else frame['phase'])
    return counter
