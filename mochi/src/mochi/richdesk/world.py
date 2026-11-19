"""Additive desk world. Archived V8 physics and checkpoints are untouched."""
import copy
import json
import math
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from ..control_v8.manipulation import ControlWorld
from ..curriculum.world import ROOT, SCALE, xml as original_xml, fmt
from ..curriculum.locomotion import Walker


def scene_spec():
    return json.loads((ROOT / 'configs/richdesk-v9.json').read_text())


def make_xml(scenario, scene):
    r = ET.fromstring(original_xml(scenario))
    r.set('model', 'Mochi used desk and physical book stairs')
    world = r.find('worldbody')
    for name in ['alarm-clock', 'globe', 'globe-base']:
        body = world.find(f'body[@name="{name}"]')
        offset = scene['clock_offset'] if name == 'alarm-clock' else scene['globe_offset']
        body.set('pos', fmt(np.fromstring(body.get('pos'), sep=' ') + offset))
    for p in scene['props']:
        x, y, z = p['pos']; sx, sy, sz = p['size']; yaw = p['yaw']
        b = ET.SubElement(world, 'body', name=p['name'], pos=fmt([x, y, z]),
                          quat=fmt([math.cos(yaw/2), 0, 0, math.sin(yaw/2)]))
        a = dict(name=p['name']+'-contact', friction='1 .005 .0001', solref='.004 1')
        if p['shape'] == 'capsule':
            ET.SubElement(b, 'geom', **a, type='capsule', size=str(sz/2),
                          fromto=fmt([-sx/2+sz/2,0,sz/2,sx/2-sz/2,0,sz/2]))
        elif p['shape'] == 'cylinder':
            ET.SubElement(b, 'geom', **a, type='cylinder', size=fmt([max(sx,sy)/2, sz/2]), pos=fmt([0,0,sz/2]))
        else:
            ET.SubElement(b, 'geom', **a, type='box', size=fmt([sx/2, sy/2, sz/2]), pos=fmt([0,0,sz/2]))
    return ET.tostring(r, encoding='unicode')


