"""Same physical model, with contact-derived steps sampled at 100 Hz."""
import math
import numpy as np

from ..directional_v14.probe import NavigationWorld
from ..terrain_v12.development import state as original_state, restore as original_restore
from .steps import StepCounter


class EfficientWorld(NavigationWorld):
    def __init__(self, *args, **kwargs):
        self.step_counter = StepCounter()
        self.efficiency_segment = 'initialization'
        super().__init__(*args, **kwargs)

    def step(self, *args, **kwargs):
        super().step(*args, **kwargs)
        if not self.measurements or 'feet' in self.measurements[-1]:
            return
        row = self.measurements[-1]
        feet = {}
        for side in ['left','right']:
            body = self.id('body', side+'_ankle_roll_link')
            R = self.d.xmat[body].reshape(3,3)
            feet[side] = {'position': (self.d.xpos[body] + R@np.array([.0058,0,-.00585])).tolist(),
                          'yaw': math.atan2(R[1,0], R[0,0])}
        category = self.efficiency_segment
        if self.phase == 'turn':
            category = 'turning'
        elif self.phase == 'walk' and self.events and self.events[-1].get('phase') == 'task-alignment':
            category = 'alignment'
        row['feet'] = feet
        row['step_category'] = category
        self.step_counter.update(row['t'], feet, row['loads_n'], category)

    def episode(self):
        no_support = longest = total = 0.
        native_acceleration=[]
        native_torque_change=[]
        for a,b in zip(self.measurements,self.measurements[1:]):
            if b['t'] < .4:
                continue
            dt = b['t']-a['t']
            if a['gait_phase']==b['gait_phase']=='native-walk':
                native_acceleration.extend(((np.asarray(b['qd'])-a['qd'])/dt).tolist())
                native_torque_change.extend((np.asarray(b['tau'])-a['tau']).tolist())
            if sum(b['loads_n'].values()) < .1:
                no_support += dt
                total += dt
                longest=max(longest,no_support)
            else:
                no_support=0.
        return {**super().episode(), 'steps': self.step_counter.summary(),
                'step_events': self.step_counter.events,
                'step_thresholds': vars(self.step_counter.thresholds),
                'unsupported_seconds': total, 'longest_unsupported_seconds': longest,
                'efficiency_validity': longest <= .06,
                'native_smoothness':{
                    'sampled_acceleration_rms_rad_s2':float(np.sqrt(np.mean(np.square(native_acceleration)))) if native_acceleration else None,
                    'sampled_torque_change_rms_nm':float(np.sqrt(np.mean(np.square(native_torque_change)))) if native_torque_change else None,
                    'scope':'Only adjacent samples inside native walking and turning, excluding holds and book-controller phases.'},
                'step_measurement_scope': '100-Hz measured sole poses and normal contact loads; frozen detector for every model.'}


def state(w, include_history=False):
    saved = original_state(w, include_history=include_history)
    if not include_history:
        saved['world']['direction_samples'] = saved['world']['direction_samples'][-30:]
        saved['world']['navigation_traces'] = []
    return saved


def restore(saved, record=False):
    w = original_restore(saved, record)
    w.__class__ = EfficientWorld
    return w


def branch(w):
    return restore(state(w), record=False)
