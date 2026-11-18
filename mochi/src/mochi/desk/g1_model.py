"""Uniformly miniaturize the licensed Menagerie G1; retain native arm chains.

Legs, waist and fingers are held at the vendor stand keyframe. Both seven-DOF
arms retain their native joint axes. The pelvis is fixed to the experiment.
"""
from pathlib import Path
import copy,json,math,xml.etree.ElementTree as ET
import mujoco,numpy as np

ROOT=Path(__file__).resolve().parents[3];SOURCE=ROOT/'assets/robot/g1';HEIGHT=.221;PAD_RADIUS=.0025
ARMS={side:[side+'_'+suffix+'_joint' for suffix in ['shoulder_pitch','shoulder_roll','shoulder_yaw','elbow','wrist_roll','wrist_pitch','wrist_yaw']] for side in ['left','right']}
def values(v):return np.fromstring(v,sep=' ')
def fmt(v):return ' '.join(f'{float(x):.12g}' for x in np.atleast_1d(v))
def quat_matrix(q):
    r=np.zeros(9);mujoco.mju_quat2Mat(r,np.asarray(q));return r.reshape(3,3)

def build():
    original=mujoco.MjModel.from_xml_path(str(SOURCE/'g1_with_hands.xml'));d=mujoco.MjData(original);mujoco.mj_resetDataKeyframe(original,d,0);mujoco.mj_forward(original,d)
    points=[]
    for i in range(original.ngeom):
        if original.geom_type[i]==mujoco.mjtGeom.mjGEOM_MESH and original.geom_group[i]==2:
            mi=original.geom_dataid[i];v=original.mesh_vert[original.mesh_vertadr[mi]:original.mesh_vertadr[mi]+original.mesh_vertnum[mi]]
            points.append(v@d.geom_xmat[i].reshape(3,3).T+d.geom_xpos[i])
    points=np.concatenate(points);minimum=float(points[:,2].min());scale=HEIGHT/float(np.ptp(points[:,2]));tree=ET.parse(SOURCE/'g1_with_hands.xml');root=tree.getroot()
    root.set('model','Mochi miniature G1 supported manipulation');root.find('compiler').set('meshdir',str(SOURCE/'assets'));root.find('option').set('timestep','.002');root.find('option').set('iterations','90')
    for tag in ['actuator','keyframe','sensor','tendon','equality']:
        for e in root.findall(tag):root.remove(e)
    for default in root.findall('.//default'):
        for p in list(default.findall('position')):default.remove(p)
    ET.SubElement(root.find('default'),'geom',solref='.004 1',solimp='.95 .99 .001')
    kept=set(sum(ARMS.values(),[]));offsets={}
    for body in root.findall('.//worldbody//body'):
        name=body.get('name');bid=mujoco.mj_name2id(original,mujoco.mjtObj.mjOBJ_BODY,name);pid=int(original.body_parentid[bid])
        rp=d.xmat[pid].reshape(3,3);position=rp.T@(d.xpos[bid]-d.xpos[pid]);rotation=rp.T@d.xmat[bid].reshape(3,3);q=np.zeros(4);mujoco.mju_mat2Quat(q,rotation.reshape(-1))
        body.set('pos',fmt(position*scale));body.set('quat',fmt(q))
        for key in ['euler','axisangle','xyaxes','zaxis']:body.attrib.pop(key,None)
        for free in list(body.findall('freejoint')):body.remove(free)
        for joint in list(body.findall('joint')):
            jname=joint.get('name')
            if jname not in kept:body.remove(joint);continue
            jid=mujoco.mj_name2id(original,mujoco.mjtObj.mjOBJ_JOINT,jname);offset=float(d.qpos[original.jnt_qposadr[jid]]);offsets[jname]=offset
            assert np.linalg.norm(original.jnt_pos[jid])<1e-8
            joint.set('range',fmt(original.jnt_range[jid]-offset));joint.set('damping','.001');joint.set('armature','.00004');joint.set('frictionloss','.00001')
        for inertial in body.findall('inertial'):
            inertial.set('pos',fmt(values(inertial.get('pos','0 0 0'))*scale));inertial.set('mass',fmt(float(inertial.get('mass'))*scale**3))
            for attr in ['diaginertia','fullinertia']:
                if attr in inertial.attrib:inertial.set(attr,fmt(values(inertial.get(attr))*scale**5))
    for mesh in root.findall('.//asset/mesh'):mesh.set('scale',fmt(values(mesh.get('scale','1 1 1'))*scale))
    for geom in root.findall('.//geom'):
        for attr in ['pos','size','fromto']:
            if attr in geom.attrib:geom.set(attr,fmt(values(geom.get(attr))*scale))
    for site in root.findall('.//site'):
        for attr in ['pos','size']:
            if attr in site.attrib:site.set(attr,fmt(values(site.get(attr))*scale))
    pelvis=root.find('./worldbody/body');pelvis.set('pos',fmt([0,0,(d.xpos[1,2]-minimum)*scale]));pelvis.set('quat','1 0 0 0')
    pads={}
    for side in ['left','right']:
        wrist=root.find(f'.//body[@name="{side}_wrist_yaw_link"]');sign=-1 if side=='left' else 1;pos=np.array([.225,0,0])*scale;pads[side]=pos.tolist()
        ET.SubElement(wrist,'geom',name=side+'-push-pad',type='sphere',pos=fmt(pos),size=str(PAD_RADIUS),mass='.00008',friction='1 .005 .0001',rgba='.08 .10 .10 1',group='2')
        ET.SubElement(wrist,'site',name=side+'-push-tip',pos=fmt(pos),size='.0005')
    actuator=ET.SubElement(root,'actuator')
    for side in ['left','right']:
        for name in ARMS[side]:
            joint=root.find(f'.//joint[@name="{name}"]');ET.SubElement(actuator,'position',name=name,joint=name,kp='8',kv='.05',ctrlrange=joint.get('range'),forcerange='-.12 .12')
    for i,geom in enumerate(root.findall('./worldbody//geom')):
        if not geom.get('name'):geom.set('name','g1-geom-'+str(i))
    metadata={'source':json.loads((SOURCE/'source.json').read_text()),'scale':scale,'height_m':HEIGHT,'pelvis_height_m':float(values(pelvis.get('pos'))[2]),'source_minimum_z':minimum,'scope':'Uniformly scaled native G1 meshes and arm kinematics; supported pelvis, fixed stand legs/waist/fingers; additional rubber push pads; tuned miniature actuators, not manufacturer hardware validation.','arm_joints':ARMS,'home_joint_offsets':offsets,'push_pad_local_positions':pads,'push_pad_radius_m':PAD_RADIUS}
    return ET.tostring(root,encoding='unicode'),metadata

TEMPLATE,METADATA=build()

def station(task,free_base=False,base_xy=None):
    xy=([.080,.045] if free_base else [.065,.065]) if task=='globe' else [.070,-.010]
    if base_xy is not None:xy=list(base_xy)
    return [*xy,METADATA['pelvis_height_m']],math.pi/2 if task=='laptop' else 0.

def model_xml(s,free_base=False):
    from .tasks import xml as prototype_xml
    root=ET.fromstring(TEMPLATE);old=ET.fromstring(prototype_xml(s));world=root.find('worldbody');pelvis=world.find('body');position,yaw=station(s['task'],free_base,s.get('free_base_xy'));pelvis.set('pos',fmt(position));pelvis.set('quat',fmt([math.cos(yaw/2),0,0,math.sin(yaw/2)]))
    if free_base:
        root.set('model','Mochi miniature G1 free-base manipulation');ET.SubElement(pelvis,'freejoint',name='free-base')
    if s['task']=='globe':old.find(".//joint[@name='object-angle']").set('damping','.0005')
    for element in old.find('worldbody'):
        if element.get('name')!='pelvis':world.append(copy.deepcopy(element))
    return ET.tostring(root,encoding='unicode')
