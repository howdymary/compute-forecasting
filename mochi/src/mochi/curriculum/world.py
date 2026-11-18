"""One physical G1, four passive desktop tasks, and continuous navigation."""
from dataclasses import dataclass,asdict
from functools import lru_cache
import json,math,xml.etree.ElementTree as ET
import mujoco,numpy as np
from scipy.optimize import least_squares
from ..desk.g1_model import build,ARMS,ROOT,PAD_RADIUS,METADATA
from .locomotion import Walker,LEGS,DEFAULT,fmt
TASKS=('alarm','drawer','laptop','globe')
SCALE=METADATA['scale'];DT=.002*math.sqrt(SCALE);CONTROL_DT=.02
STATIONS={'alarm':(-.375,.040,math.pi/2),'drawer':(-.13,.020,math.pi/2),'laptop':(.33,.27,math.pi),'globe':(.35,.225,0.)}
# Explicit waypoint stops avoid the laptop footprint. Target poses are observations.
ROUTE=[('alarm',(-.375,.040,math.pi/2)),('drawer',(-.13,.020,math.pi/2)),('transit',(.33,.025,0.)),('laptop',(.33,.27,math.pi)),('globe',(.35,.225,0.))]
@dataclass(frozen=True)
class Profile:
 code:str;speed:float;depth:float;force:float;brake:float;hold:float
PROFILES=[Profile('A',.012,.0002,.055,.001,.3),Profile('B',.025,.0003,.12,.001,.35),Profile('C',.04,.0006,.22,.002,.25),Profile('D',.016,.0005,.22,.004,.5),Profile('E',.04,.0002,.08,.005,.25),Profile('F',.025,.0008,.30,.0005,.4),Profile('G',.035,.0004,.25,.001,.3),Profile('H',.05,.0003,.18,.001,.25)]
MOVES={'forward':(.065,0,0),'slow':(.025,0,0),'back':(-.025,0,0),'left':(0,0,1.1),'right':(0,0,-1.1),'left_slow':(0,0,.45),'right_slow':(0,0,-.45),'stop':(0,0,0),'side_left':(0,.025,0),'side_right':(0,-.025,0)}

def scenario(seed):
 r=np.random.default_rng(seed)
 return {'seed':seed,'clock_stroke':float(r.uniform(.0035,.0055)),'clock_spring':float(r.uniform(8,14) if seed%2==0 else r.uniform(18,24)),'clock_class':'soft' if seed%2==0 else 'firm','drawer_open':float(r.uniform(.018,.033)),'drawer_friction':float(r.uniform(.008,.016) if seed%2==0 else r.uniform(.025,.035)),'drawer_mass':float(r.uniform(.012,.025)),'drawer_rail':'smooth' if seed%2==0 else 'felt','laptop_angle':float(r.uniform(math.radians(68),math.radians(76))),'laptop_mass':float(r.uniform(.15,.17)),'laptop_friction':float(r.uniform(.05,.06)),'globe_angle':float(r.uniform(-.46,-.32)),'globe_mass':float(r.uniform(.035,.05)),'globe_friction':float(r.uniform(.000025,.000045)),'start_xy':[-.48,float(r.uniform(.016,.030))],'start_yaw':float(r.uniform(-.08,.08))}

