"""Detached configuration-space collision checks; never moves a live rollout.

The original World XML remains immutable. This planning copy enables visual
robot meshes and adds conservative per-part clock boxes from its actual GLB.
"""
import json,math,struct,xml.etree.ElementTree as ET
from functools import lru_cache
import mujoco,numpy as np
from ..curriculum.world import World,xml,DT,ROOT,STATIONS,wrap

def quat_matrix(q):
 m=np.zeros(9);mujoco.mju_quat2Mat(m,np.asarray(q,dtype=float));return m.reshape(3,3)
def quat_product(a,b):
 out=np.empty(4);mujoco.mju_mulQuat(out,np.asarray(a),np.asarray(b));return out

def glb_boxes(path):
 raw=path.read_bytes();length,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a;g=json.loads(raw[20:20+length]);nodes=g.get('nodes',[]);result=[];axis=np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1.]])
 def visit(i,parent):
  node=nodes[i]
  if 'matrix' in node:local=np.asarray(node['matrix']).reshape(4,4).T
  else:
   local=np.eye(4);q=node.get('rotation',[0,0,0,1]);local[:3,:3]=quat_matrix([q[3],*q[:3]])@np.diag(node.get('scale',[1,1,1]));local[:3,3]=node.get('translation',[0,0,0])
  transform=parent@local
  if 'mesh' in node:
   bounds=[]
   for p in g['meshes'][node['mesh']]['primitives']:
    a=g['accessors'][p['attributes']['POSITION']];lo,hi=np.array(a['min']),np.array(a['max']);corners=np.array([[x,y,z,1] for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]]);bounds.extend((axis@transform@corners.T).T[:,:3])
   pts=np.array(bounds);result.append({'name':node.get('name',str(i)),'lo':pts.min(0),'hi':pts.max(0)})
  for child in node.get('children',[]):visit(child,transform)
 for i in g['scenes'][g.get('scene',0)]['nodes']:visit(i,np.eye(4))
 return result

@lru_cache(maxsize=1)
def walking_postures():
 w=World(18010);w.d.qpos[:2]=[-.49,-.15];mujoco.mj_forward(w.m,w.d);samples=[w.d.qpos.copy()];times=[]
 for velocity in [(.065,0,0),(0,.025,0),(0,0,1.1)]:
  for i in range(round(.7/DT)):
   w.step(velocity)
   if i in [round(.2/DT),round(.55/DT)] and not w.fall:samples.append(w.d.qpos.copy());times.append(float(w.d.time))
  if w.fall:break
 return samples