class DeskWorld(ControlWorld):
    def __init__(self, seed=30000, record=False, scene=None):
        super().__init__(seed, False)
        self.scene = copy.deepcopy(scene or scene_spec())
        pose = self.scene['initial_pose']
        self.s.update(start_xy=pose[:2], start_yaw=pose[2])
        oldm, oldd = self.m, self.d
        self.m = mujoco.MjModel.from_xml_string(make_xml(self.s, self.scene))
        self.d = mujoco.MjData(self.m)
        assert self.m.nq == oldm.nq and self.m.nu == oldm.nu
        self.d.qpos[7:] = oldd.qpos[7:]
        self.d.ctrl[:] = oldd.ctrl
        self.m.actuator_ctrllimited[:] = oldm.actuator_ctrllimited
        self.m.actuator_forcelimited[:] = oldm.actuator_forcelimited
        self.m.actuator_forcerange[:] = oldm.actuator_forcerange
        self.walker = Walker(self.m, self.d, SCALE, self.walker.offsets)
        self.viz = mujoco.MjData(self.m)
        self.standing_mode = None
        self.record = record
        self.frames = []
        self.support_geoms = {self.id('geom', 'desk')} | {
            self.id('geom', p['name']+'-contact') for p in self.scene['props']}
        self.book_geoms = {self.id('geom',p['name']+'-contact') for p in self.scene['props'] if p.get('climb')}
        self.metrics = {'samples': 0, 'tilt_squared': 0., 'slip_m': 0., 'loaded_seconds': 0.,
                        'nonfoot_terrain_contacts': 0, 'maximum_height_m': 0., 'yaw_accel_squared':0.}
        self.next_metric = 0.; self.previous_yaw_rate = 0.; self.previous_metric_time = 0.
        mujoco.mj_forward(self.m, self.d)
        self.capture()

    def terrain_height(self, x, y, margin=0.):
        height = 0.
        for p in self.scene['props']:
            if not p.get('climb'): continue
            dx,dy=x-p['pos'][0],y-p['pos'][1];c,s=math.cos(p['yaw']),math.sin(p['yaw'])
            u,v=c*dx+s*dy,-s*dx+c*dy
            if abs(u)<=p['size'][0]/2+margin and abs(v)<=p['size'][1]/2+margin:
                height=max(height,p['pos'][2]+p['size'][2])
        return height

    def foot_state(self):
        if not hasattr(self,'support_geoms'): return super().foot_state()
        contacts={s:False for s in ['left','right']};speed={s:0. for s in contacts}
        for i,c in enumerate(self.d.contact):
            g1,g2=int(c.geom1),int(c.geom2)
            if not self.support_geoms.intersection([g1,g2]):continue
            if abs(float(c.frame[2]))<.7:continue
            other=g2 if g1 in self.support_geoms else g1
            b=int(self.m.geom_bodyid[other]);name=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_BODY,b) or ''
            for side in contacts:
                if name==side+'_ankle_roll_link':
                    force=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,force)
                    if force[0]>.05:
                        contacts[side]=True;J=np.zeros((3,self.m.nv));mujoco.mj_jac(self.m,self.d,J,None,c.pos,b)
                        speed[side]=max(speed[side],float(np.linalg.norm((J@self.d.qvel)[:2])))
        return contacts,speed

    def hand_target(self, task, phase):
        target,normal=super().hand_target(task,phase)
        if task=='alarm':target=target+np.array(self.scene['clock_offset'])
        elif task=='globe':target=target+np.array(self.scene['globe_offset'])
        return target,normal

    def foot_touching(self, side):
        """Touchdown contact; separate from the 0.05 N loaded-foot metric."""
        body=self.id('body',side+'_ankle_roll_link')
        R=self.d.xmat[body].reshape(3,3)
        if R[2,2]<math.cos(math.radians(3.)):return False
        sole=self.d.xpos[body]+R@np.array([.005,0,-.00585])
        for i,c in enumerate(self.d.contact):
            a,b=int(c.geom1),int(c.geom2)
            other=b if a in self.support_geoms else a if b in self.support_geoms else -1
            if other<0 or int(self.m.geom_bodyid[other])!=body:continue
            if abs(float(c.frame[2]))<.7:continue
            force=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,force)
            if c.dist<.0004 and force[0]>.0005 and abs(sole[2]-c.pos[2])<.0012:return True
        return False

    def capture(self):
        super().capture()
        if self.record and self.frames:
            self.frames[-1]['support_phase']=getattr(self.walker,'stage',None)
            self.frames[-1]['swing_foot']=(['left','right'][self.walker.swing] if hasattr(self.walker,'swing') else None)

    def step(self,*a,**kw):
        previous_fall=self.fall
        super().step(*a,**kw)
        # The archived flat-desk cutoff called a deliberate deep crouch a
        # fall. This new terrain study uses declared pelvis clearance plus
        # tilt and real non-foot ground contact; all V10 comparisons must use
        # this same verifier. It never edits state or prevents a collision.
        tilt=math.acos(float(np.clip(self.d.xmat[1,8],-1,1)))
        low=float(self.d.qpos[2])-self.terrain_height(*self.d.qpos[:2])<.080
        ground_contact=False
        for i,c in enumerate(self.d.contact):
            a,b=int(c.geom1),int(c.geom2)
            if not self.support_geoms.intersection([a,b]):continue
            other=b if a in self.support_geoms else a;body=int(self.m.geom_bodyid[other])
            name=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_BODY,body) or ''
            if body not in self.robot_bodies or name.endswith('ankle_roll_link'):continue
            force=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,force)
            if force[0]>.05 and abs(float(c.frame[2]))>.7:ground_contact=True
        self.fall=bool(previous_fall or tilt>math.radians(30) or low or ground_contact
                       or abs(self.d.qpos[0])>.59 or abs(self.d.qpos[1])>.39)
        if self.d.time < self.next_metric:return
        dt=float(self.d.time)-self.previous_metric_time;self.previous_metric_time=float(self.d.time)
        self.next_metric=float(self.d.time)+.01
        if self.phase!='walk':return
        contact,speeds=self.foot_state();m=self.metrics;m['samples']+=1
        m['tilt_squared']+=math.acos(float(np.clip(self.d.xmat[1,8],-1,1)))**2
        m['slip_m']+=sum(speeds.values())*dt;m['loaded_seconds']+=sum(contact.values())*dt
        m['maximum_height_m']=max(m['maximum_height_m'],float(self.d.qpos[2])-self.meta['pelvis_height_m'])
        rate=float(self.d.qvel[5]);m['yaw_accel_squared']+=((rate-self.previous_yaw_rate)/max(dt,1e-6))**2;self.previous_yaw_rate=rate
        for c in self.d.contact:
            g1,g2=int(c.geom1),int(c.geom2)
            if not self.book_geoms.intersection([g1,g2]):continue
            other=g2 if g1 in self.book_geoms else g1;b=int(self.m.geom_bodyid[other]);name=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_BODY,b) or ''
            if b in self.robot_bodies and not name.endswith('ankle_roll_link'):m['nonfoot_terrain_contacts']+=1

    def episode(self):
        m=self.metrics;n=max(1,m['samples'])
        return {**super().episode(),'scene':self.scene,
            'validity_revision':'terrain-v2: 80 mm pelvis clearance, 30 degree tilt, non-foot loaded terrain contact, desk boundaries',
            'locomotion_metrics':{
            **m,'torso_tilt_rms_deg':math.degrees(math.sqrt(m['tilt_squared']/n)),
            'yaw_acceleration_rms_rad_s2':math.sqrt(m['yaw_accel_squared']/n),
            'controller':getattr(self.walker,'label','pinned-native-gait'),
            'scope':'Measured physical contact velocities and torso motion; no render-space foot locking.'}}