@lru_cache(maxsize=1)
def robot_template():return build(moving_legs=True)
def xml(s):
 template,meta=robot_template();r=ET.fromstring(template);r.set('model','Mochi continuous desk curriculum');
 for actuator in r.findall('./actuator/position'):actuator.set('kp','4');actuator.set('kv','.025')
 r.find('option').set('timestep',str(DT));r.find('default/geom').set('solref',f'{.02*math.sqrt(SCALE)} 1');r.find('default/geom').set('solimp',f'.9 .95 {.001*SCALE}')
 world=r.find('worldbody');pelvis=world.find('body');pelvis.set('pos',fmt([*s['start_xy'],meta['pelvis_height_m']]));pelvis.set('quat',fmt([math.cos(s['start_yaw']/2),0,0,math.sin(s['start_yaw']/2)]));ET.SubElement(pelvis,'freejoint',name='free-base')
 for g in r.findall(".//geom"):
  if 'push-pad' in (g.get('name') or ''):g.set('solref','.004 1')
 ET.SubElement(world,'geom',name='desk',type='box',pos='0 0 -.02',size='.6 .4 .02',friction='1 .005 .0001')
 def body(name,pos,parent=world):return ET.SubElement(parent,'body',name=name,pos=fmt(pos))
 def box(parent,name,size,pos=(0,0,0),mass=None):
  args={'name':name,'type':'box','size':fmt(np.array(size)/2),'pos':fmt(pos),'solref':'.004 1'}
  if mass is not None:args['mass']=str(mass)
  return ET.SubElement(parent,'geom',**args)
 clock=body('alarm-clock',(-.36,.11,.06));box(clock,'clock-case',(.075,.05,.116),(0,0,-.002));cap=body('alarm-button',(.025,-.010,.064),clock);ET.SubElement(cap,'joint',name='alarm-slider',type='slide',axis='0 0 -1',range=fmt([0,s['clock_stroke']]),stiffness=str(s['clock_spring']),springref='-.0015',damping='.03');box(cap,'alarm-contact',(.025,.018,.004),mass=.0006)
 cabinet=body('drawer-cabinet',(-.10,.15,0));box(cabinet,'cabinet-left',(.004,.09,.145),(-.052,0,.0725));box(cabinet,'cabinet-right',(.004,.09,.145),(.052,0,.0725));box(cabinet,'cabinet-top',(.108,.09,.004),(0,0,.147));box(cabinet,'cabinet-back',(.108,.004,.145),(0,.046,.0725));box(cabinet,'cabinet-bottom',(.108,.09,.004),(0,0,.002));drawer=body('drawer',(-.10,.103,.12));ET.SubElement(drawer,'joint',name='drawer-slider',type='slide',axis='0 -1 0',range='0 .045',damping='.045',frictionloss=str(s['drawer_friction']));box(drawer,'drawer-contact',(.095,.005,.043),mass=s['drawer_mass']);box(drawer,'drawer-tray',(.091,.065,.002),(0,.033,-.021),mass=.002)
 laptop=body('laptop-base',(.14,.17,.007));box(laptop,'laptop-base-contact',(.25,.17,.014));lid=body('laptop-screen',(.14,.249,.0185));ET.SubElement(lid,'joint',name='laptop-hinge',axis='1 0 0',range=fmt([0,math.pi/2]),solreffriction='.001 1',solimpfriction='.99 .999 .0001',damping='.065',frictionloss=str(s['laptop_friction']));box(lid,'laptop-contact',(.25,.007,.15),(0,0,.075),mass=s['laptop_mass'])
 globe_base=body('globe-base',(.47,.22,0));ET.SubElement(globe_base,'geom',type='cylinder',size='.039 .006',pos='0 0 .006');ET.SubElement(globe_base,'geom',type='cylinder',size='.004 .027',pos='0 0 .038');globe=body('globe',(.47,.22,.123));ET.SubElement(globe,'joint',name='globe-hinge',axis='0 0 1',limited='false',damping='.0005',frictionloss=str(s['globe_friction']));ET.SubElement(globe,'geom',name='globe-contact',type='sphere',size='.058',mass=str(s['globe_mass']),friction='.7 .005 .0001',solref='.004 1')
 return ET.tostring(r,encoding='unicode')

def wrap(a):return float((a+math.pi)%(2*math.pi)-math.pi)

