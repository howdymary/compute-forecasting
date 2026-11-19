"""New-study measurements and separated stop reasons; same physical scene."""
import math
import mujoco
import numpy as np
from ..richdesk.world import DeskWorld


class BalancedWorld(DeskWorld):
    def __init__(self,*args,**kwargs):
        self.invalid_contact=False;self.contact_failures=[];self.measurements=[];self.next_measurement=0.
        self.path_heading=math.pi/2;self.path_origin=None;self.previous_sample=None
        super().__init__(*args,**kwargs)
        self.path_origin=self.d.qpos[:2].copy()

    @property
    def stopped(self):return self.fall or self.invalid_contact

    def loads(self):
        result={s:0. for s in ['left','right']}
        for i,c in enumerate(self.d.contact):
            a,b=int(c.geom1),int(c.geom2)
            other=b if a in self.support_geoms else a if b in self.support_geoms else -1
            if other<0 or abs(float(c.frame[2]))<.7:continue
            name=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_BODY,int(self.m.geom_bodyid[other])) or ''
            for side in result:
                if name==side+'_ankle_roll_link':
                    force=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,force);result[side]+=max(0.,float(force[0]))
        return result

    def foot_state(self):
        if not hasattr(self,'support_geoms'):return super().foot_state()
        load={s:0. for s in ['left','right']};speed={s:0. for s in load}
        for i,c in enumerate(self.d.contact):
            a,b=int(c.geom1),int(c.geom2);other=b if a in self.support_geoms else a if b in self.support_geoms else -1
            if other<0 or abs(float(c.frame[2]))<.7:continue
            body=int(self.m.geom_bodyid[other]);name=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_BODY,body) or ''
            for side in load:
                if name==side+'_ankle_roll_link':
                    force=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,force);load[side]+=max(0.,float(force[0]))
                    if force[0]>.005:
                        J=np.zeros((3,self.m.nv));mujoco.mj_jac(self.m,self.d,J,None,c.pos,body)
                        speed[side]=max(speed[side],float(np.linalg.norm((J@self.d.qvel)[:2])))
        return {s:load[s]>.05 for s in load},{s:speed[s] if load[s]>.05 else 0. for s in load}

    def step(self,*args,**kwargs):
        previous_fall=self.fall
        if kwargs.get('standing',False) and hasattr(self,'waist'):
            from ..curriculum.world import SCALE
            for q,v,a in self.waist:self.d.ctrl[a]=-100*SCALE**4*self.d.qpos[q]-6*SCALE**4.5*self.d.qvel[v]+self.d.qfrc_bias[v]
        original_offsets=self.walker.offsets
        if kwargs.get('standing',False) and hasattr(self.walker,'standing_target'):
            from ..curriculum.locomotion import DEFAULT
            self.walker.offsets=DEFAULT-self.walker.standing_target
        try:super().step(*args,**kwargs)
        finally:self.walker.offsets=original_offsets
        tilt=math.acos(float(np.clip(self.d.xmat[1,8],-1,1)))
        self.fall=bool(previous_fall or tilt>math.radians(30) or self.d.qpos[2]-self.terrain_height(*self.d.qpos[:2])<.080
                       or abs(self.d.qpos[0])>.59 or abs(self.d.qpos[1])>.39)
        for i,c in enumerate(self.d.contact):
            a,b=int(c.geom1),int(c.geom2)
            other=b if a in self.support_geoms else a if b in self.support_geoms else -1
            if other<0:continue
            body=int(self.m.geom_bodyid[other]);name=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_BODY,body) or ''
            if body not in self.robot_bodies or name.endswith('ankle_roll_link'):continue
            force=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,force)
            if force[0]>.05:
                self.invalid_contact=True
                if not self.contact_failures:
                    self.contact_failures.append({'t':float(self.d.time),'body':name,'fixture':mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_GEOM,a if other==b else b),'force_n':float(force[0]),'normal':c.frame[:3].tolist()})
        if self.d.time<self.next_measurement:return
        self.next_measurement=float(self.d.time)+.01
        R=self.d.xmat[1].reshape(3,3);roll=math.atan2(R[2,1],R[2,2]);normal=np.array([-math.sin(self.path_heading),math.cos(self.path_heading)])
        delta=self.d.qpos[:2]-(self.path_origin if self.path_origin is not None else self.d.qpos[:2])
        legs=self.walker.vids;effort=float(np.sum(abs(self.d.actuator_force[self.walker.aids]*self.d.qvel[legs])))
        from .balance import support
        self.measurements.append({'t':float(self.d.time),'phase':self.phase,'gait_phase':getattr(self.walker,'stage','native'),
          'root':self.d.qpos[:3].tolist(),'lateral_m':float(delta@normal),'roll_rad':roll,
          'roll_velocity_rad_s':float(self.d.qvel[3]),'loads_n':self.loads(),'q':self.d.qpos[self.walker.qids].tolist(),
          'qd':self.d.qvel[legs].tolist(),'tau':self.d.actuator_force[self.walker.aids].tolist(),'effort_w':effort,
          'com':self.d.subtree_com[1].tolist(),'com_target':getattr(self.walker,'com_target',None).tolist() if getattr(self.walker,'com_target',None) is not None else None,
          'path_origin':self.path_origin.tolist() if self.path_origin is not None else None,
          'path_heading':self.path_heading,'support':support(self)})

    def episode(self):
        rows=self.measurements;lat=np.array([r['lateral_m'] for r in rows]);roll=np.array([r['roll_rad'] for r in rows])
        acceleration=[];changes=[]
        for previous,current in zip(rows,rows[1:]):
            dt=current['t']-previous['t']
            acceleration.extend(((np.array(current['qd'])-previous['qd'])/dt).tolist())
            changes.extend((np.array(current['tau'])-previous['tau']).tolist())
        m={'samples':len(rows),'lateral_rms_m':float(np.sqrt(np.mean(lat**2))) if len(lat) else None,
           'lateral_peak_to_peak_m':float(np.ptp(lat)) if len(lat) else None,
           'roll_rms_deg':float(np.degrees(np.sqrt(np.mean(roll**2)))) if len(roll) else None,
           'roll_peak_deg':float(np.degrees(np.max(abs(roll)))) if len(roll) else None,
           'sampled_joint_acceleration_rms_rad_s2':float(np.sqrt(np.mean(np.array(acceleration)**2))) if acceleration else None,
           'sampled_torque_change_rms_nm':float(np.sqrt(np.mean(np.array(changes)**2))) if changes else None,
           'progress_m':float((self.d.qpos[:2]-self.path_origin)@np.array([math.cos(self.path_heading),math.sin(self.path_heading)])) if self.path_origin is not None else 0.,
           'scope':'Straight approach in the declared path frame; report progress, duration, falls and invalid contacts alongside sway.'}
        return {**super().episode(),'physical_model':getattr(self,'model_note','Source G1 collision pads and original inertial properties'),
            'validity_revision':'balanced-v11: same scene and safety limits; falls and invalid contacts reported separately',
            'fall':self.fall,'invalid_contact':self.invalid_contact,'contact_failures':self.contact_failures,
            'balance_measurements':rows,'balance_metrics':m}
