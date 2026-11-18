"""Validate restored native leg chains with the published walking foundation."""
import xml.etree.ElementTree as ET,math,json
import mujoco,numpy as np
from mochi.desk.g1_model import build,ROOT,ARMS
from mochi.curriculum.locomotion import Walker,DEFAULT,LEGS,fmt

def run(seconds=3.,velocity=(.08,0,0)):
 xml,meta=build(moving_legs=True);r=ET.fromstring(xml);pelvis=r.find('./worldbody/body');ET.SubElement(pelvis,'freejoint',name='free-base');r.find('option').set('timestep',str(.002*math.sqrt(meta['scale'])));r.find('default/geom').set('solref',f'{.02*math.sqrt(meta["scale"])} 1');r.find('default/geom').set('solimp',f'.9 .95 {.001*meta["scale"]}');ET.SubElement(r.find('worldbody'),'geom',type='plane',size='10 10 .1',friction='1 .005 .0001')
 m=mujoco.MjModel.from_xml_string(ET.tostring(r,encoding='unicode'));d=mujoco.MjData(m);w=Walker(m,d,meta['scale'],[meta['home_joint_offsets'][n] for n in LEGS]);arms=[]
 for side in ARMS:
  for name in ARMS[side]:
   j=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,name);q=int(m.jnt_qposadr[j]);v=int(m.jnt_dofadr[j]);a=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_ACTUATOR,name);d.qpos[q]=-meta['home_joint_offsets'][name];d.ctrl[a]=d.qpos[q];arms.append(v)
 mujoco.mj_forward(m,d);start=d.qpos[:3].copy();tilt=0;frames=[]
 for step in range(int(seconds/m.opt.timestep)):
  w.command(velocity);d.qfrc_applied[arms]=d.qfrc_bias[arms];mujoco.mj_step(m,d);tilt=max(tilt,math.acos(float(np.clip(d.xmat[1].reshape(3,3)[2,2],-1,1))))
  if step%25==0:frames.append({'t':float(d.time),'positions':d.xpos.tolist(),'quaternions':d.xquat.tolist()})
  if tilt>math.radians(55):break
 return {'start':start.tolist(),'end':d.qpos[:3].tolist(),'max_tilt_deg':math.degrees(tilt),'seconds':float(d.time),'body_names':[mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,i) or 'world' for i in range(m.nbody)],'frames':frames}
if __name__=='__main__':
 r=run();out=ROOT/'artifacts/curriculum';out.mkdir(parents=True,exist_ok=True);(out/'restored-walking.json').write_text(json.dumps(r));print({k:v for k,v in r.items() if k not in ['frames','body_names']})