class World:
 def __init__(self,seed=12000,record=False,start_task=None):
  self.s=scenario(seed);self.m=mujoco.MjModel.from_xml_string(xml(self.s));self.d=mujoco.MjData(self.m);self.meta=robot_template()[1];self.walker=Walker(self.m,self.d,SCALE,[self.meta['home_joint_offsets'][n] for n in LEGS]);self.standing_mode=None;self.m.actuator_ctrllimited[self.walker.aids]=False;self.m.actuator_forcelimited[self.walker.aids]=True;self.m.actuator_forcerange[self.walker.aids]=np.array([-139,139])*SCALE**4;self.d.qpos[self.walker.qids]=DEFAULT-self.walker.offsets;self.record=record;self.viz=mujoco.MjData(self.m);self.frames=[];self.events=[];self.decisions=[];self.last_frame=-.04;self.last_arm=-.02;self.task=None;self.phase='walk';self.profile=PROFILES[1];self.t0=0.;self.activated=False;self.hold_start=None;self.release_at=None;self.hand_contacts=0;self.max_force=0.;self.bad_contacts=0;self.fall=False;self.max_tilt=0.;self.base_force=0.;self.ik_cache={};self.results={};self.next_frame=0.;self.prev_angle=None;self.progress_contact=0.;self.stroke=math.pi-.25
  self.arm={};self.arm_dofs=[];self.armrest=np.zeros(14)
  for side in ARMS:
   js=[self.id('joint',n) for n in ARMS[side]];qs=np.array([self.m.jnt_qposadr[j] for j in js]);vs=np.array([self.m.jnt_dofadr[j] for j in js]);acts=np.array([self.id('actuator',n) for n in ARMS[side]]);targets=np.zeros(7);self.d.qpos[qs]=targets;self.d.ctrl[acts]=targets;self.arm[side]={'qs':qs,'vs':vs,'acts':acts,'rest':targets,'limits':self.m.jnt_range[js],'tip':self.id('site',side+'-push-tip')};self.arm_dofs.extend(vs)
  self.joints={t:self.id('joint',n) for t,n in zip(TASKS,['alarm-slider','drawer-slider','laptop-hinge','globe-hinge'])};self.q={t:int(self.m.jnt_qposadr[j]) for t,j in self.joints.items()};self.v={t:int(self.m.jnt_dofadr[j]) for t,j in self.joints.items()};self.d.qpos[self.q['drawer']]=self.s['drawer_open'];self.d.qpos[self.q['laptop']]=math.pi/2-self.s['laptop_angle'];self.d.qpos[self.q['globe']]=self.s['globe_angle'];self.object_geoms={t:self.id('geom',n) for t,n in zip(TASKS,['alarm-contact','drawer-contact','laptop-contact','globe-contact'])};self.hand_geoms={side:set() for side in ARMS};self.robot_bodies=set(range(1,self.id('body','alarm-clock')))
  for g in range(self.m.ngeom):
   mesh=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_MESH,int(self.m.geom_dataid[g])) if self.m.geom_type[g]==mujoco.mjtGeom.mjGEOM_MESH else '';name=mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_GEOM,g) or ''
   for side in ARMS:
    if side+'_hand_' in (mesh or '') or name==side+'-push-pad':self.hand_geoms[side].add(g)
  if start_task:
   x,y,yaw=STATIONS[start_task];self.d.qpos[:3]=[x,y,self.meta['pelvis_height_m']];self.d.qpos[3:7]=[math.cos(yaw/2),0,0,math.sin(yaw/2)]
  mujoco.mj_forward(self.m,self.d);self.capture()
 def id(self,kind,name):return mujoco.mj_name2id(self.m,getattr(mujoco.mjtObj,'mjOBJ_'+kind.upper()),name)
 def yaw(self):return math.atan2(self.d.xmat[1,3],self.d.xmat[1,0])
 def value(self,t):
  q=float(self.d.qpos[self.q[t]])
  return math.pi/2-q if t=='laptop' else q
 def contacts(self,t):
  side='left' if t=='laptop' else 'right';obj=self.object_geoms[t];force=0.;good=False;bad=False
  for c in self.d.contact:
   if obj not in [int(c.geom1),int(c.geom2)]:continue
   other=int(c.geom2) if int(c.geom1)==obj else int(c.geom1)
   if other in self.hand_geoms[side]:
    good=True
   elif int(self.m.geom_bodyid[other]) in self.robot_bodies:bad=True
  for i,c in enumerate(self.d.contact):
   if obj in [int(c.geom1),int(c.geom2)] and bool(self.hand_geoms[side].intersection([int(c.geom1),int(c.geom2)])):
    f=np.zeros(6);mujoco.mj_contactForce(self.m,self.d,i,f);force+=abs(float(f[0]))
  return good,force,bad
 def capture(self):
  if not self.record:return
  self.viz.qpos[:]=self.d.qpos;self.viz.qvel[:]=self.d.qvel;mujoco.mj_forward(self.m,self.viz);self.frames.append({'t':round(float(self.d.time),6),'positions':self.viz.xpos.tolist(),'quaternions':self.viz.xquat.tolist(),'phase':self.phase,'task':self.task,'objects':{t:self.value(t) for t in TASKS},'base_tilt_degrees':math.degrees(math.acos(float(np.clip(self.viz.xmat[1,8],-1,1)))),'hand_contact':bool(self.contacts(self.task)[0]) if self.task else False,'alarm_activated':self.activated});self.last_frame=float(self.d.time)
 def step(self,velocity=(0,0,0),standing=False):
  aids=self.walker.aids;kp=np.array([100,100,100,150,40,40]*2)*SCALE**4*6;kd=np.array([2,2,2,4,2,2]*2)*SCALE**4.5*6
  if self.standing_mode!=standing:
   self.m.actuator_biastype[aids]=mujoco.mjtBias.mjBIAS_AFFINE if standing else mujoco.mjtBias.mjBIAS_NONE;self.m.actuator_gainprm[aids,0]=kp if standing else 1.;self.m.actuator_biasprm[aids,1]=-kp if standing else 0.;self.m.actuator_biasprm[aids,2]=-kd if standing else 0.;self.standing_mode=standing;self.walker.last=-1.
  if standing:
   self.d.ctrl[aids]=DEFAULT-self.walker.offsets;self.d.qfrc_applied[self.walker.vids]=self.d.qfrc_bias[self.walker.vids]
   rot=self.d.xmat[1].reshape(3,3);pitch=math.asin(float(np.clip(-rot[2,0],-1,1)));roll=math.atan2(rot[2,1],rot[2,2]);feet=[self.d.xpos[self.id('body',side+'_ankle_roll_link')] for side in ['left','right']];center=np.mean(feet,axis=0)+rot@np.array([.0058,0,0]);error=rot.T@(self.d.subtree_com[1]-center);mass=float(self.m.body_subtreemass[1]);omega=self.d.qvel[3:6]
   for i in [4,10]:self.d.ctrl[aids[i]]+=(mass*9.81*error[0]/2+.22*pitch+.012*omega[1])/kp[i]
   for i in [5,11]:self.d.ctrl[aids[i]]+=(-mass*9.81*error[1]/2+.22*roll+.012*omega[0])/kp[i]
  else:self.d.qfrc_applied[self.walker.vids]=0;self.walker.command(velocity)
  self.d.qfrc_applied[self.arm_dofs]=self.d.qfrc_bias[self.arm_dofs];mujoco.mj_step(self.m,self.d)
  tilt=math.acos(float(np.clip(self.d.xmat[1,8],-1,1)));self.max_tilt=max(self.max_tilt,tilt);self.fall=bool(self.fall or tilt>math.radians(30) or self.d.qpos[2]<.105 or abs(self.d.qpos[0])>.59 or abs(self.d.qpos[1])>.39);self.base_force=max(self.base_force,float(np.max(np.abs(self.d.qfrc_applied[:6]))))
  if self.d.time-self.last_frame>=.04-1e-7:self.capture()
 def walk_observation(self,goal):
  delta=np.array(goal[:2])-self.d.qpos[:2];yaw=self.yaw();bearing=wrap(math.atan2(delta[1],delta[0])-yaw);distance=float(np.linalg.norm(delta));final=wrap(goal[2]-yaw)
  return {'domain':'walk','distance_mm':round(distance*1000,1),'bearing_degrees':round(math.degrees(bearing),1),'heading_error_degrees':round(math.degrees(final),1),'speed_mm_s':round(float(np.linalg.norm(self.d.qvel[:2]))*1000,1),'body_tilt_degrees':round(math.degrees(math.acos(float(np.clip(self.d.xmat[1,8],-1,1)))),2),'target_forward_mm':round(float(math.cos(yaw)*delta[0]+math.sin(yaw)*delta[1])*1000,1),'target_left_mm':round(float(-math.sin(yaw)*delta[0]+math.cos(yaw)*delta[1])*1000,1),'near_station':distance<.07}
 @staticmethod
 def teacher_move(obs):
  if obs['distance_mm']<18 and abs(obs['heading_error_degrees'])<9:return 'stop'
  if obs['distance_mm']<70:
   angle=obs['heading_error_degrees']
   if abs(angle)>7:return ('left' if angle>0 else 'right')+('_slow' if abs(angle)<25 else '')
   if abs(obs['target_forward_mm'])>9 and abs(obs['target_forward_mm'])>=abs(obs['target_left_mm']):return 'slow' if obs['target_forward_mm']>0 else 'back'
   if abs(obs['target_left_mm'])>9:return 'side_left' if obs['target_left_mm']>0 else 'side_right'
   return 'stop'
  error=obs['bearing_degrees']
  if abs(error)>10:return ('left' if error>0 else 'right')+('_slow' if abs(error)<25 else '')
  return 'forward' if obs['distance_mm']>100 else 'slow'
 def walk_to(self,goal,decide=None,max_seconds=22.):
  self.task=None;self.phase='walk';start=float(self.d.time);self.walker.last=-1.;self.walker.action[:]=0;self.walker.velocity_integral[:]=0;self.walker.yaw_integral=0;command='stop';next_command=-1.;settle=0.
  while self.d.time-start<max_seconds and not self.fall:
   if self.d.time>=next_command and settle==0:
    obs=self.walk_observation(goal);command=self.teacher_move(obs) if decide is None else decide(obs);self.decisions.append({'t':float(self.d.time),'observation':obs,'action':command});next_command=float(self.d.time)+(.64 if obs['distance_mm']>100 else .32)
   obs=self.walk_observation(goal);arrived=(settle>0 or obs['distance_mm']<22) and abs(obs['heading_error_degrees'])<12
   if command=='stop' and arrived:
    self.step(standing=True);settle+=DT
    if settle>.4:return obs['distance_mm']<32
   else:
    settle=0;self.step(MOVES[command])
  return False
 def task_observation(self,t):
  return {'domain':t,'object_state':round(self.value(t),5),'relative_position_mm':((np.array(STATIONS[t][:2])-self.d.qpos[:2])*1000).round(1).tolist(),'body_tilt_degrees':round(math.degrees(math.acos(float(np.clip(self.d.xmat[1,8],-1,1)))),2),'button_travel_mm':round(self.s['clock_stroke']*1000,1) if t=='alarm' else None,'material_cue':self.s['clock_class'] if t=='alarm' else self.s['drawer_rail'] if t=='drawer' else 'friction hinge' if t=='laptop' else 'globe bearing'}
 def hand_target(self,t,phase):
  a=self.value(t);p=self.profile;hover=phase in ['approach','hover'];release=phase=='release'
  if t=='alarm':
   normal=np.array([0.,0.,1.]);point=np.array([-.335,.100,.126]);point[2]-=self.s['clock_stroke']+p.depth if phase in ['push','hold'] else 0.;target=point+normal*(PAD_RADIUS+(.018 if hover or release else 0))
   if phase=='approach' and self.d.time-self.t0<1.6:target=np.array([-.335,.080,.158])
  elif t=='drawer':
   normal=np.array([0.,-1.,0.]);point=np.array([-.092,.103-a,.130]);target=point+normal*(.0025+PAD_RADIUS+(.014 if hover or release else -p.depth))
  elif t=='laptop':
   normal=np.array([0,math.sin(a),math.cos(a)]);point=np.array([.259,.249-.14*math.cos(a),.0185+.14*math.sin(a)]);target=point+normal*(.0035+PAD_RADIUS+(.014 if hover or release else -p.depth))
   if release:target+=np.array([.025,0,.015])
  else:
   normal=np.array([math.cos(self.stroke),math.sin(self.stroke),0.]);target=np.array([.47,.22,.123])+normal*(.058+PAD_RADIUS+(.014 if hover or release else -p.depth))
   if phase=='hold' and self.hold_pose is not None:target=self.hold_pose.copy()
   if release:target[2]+=.012
  return target,normal
 def ik(self,side,target,normal):
  arm=self.arm[side];tmp=self.viz;tmp.qpos[:]=self.d.qpos;tmp.qvel[:]=0;qs=arm['qs'];limits=arm['limits'];tip=arm['tip'];jp=np.zeros((3,self.m.nv));mujoco.mj_forward(self.m,tmp)
  # Solve in separate kinematics data; physical qpos are never overwritten.
  def residual(q):
   tmp.qpos[qs]=q;mujoco.mj_forward(self.m,tmp);penalty=np.zeros(self.m.nbody)
   for contact in tmp.contact:
    b1=int(self.m.geom_bodyid[contact.geom1]);b2=int(self.m.geom_bodyid[contact.geom2]);
    if b1 in self.robot_bodies and b2 in self.robot_bodies and contact.dist<-.0003:penalty[b1]=max(penalty[b1],-float(contact.dist)-.0003)
   return np.r_[tmp.site_xpos[tip]-target,(.006 if self.task=='alarm' else .0005)*(tmp.site_xmat[tip].reshape(3,3)[:,0]+normal),4*penalty]
  opt=least_squares(residual,np.clip(self.d.qpos[qs],limits[:,0]+.00101,limits[:,1]-.00101),bounds=(limits[:,0]+.001,limits[:,1]-.001),max_nfev=35,ftol=1e-7,xtol=1e-7,gtol=1e-8)
  return opt.x
 def do_task(self,t,profile=None,max_seconds=10.):
  self.approach_path=[];self.approach_side='left' if t=='laptop' else 'right';self.task=t;self.profile=profile or PROFILES[1];self.phase='approach';self.t0=float(self.d.time);self.hand_contacts=0;self.max_force=0.;self.bad_contacts=0;self.hold_start=None;self.hold_pose=None;self.release_at=None;self.stroke=math.pi-.25;self.progress_contact=0.;first_angle=None;side='left' if t=='laptop' else 'right';arm=self.arm[side];next_control=-1.;next_ik=-1.;qtarget=self.d.qpos[arm['qs']].copy();dwell=0.
  while self.d.time-self.t0<max_seconds and not self.fall:
   elapsed=float(self.d.time)-self.t0;contact,force,bad=self.contacts(t);self.hand_contacts+=int(contact);self.max_force=max(self.max_force,force);self.bad_contacts+=int(bad);value=self.value(t)
   if contact and first_angle is None:first_angle=value
   if t=='alarm' and value>=self.s['clock_stroke']*.85:self.activated=True
   if self.phase=='approach' and elapsed>1.8 and np.linalg.norm(self.d.site_xpos[arm['tip']]-self.hand_target(t,'hover')[0])<.006:self.phase='push'
   reached=self.activated if t=='alarm' else value<=self.profile.brake if t=='drawer' else value<math.radians(52) if t=='laptop' else value>=-max(.012,self.profile.brake*12)
   if self.phase=='push' and reached:self.phase='hold';self.hold_start=float(self.d.time);self.hold_pose=self.d.site_xpos[arm['tip']].copy();self.progress_contact=0. if first_angle is None else first_angle-value
   if self.phase=='hold' and self.d.time-self.hold_start>self.profile.hold:self.phase='release';self.release_at=float(self.d.time)
   if self.d.time>=next_control:
    if t=='globe' and self.phase=='push' and contact:self.stroke=min(math.pi+.5,self.stroke+self.profile.speed/.058*CONTROL_DT)
    desired,normal=self.hand_target(t,self.phase);current=self.d.site_xpos[arm['tip']].copy();delta=desired-current;max_step=(.045 if self.phase in ['approach','release'] else self.profile.speed)*CONTROL_DT
    if np.linalg.norm(delta)>max_step:delta*=max_step/np.linalg.norm(delta)
    if force>self.profile.force and self.phase=='push':delta=normal*min(.0006,(force-self.profile.force)*.003)
    if self.phase=='approach':
     self.approach_path.append(self.d.qpos[arm['qs']].copy());qtarget=self.ik(side,desired,normal)
    else:
     jac=np.zeros((3,self.m.nv));mujoco.mj_jacSite(self.m,self.d,jac,None,arm['tip']);J=jac[:,arm['vs']];dq=J.T@np.linalg.solve(J@J.T+np.eye(3)*8e-8,delta);qtarget=self.d.qpos[arm['qs']]+dq
    change=qtarget-self.d.ctrl[arm['acts']];change*=min(1.,.018/max(float(np.max(np.abs(change))),1e-8));self.d.ctrl[arm['acts']]=np.clip(self.d.ctrl[arm['acts']]+change,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001);next_control=float(self.d.time)+CONTROL_DT
   self.step(standing=True)
   if int(elapsed*2)!=int((elapsed-DT)*2):
    import os
    if os.environ.get('MOCHI_DEBUG'):print('DEBUG',t,round(elapsed,2),self.phase,round(value,4),round(force,3),np.round(self.d.site_xpos[arm['tip']],4),round(math.degrees(self.max_tilt),1),flush=True)
   speed=abs(float(self.d.qvel[self.v[t]]));value=self.value(t)
   good=(self.activated and value<self.s['clock_stroke']*.20) if t=='alarm' else (value<.002 and speed<.01) if t=='drawer' else (value<math.radians(5) and speed<.15 and self.progress_contact>math.radians(4)) if t=='laptop' else (abs(value)<math.radians(3) and speed<.07)
   dwell=dwell+DT if self.phase=='release' and good else 0.
   if dwell>.35:break
  value=self.value(t);success=bool(dwell>.35 and self.hand_contacts>0 and self.bad_contacts==0 and not self.fall and self.max_force<.8)
  result={'task':t,'success':success,'value':value,'duration':float(self.d.time)-self.t0,'contacts':self.hand_contacts,'non_hand_contact_steps':self.bad_contacts,'max_force_n':self.max_force,'fall':self.fall,'max_tilt_deg':math.degrees(self.max_tilt),'profile':asdict(self.profile),'phase':self.phase,'contact_progress':self.progress_contact};self.results[t]=result;self.events.append({**result,'t':float(self.d.time)});return result
 def rest_arms(self,max_seconds=9.):
  self.task=None;self.phase='recover';start=float(self.d.time);arm=self.arm[self.approach_side];next_control=-1.;index=0;tip=self.d.site_xpos[arm['tip']].copy();rot=self.d.xmat[1].reshape(3,3);parking=self.d.qpos[:3]+rot@np.array([.015,.045 if self.approach_side=='left' else -.045,0.]);parking[2]=.195;tip[2]=.195;targets=[tip,parking]
  while self.d.time-start<max_seconds and not self.fall:
   if self.d.time>=next_control:
    target=self.ik(self.approach_side,targets[index],np.array([0.,0.,1.])) if index<2 else arm['rest'];change=target-self.d.ctrl[arm['acts']];change*=min(1.,.014/max(float(np.max(np.abs(change))),1e-8));self.d.ctrl[arm['acts']]+=change;next_control=float(self.d.time)+CONTROL_DT
    if index<2 and np.linalg.norm(self.d.site_xpos[arm['tip']]-targets[index])<.006:index+=1
   self.step(standing=True)
   if index==2 and np.max(np.abs(self.d.qpos[arm['qs']]-arm['rest']))<.03:break
 def episode(self):return {'scenario':self.s,'events':self.events,'results':self.results,'fall':self.fall,'max_tilt_deg':math.degrees(self.max_tilt),'maximum_applied_base_force':self.base_force,'duration':float(self.d.time),'decisions':self.decisions,'trajectory':{'body_names':[mujoco.mj_id2name(self.m,mujoco.mjtObj.mjOBJ_BODY,i) or 'world' for i in range(self.m.nbody)],'frames':self.frames,'sample_hz':25}}

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--task',choices=TASKS+('walk','all'),default='all');p.add_argument('--seed',type=int,default=12000);a=p.parse_args();w=World(a.seed,record=True,start_task=a.task if a.task in TASKS else None)
 if a.task in TASKS:print(w.do_task(a.task),flush=True)
 elif a.task=='walk':print('walk',w.walk_to((-.36,.025,math.pi/2)),w.d.qpos[:3],w.max_tilt,flush=True)
 else:
  for task,goal in ROUTE:
   arrived=w.walk_to(goal);print('ARRIVAL',task,arrived,w.d.qpos[:3],flush=True)
   if not arrived:break
   if task!='transit':
    print('TASK',w.do_task(task),flush=True);w.rest_arms()
 out=ROOT/'artifacts/curriculum';out.mkdir(parents=True,exist_ok=True);(out/('smoke-'+a.task+'.json')).write_text(json.dumps(w.episode(),separators=(',',':')))
