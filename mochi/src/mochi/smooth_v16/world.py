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
        self.postit_crossings = []
        self.book_motion_samples = []
        super().__init__(*args, **kwargs)
        # The longer route exposed passive hinge creep before hand contact.
        # A physical friction change, never a lid clamp or state reset.
        self.s['laptop_friction']+=.015
        self.m.dof_frictionloss[self.v['laptop']]=self.s['laptop_friction']
        self.scene['version']='richdesk-v16-open-hinge'
        self.scene['physics']={'laptop_hinge_friction_increment_nm':.015,
            'reason':'Hold the initially open lid during the longer route; hand-contact success criteria stay fixed.'}

    def terrain_height(self, x, y, margin=0.):
        height = super().terrain_height(x, y, margin)
        p = next(p for p in self.scene['props'] if p['name']=='sticky-notes')
        dx,dy=x-p['pos'][0],y-p['pos'][1]
        c,s=math.cos(p['yaw']),math.sin(p['yaw'])
        if abs(c*dx+s*dy)<=p['size'][0]/2+margin and abs(-s*dx+c*dy)<=p['size'][1]/2+margin:
            height=max(height,p['pos'][2]+p['size'][2])
        return height

    def step(self, *args, **kwargs):
        from ..balanced.world import BalancedWorld
        from ..balanced.onnx_walk import HubWalker
        from ..balanced.sequence import PhysicalStop, average_velocity
        from .verification import fixture_violation
        if kwargs.get('standing',False) and isinstance(self.walker,HubWalker) and self.walker.mode!='walk':
            kwargs['standing']=False
        BalancedWorld.step(self,*args,**kwargs)
        violation=fixture_violation(self)
        if violation:
            self.invalid_contact=True
            self.contact_failures.append(violation)
        if self.stopped:
            raise PhysicalStop('fall' if self.fall else 'invalid_fixture_contact')
        if self.d.time>=self.next_direction_sample:
            self.direction_samples.append({'t':float(self.d.time),
                'phase':'turn-to-path' if self.phase=='turn' else 'walk-forward',
                'native_walk':isinstance(self.walker,HubWalker) and self.walker.mode=='walk',
                'yaw_rad':self.yaw(),'root':self.d.qpos[:3].tolist(),
                'cycle_averaged_velocity_xy':average_velocity(self,.25).tolist()})
            self.next_direction_sample=float(self.d.time)+.04
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
        if not hasattr(self,'postit_crossings'):
            self.postit_crossings=[]
            self.book_motion_samples=[]
        if category in ['book_turnaround','book_descent']:
            self.book_motion_samples.append({'t':row['t'],'category':category,'yaw':self.yaw(),
                'root':self.d.qpos[:3].tolist(),'loads':row['loads_n']})
        p=next(p for p in self.scene['props'] if p['name']=='sticky-notes')
        for side,foot in feet.items():
            dx,dy=foot['position'][0]-p['pos'][0],foot['position'][1]-p['pos'][1]
            c,s=math.cos(p['yaw']),math.sin(p['yaw'])
            inside=abs(c*dx+s*dy)<p['size'][0]/2-.002 and abs(-s*dx+c*dy)<p['size'][1]/2-.002
            sticky=self.id('geom','sticky-notes-contact')
            body=self.id('body',side+'_ankle_roll_link')
            contact=False
            for hit in self.d.contact:
                a,b=int(hit.geom1),int(hit.geom2)
                other=b if a==sticky else a if b==sticky else -1
                if other>=0 and int(self.m.geom_bodyid[other])==body:
                    contact=True
            if inside and contact and row['loads_n'][side]>.08 and category=='postit_crossing':
                self.postit_crossings.append({'t':row['t'],'side':side,'position':foot['position'],
                    'load_n':row['loads_n'][side],'physical_paper_contact':True})

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
        arm_travel={side:0. for side in ['left','right']}
        for a,b in zip(self.control_telemetry,self.control_telemetry[1:]):
            if a['phase'] in ['walk','turn','recover'] and b['phase'] in ['walk','turn','recover']:
                for side in arm_travel:
                    arm_travel[side]+=float(np.sum(abs(np.asarray(b['q'][side])-a['q'][side])))
        return {**super().episode(), 'validity_revision':'smooth-v16: paper-top foot support allowed; paper edges and nonfoot contact rejected; other task predicates preserved',
                'intertask_arm_joint_travel_rad':arm_travel,
                'postit_crossings':getattr(self,'postit_crossings',[]),
                'book_motion_samples':getattr(self,'book_motion_samples',[]), 'steps': self.step_counter.summary(),
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
    saved['model']['dof_frictionloss']=w.m.dof_frictionloss.copy()
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
