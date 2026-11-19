"""Optional sole collision refinement contained inside the visible G1 shoe."""
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from ..richdesk.world import make_xml


def flat_sole_xml(scenario,scene):
    root=ET.fromstring(make_xml(scenario,scene))
    for side in ['left','right']:
        foot=root.find(f'.//body[@name="{side}_ankle_roll_link"]')
        for geom in foot.findall('geom'):
            if geom.get('type')=='sphere':geom.set('contype','0');geom.set('conaffinity','0')
        ET.SubElement(foot,'geom',name=side+'-flat-sole',type='box',size='.014 .0055 .0004',
            pos='.0058 0 -.00545',friction='.6 .005 .0001',priority='1',
            solref='.008174695273 1',rgba='.05 .05 .05 1')
    return ET.tostring(root,encoding='unicode')


def install_flat_soles(w):
    oldm,oldd=w.m,w.d;newm=mujoco.MjModel.from_xml_string(flat_sole_xml(w.s,w.scene));newd=mujoco.MjData(newm)
    assert newm.nq==oldm.nq and newm.nu==oldm.nu and newm.nbody==oldm.nbody
    assert np.allclose(newm.body_mass,oldm.body_mass), 'Sole refinement must not alter body mass'
    newd.qpos[:]=oldd.qpos;newd.qvel[:]=oldd.qvel;newd.ctrl[:]=oldd.ctrl
    for name in ['actuator_ctrllimited','actuator_forcelimited','actuator_forcerange']:getattr(newm,name)[:]=getattr(oldm,name)
    def geom(g):return mujoco.mj_name2id(newm,mujoco.mjtObj.mjOBJ_GEOM,mujoco.mj_id2name(oldm,mujoco.mjtObj.mjOBJ_GEOM,int(g)))
    w.support_geoms={geom(g) for g in w.support_geoms};w.book_geoms={geom(g) for g in w.book_geoms}
    w.object_geoms={k:geom(g) for k,g in w.object_geoms.items()};w.hand_geoms={k:{geom(g) for g in values} for k,values in w.hand_geoms.items()}
    w.m,w.d=newm,newd;w.viz=mujoco.MjData(newm)
    w.walker.m=newm;w.walker.d=newd
    mujoco.mj_forward(newm,newd);w.frames=[];w.last_frame=-1.;w.capture()
    w.model_note='Flat sole collision boxes replace four contact spheres; contained within the visible shoe, same bottom height, friction and inertial properties. Engineering model change, not trained improvement.'


def install_native_waist(w):
    """Restore the three real G1 waist joints deleted by the earlier template."""
    from ..desk.g1_model import SOURCE,ARMS
    from ..curriculum.world import SCALE
    from ..curriculum.locomotion import Walker
    xml=flat_sole_xml(w.s,w.scene) if hasattr(w,'model_note') else make_xml(w.s,w.scene)
    root=ET.fromstring(xml);source=ET.parse(SOURCE/'g1_with_hands.xml').getroot();act=root.find('actuator')
    names=['waist_yaw_joint','waist_roll_joint','waist_pitch_joint']
    for name,force in zip(names,[88,50,50]):
        source_body=next(b for b in source.iter('body') if b.find(f'joint[@name="{name}"]') is not None)
        body=root.find(f'.//body[@name="{source_body.get("name")}"]');original=source_body.find(f'joint[@name="{name}"]')
        ET.SubElement(body,'joint',name=name,axis=original.get('axis'),range=original.get('range'),
            damping=str(.001*SCALE**4.5),armature=str(.01*SCALE**5),frictionloss=str(.1*SCALE**4))
        ET.SubElement(act,'motor',name=name,joint=name,ctrlrange=f'{-force*SCALE**4} {force*SCALE**4}',forcerange=f'{-force*SCALE**4} {force*SCALE**4}')
    oldm,oldd=w.m,w.d;m=mujoco.MjModel.from_xml_string(ET.tostring(root,encoding='unicode'));d=mujoco.MjData(m)
    assert m.nq==oldm.nq+3 and m.nu==oldm.nu+3 and np.allclose(m.body_mass,oldm.body_mass)
    d.qpos[:7]=oldd.qpos[:7];d.qvel[:6]=oldd.qvel[:6];d.ctrl[:oldm.nu]=oldd.ctrl
    for j in range(1,oldm.njnt):
        name=mujoco.mj_id2name(oldm,mujoco.mjtObj.mjOBJ_JOINT,j);k=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,name)
        d.qpos[m.jnt_qposadr[k]]=oldd.qpos[oldm.jnt_qposadr[j]];d.qvel[m.jnt_dofadr[k]]=oldd.qvel[oldm.jnt_dofadr[j]]
    for name in ['actuator_ctrllimited','actuator_forcelimited','actuator_forcerange']:getattr(m,name)[:oldm.nu]=getattr(oldm,name)
    w.m,w.d=m,d;w.viz=mujoco.MjData(m);w.walker=Walker(m,d,SCALE,w.walker.offsets)
    w.arm_dofs=[]
    for side,joints in ARMS.items():
        ids=[w.id('joint',n) for n in joints];a=w.arm[side];a['qs']=m.jnt_qposadr[ids];a['vs']=m.jnt_dofadr[ids]
        a['acts']=np.array([w.id('actuator',n) for n in joints]);a['limits']=m.jnt_range[ids];w.arm_dofs.extend(a['vs'])
    w.joints={task:w.id('joint',name) for task,name in zip(['alarm','drawer','laptop','globe'],['alarm-slider','drawer-slider','laptop-hinge','globe-hinge'])}
    w.q={t:int(m.jnt_qposadr[j]) for t,j in w.joints.items()};w.v={t:int(m.jnt_dofadr[j]) for t,j in w.joints.items()}
    w.waist=[(int(m.jnt_qposadr[w.id('joint',n)]),int(m.jnt_dofadr[w.id('joint',n)]),w.id('actuator',n)) for n in names]
    w.meta={**w.meta,'home_joint_offsets':{**w.meta['home_joint_offsets'],**dict.fromkeys(names,0.)}}
    w.model_note=getattr(w,'model_note','Source foot collision pads.')+' Restored native G1 yaw/roll/pitch waist joints and bounded actuators; unchanged mesh body and inertial properties.'
    mujoco.mj_forward(m,d);w.frames=[];w.last_frame=-1.;w.capture()