class ConfigurationSpace:
 def __init__(self,seed=19000,clearance=.002,walking_envelope=True):
  original=World(seed);tree=ET.fromstring(xml(original.s));robot=tree.find('worldbody/body')
  for geom in robot.iter('geom'):geom.set('contype','1');geom.set('conaffinity','1')
  wb=tree.find('worldbody');self.visual_boxes=glb_boxes(ROOT/'web/desk/assets/sand-clock-case.glb');offset=np.array([-.36,.11,.06])
  for i,box in enumerate(self.visual_boxes):
   lo=box['lo']+offset;hi=box['hi']+offset;ET.SubElement(wb,'geom',name='planning-clock-visual-'+str(i),type='box',pos=' '.join(map(str,(lo+hi)/2)),size=' '.join(map(str,np.maximum((hi-lo)/2,.00001))),contype='1',conaffinity='1',group='5')
  self.m=mujoco.MjModel.from_xml_string(ET.tostring(tree,encoding='unicode'));self.d=mujoco.MjData(self.m);self.d.qpos[:]=original.d.qpos;self.initial=original.d.qpos.copy();self.robot_end=original.id('body','alarm-clock');self.robot_geoms={i for i,b in enumerate(self.m.geom_bodyid) if 0<int(b)<self.robot_end};self.desk=mujoco.mj_name2id(self.m,mujoco.mjtObj.mjOBJ_GEOM,'desk');self.clearance=clearance;self.m.geom_margin[:]=clearance;self.foot_geoms=[i for i in self.robot_geoms if 'ankle_roll_link' in (mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_BODY,int(self.m.geom_bodyid[i])) or '')];self.robot_nq=int(original.m.jnt_qposadr[original.joints['alarm']]);self.samples=walking_postures() if walking_envelope else [self.initial];self.calls=0;self.cache={}
  mujoco.mj_forward(self.m,self.d)
 def bounds(self,g):
  a=self.m.geom_aabb[g];R=self.d.geom_xmat[g].reshape(3,3);center=self.d.geom_xpos[g]+R@a[:3];extent=np.abs(R)@a[3:];return center-extent,center+extent
 def check(self,pose,standing=False):
  key=tuple(round(float(v),5) for v in pose)+(standing,)
  if key in self.cache:return self.cache[key]
  self.calls+=1;answer={'free':True,'minimum_clearance_m':None,'collision':None};yaw=float(pose[2]);qyaw=np.array([math.cos(yaw/2),0,0,math.sin(yaw/2)])
  for sample in ([self.initial] if standing else self.samples):
   self.d.qpos[:]=self.initial;self.d.qpos[:self.robot_nq]=sample[:self.robot_nq];self.d.qpos[:2]=pose[:2];q=sample[3:7];rotation=quat_matrix(q);old_yaw=math.atan2(rotation[1,0],rotation[0,0]);self.d.qpos[3:7]=quat_product(qyaw,quat_product([math.cos(old_yaw/2),0,0,-math.sin(old_yaw/2)],q));mujoco.mj_forward(self.m,self.d)
   for g in self.foot_geoms:
    lo,hi=self.bounds(g)
    if lo[0]<-.6+self.clearance or hi[0]>.6-self.clearance or lo[1]<-.4+self.clearance or hi[1]>.4-self.clearance:answer={'free':False,'collision':'desk-edge','minimum_clearance_m':0.};break
   if not answer['free']:break
   for c in self.d.contact:
    a,b=int(c.geom1),int(c.geom2)
    if self.desk in [a,b] or (a in self.robot_geoms)==(b in self.robot_geoms):continue
    if c.dist<self.clearance-1e-7:
     other=b if a in self.robot_geoms else a;answer={'free':False,'minimum_clearance_m':float(c.dist),'collision':mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_GEOM,other)};break
   if not answer['free']:break
  self.cache[key]=answer;return answer
 def rotation_free(self,xy,a,b):
  delta=wrap(b-a)
  return all(self.check([*xy,a+delta*f])['free'] for f in np.linspace(0,1,max(2,math.ceil(abs(delta)/(math.pi/24))+1)))
 def segment_free(self,a,b,heading):
  distance=float(np.linalg.norm(np.array(b)-a))
  return all(self.check([*(np.array(a)+(np.array(b)-a)*f),heading])['free'] for f in np.linspace(0,1,max(2,math.ceil(distance/.0075)+1)))
 def obstacle_bounds(self):
  self.d.qpos[:]=self.initial;mujoco.mj_forward(self.m,self.d);groups={}
  for g in range(self.m.ngeom):
   if g in self.robot_geoms or g==self.desk:continue
   body=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_BODY,int(self.m.geom_bodyid[g])) or ''
   name=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_GEOM,g) or ''
   group='clock' if 'clock' in name or 'alarm' in body else 'drawer' if any(x in body for x in ['drawer','cabinet']) else 'laptop' if 'laptop' in body else 'globe' if 'globe' in body else None
   if not group:continue
   lo,hi=self.bounds(g)
   if group not in groups:groups[group]=[lo,hi]
   else:groups[group]=[np.minimum(groups[group][0],lo),np.maximum(groups[group][1],hi)]
  return {k:{'lo':a.tolist(),'hi':b.tolist()} for k,(a,b) in groups.items()}
 def projection(self,pose):
  """Conservative 2D hull of actual rest geoms, for annotation only."""
  from scipy.spatial import ConvexHull
  self.check(pose,standing=True);self.d.qpos[:]=self.initial;self.d.qpos[:2]=pose[:2];self.d.qpos[3:7]=[math.cos(pose[2]/2),0,0,math.sin(pose[2]/2)];mujoco.mj_forward(self.m,self.d);points=[];feet=[]
  for g in self.robot_geoms:
   lo,hi=self.bounds(g);corners=[[x,y] for x in [lo[0],hi[0]] for y in [lo[1],hi[1]]];points.extend(corners)
   if g in self.foot_geoms:feet.append(corners)
  points=np.array(points);return {'body_xy':points[ConvexHull(points).vertices].tolist(),'feet_xy':feet,'note':'Rest-pose projected geom bounds; planning uses full height-aware sampled poses.'}
