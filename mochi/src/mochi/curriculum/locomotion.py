"""Pinned Unitree walking policy, with explicit miniature similarity scaling."""
from pathlib import Path
import hashlib,json,math,os,xml.etree.ElementTree as ET
import mujoco,numpy as np,torch,yaml
ROOT=Path(os.environ.get('MOCHI_ROOT',Path(__file__).resolve().parents[3]))
SOURCE=ROOT/'assets/robot/locomotion'
CFG=yaml.safe_load((SOURCE/'deploy/deploy_mujoco/configs/g1.yaml').read_text())
LEGS=[side+'_'+part+'_joint' for side in ['left','right'] for part in ['hip_pitch','hip_roll','hip_yaw','knee','ankle_pitch','ankle_roll']]
DEFAULT=np.array(CFG['default_angles']);KP=np.array(CFG['kps']);KD=np.array(CFG['kds'])
torch.set_num_threads(1)

def numbers(s):return np.fromstring(s,sep=' ')
def fmt(v):return ' '.join(f'{float(x):.12g}' for x in np.atleast_1d(v))
def vendor_xml(scale=1.):
 path=SOURCE/'resources/robots/g1_description/g1_12dof.xml';r=ET.parse(path).getroot();r.find('compiler').set('meshdir',str(path.parent/'meshes'))
 for mesh in r.findall('.//asset/mesh'):mesh.set('scale',fmt(np.ones(3)*scale))
 for b in r.findall('.//body'):
  if 'pos' in b.attrib:b.set('pos',fmt(numbers(b.get('pos'))*scale))
 for e in r.findall('.//inertial'):
  e.set('pos',fmt(numbers(e.get('pos'))*scale));e.set('mass',str(float(e.get('mass'))*scale**3));e.set('diaginertia',fmt(numbers(e.get('diaginertia'))*scale**5))
 for g in r.findall('.//geom'):
  for a in ['pos','size','fromto']:
   if a in g.attrib:g.set(a,fmt(numbers(g.get(a))*scale))
 for j in r.findall('.//joint'):
  for a,power in [('pos',1),('actuatorfrcrange',4),('damping',4.5),('armature',5),('frictionloss',4)]:
   if a in j.attrib:j.set(a,fmt(numbers(j.get(a))*scale**power))
 ET.SubElement(r,'option',timestep=str(.002*math.sqrt(scale)),integrator='implicitfast',iterations='90')
 ET.SubElement(r.find('default'),'geom',solref=f'{.02*math.sqrt(scale)} 1',solimp=f'.9 .95 {.001*scale}')
 ET.SubElement(r.find('worldbody'),'geom',name='desk',type='plane',size='10 10 .1',friction='1 .005 .0001')
 return ET.tostring(r,encoding='unicode')

class Walker:
 def __init__(self,m,d,scale=1.,offsets=None,velocity_feedback=True):
  self.velocity_feedback=velocity_feedback;self.m=m;self.d=d;self.scale=scale;self.time_scale=math.sqrt(scale);self.policy=torch.jit.load(str(SOURCE/'deploy/pre_train/g1/motion.pt'),map_location='cpu').eval();self.action=np.zeros(12,dtype=np.float32);self.target=DEFAULT.copy();self.offsets=np.zeros(12) if offsets is None else np.array(offsets)
  js=[mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,n) for n in LEGS];self.qids=np.array([m.jnt_qposadr[j] for j in js]);self.vids=np.array([m.jnt_dofadr[j] for j in js]);self.aids=np.array([mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_ACTUATOR,n) for n in LEGS]);self.last=-1.;self.velocity_integral=np.zeros(2);self.yaw_integral=0.
 def command(self,velocity):
  m,d=self.m,self.d
  if d.time-self.last>=.02*self.time_scale-1e-9:
   self.last=float(d.time);q=d.qpos[3:7];w,x,y,z=q;gravity=np.array([2*(-z*x+w*y),-2*(z*y+w*x),1-2*(w*w+z*z)])
   desired=np.array(velocity,dtype=float)
   if self.velocity_feedback:
    rotation=d.xmat[1].reshape(3,3);actual=rotation.T@d.qvel[:3];error=desired[:2]-actual[:2];self.velocity_integral=np.clip(self.velocity_integral+error*.02*self.time_scale,-.025,.025);desired[:2]=np.clip(desired[:2]+.7*error+1.4*self.velocity_integral,-.12,.12);yaw_error=desired[2]-d.qvel[5];self.yaw_integral=float(np.clip(self.yaw_integral+yaw_error*.02*self.time_scale,-.25,.25));desired[2]=float(np.clip(desired[2]+.35*yaw_error+.4*self.yaw_integral,-1.8,1.8))
   phase=(d.time/self.time_scale% .8)/.8;obs=np.r_[d.qvel[3:6]*self.time_scale*.25,gravity,desired*np.array([1/self.time_scale,1/self.time_scale,self.time_scale])*np.array(CFG['cmd_scale']),(d.qpos[self.qids]+self.offsets-DEFAULT),d.qvel[self.vids]*self.time_scale*.05,self.action,[math.sin(2*math.pi*phase),math.cos(2*math.pi*phase)]].astype(np.float32)
   with torch.no_grad():self.action=self.policy(torch.from_numpy(obs)[None]).numpy().reshape(12)
   self.target=self.action*.25+DEFAULT-self.offsets
  tau=(self.target-d.qpos[self.qids])*KP*self.scale**4-d.qvel[self.vids]*KD*self.scale**4.5
  self.d.ctrl[self.aids]=tau

def smoke(scale=1.,seconds=4.,velocity=(.3,0,0)):
 m=mujoco.MjModel.from_xml_string(vendor_xml(scale));d=mujoco.MjData(m);w=Walker(m,d,scale,velocity_feedback=False);d.qpos[w.qids]=DEFAULT;mujoco.mj_forward(m,d);start=d.qpos[:3].copy();max_tilt=0.;frames=[]
 for step in range(int(seconds/m.opt.timestep)):
  w.command(np.array(velocity)*np.array([math.sqrt(scale),math.sqrt(scale),1/math.sqrt(scale)]));mujoco.mj_step(m,d);tilt=math.acos(float(np.clip(d.xmat[1].reshape(3,3)[2,2],-1,1)));max_tilt=max(max_tilt,tilt)
  if step%50==0:frames.append({'t':float(d.time),'base':d.qpos[:7].tolist()})
  if tilt>1.1:break
 return {'scale':scale,'seconds':float(d.time),'native_velocity_command':list(velocity),'start':start.tolist(),'end':d.qpos[:3].tolist(),'max_tilt_deg':math.degrees(max_tilt),'fall':bool(max_tilt>math.radians(30)),'frames':frames,'policy_sha256':hashlib.sha256((SOURCE/'deploy/pre_train/g1/motion.pt').read_bytes()).hexdigest()}

if __name__=='__main__':
 out=ROOT/'artifacts/curriculum';out.mkdir(parents=True,exist_ok=True)
 for scale in [1.,.16706410701699295]:
  r=smoke(scale,seconds=4.*math.sqrt(scale));(out/f'walking-source-{scale:.5f}.json').write_text(json.dumps(r,indent=2));print({k:v for k,v in r.items() if k!='frames'},flush=True)
