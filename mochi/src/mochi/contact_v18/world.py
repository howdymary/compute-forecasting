"""Contact repair and measured flat-ground motion on the unchanged model."""
import bisect
import math
import mujoco
import numpy as np
from ..smooth_v16.world import EfficientWorld,restore as old_restore

class ContactWorld(EfficientWorld):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.prepare_measurements()

    def prepare_measurements(self):
        self.flat_clearance_samples=[]
        self.flat_smoothness_samples=[]
        self._flat_sample_t=-1.
        self._foot_geoms={}
        for side in ['left','right']:
            b=self.id('body',side+'_ankle_roll_link')
            self._foot_geoms[side]=[g for g in range(self.m.ngeom) if int(self.m.geom_bodyid[g])==b
                    and self.m.geom_type[g]==mujoco.mjtGeom.mjGEOM_SPHERE and self.m.geom_contype[g]]

    def laptop(self,p,horizon):
        if getattr(self,'contact_force_schedule',False):
            from .contact import adaptive_laptop
            return adaptive_laptop(self,p,horizon)
        return super().laptop(p,horizon)

    def step(self,*args,**kwargs):
        if getattr(self,'raised_native_swing',False) and self.efficiency_segment in ['flat_transit','fixture_clearance','lifted_flat_walk','alignment']:
            from ..balanced.onnx_walk import HubWalker
            from .residual import LiftedHubWalker
            if isinstance(self.walker,HubWalker) and not isinstance(self.walker,LiftedHubWalker):
                self.walker.__class__=LiftedHubWalker
        if getattr(self,'parked_arm_transit',False):
            if hasattr(self.walker,'control_arms'):self.walker.control_arms=False
            for arm in self.arm.values():self.d.ctrl[arm['acts']]=arm['rest']
        super().step(*args,**kwargs)
        if not hasattr(self,'_foot_geoms'):return
        eligible=self.efficiency_segment in ['flat_transit','fixture_clearance','lifted_flat_walk','alignment'] and self.phase in ['walk','turn','settle']
        if eligible and self.record and self.d.time-self.last_frame>=.01-1e-7:self.capture()
        if eligible and self.measurements and self.measurements[-1]['t']>self._flat_sample_t:
            row=self.measurements[-1];self._flat_sample_t=row['t']
            clearance={}
            for side,geoms in self._foot_geoms.items():
                clearance[side]=min(float(self.d.geom_xpos[g,2]-self.m.geom_size[g,0]-
                     self.terrain_height(*self.d.geom_xpos[g,:2])) for g in geoms)
            self.flat_clearance_samples.append({'t':row['t'],'clearance_m':clearance,'loads_n':row['loads_n'],
                       'segment':self.efficiency_segment,'category':row['step_category']})
            self.flat_smoothness_samples.append({k:row[k] for k in ['t','qd','tau']})

    def episode(self):
        e=super().episode()
        samples=getattr(self,'flat_clearance_samples',[]);times=[s['t'] for s in samples];peaks=[]
        for event in self.step_counter.events:
            if not event['completed']:continue
            a=bisect.bisect_left(times,event['start_t']);b=bisect.bisect_right(times,event['touchdown_t'])
            side=event['side'];other='right' if side=='left' else 'left'
            values=[s['clearance_m'][side] for s in samples[a:b]
                    if s['loads_n'][side]<.08 and s['loads_n'][other]>.10]
            if values:peaks.append({'side':side,'start_t':event['start_t'],'category':event['category'],'peak_minimum_sole_clearance_m':max(values)})
        moving=[p for p in peaks if p['category'] in ['flat_transit','turning','fixture_clearance']]
        e['flat_foot_clearance']={'completed_swings_measured':len(peaks),
           'fraction_at_least_5mm':sum(p['peak_minimum_sole_clearance_m']>=.005 for p in peaks)/len(peaks) if peaks else None,
           'median_peak_m':float(np.median([p['peak_minimum_sole_clearance_m'] for p in peaks])) if peaks else None,
           'moving_swings_measured':len(moving),
           'moving_fraction_at_least_5mm':sum(p['peak_minimum_sole_clearance_m']>=.005 for p in moving)/len(moving) if moving else None,
           'moving_median_peak_m':float(np.median([p['peak_minimum_sole_clearance_m'] for p in moving])) if moving else None,
           'swings':peaks,'definition':'Lowest physical collision-pad point above the local surface, with the other foot loaded. Same sensor and detector for every policy.'}
        acc=[];change=[]
        for a,b in zip(getattr(self,'flat_smoothness_samples',[]),getattr(self,'flat_smoothness_samples',[])[1:]):
            dt=b['t']-a['t']
            if dt>.03:continue
            acc.extend(((np.asarray(b['qd'])-a['qd'])/dt).tolist());change.extend((np.asarray(b['tau'])-a['tau']).tolist())
        e['flat_actuation_smoothness']={'sampled_acceleration_rms_rad_s2':float(np.sqrt(np.mean(np.square(acc)))) if acc else None,
            'sampled_torque_change_rms_nm':float(np.sqrt(np.mean(np.square(change)))) if change else None,
            'scope':'All flat-ground controllers at 100-Hz measurement, including native and planned steps; book and paper transitions excluded.'}
        e['trajectory']['sampling']='100 Hz on flat transit, 25 Hz elsewhere; use actual timestamps'
        e['trajectory']['sample_hz']=None
        return e

def restore(saved,record=False):
    w=old_restore(saved,record);w.__class__=ContactWorld
    w.prepare_measurements()
    return w
