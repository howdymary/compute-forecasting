"""Bounded active-arm recovery choices, physically evaluated before training."""
import copy,math
from dataclasses import dataclass,asdict
import mujoco,numpy as np
from ..curriculum.world import DT
from .manipulation import ControlWorld

@dataclass(frozen=True)
class Recovery:
 code:str;waypoint:str;slew:float;pause:float
RECOVERIES=[Recovery('R0','direct',.020,0),Recovery('R1','clearance',.04,0),Recovery('R2','parking',.014,0),Recovery('R3','direct',.018,.35)]
def snapshot(w):
 kind=mujoco.mjtState.mjSTATE_INTEGRATION;state=np.empty(mujoco.mj_stateSize(w.m,kind));mujoco.mj_getState(w.m,w.d,state,kind)
 return {'seed':w.s['seed'],'state':state.tolist(),'side':w.approach_side,'task':w.task,'results':copy.deepcopy(w.results),'activated':w.activated,'standing_mode':w.standing_mode,'model':{k:getattr(w.m,k).tolist() for k in ['actuator_gainprm','actuator_biasprm','actuator_biastype','actuator_ctrllimited','actuator_forcelimited','actuator_forcerange']}}
def restore(data,record=False):
 w=ControlWorld(data['seed'],record);w.standing_mode=data['standing_mode']
 for k,v in data['model'].items():getattr(w.m,k)[:]=v
 mujoco.mj_setState(w.m,w.d,np.array(data['state']),mujoco.mjtState.mjSTATE_INTEGRATION);w.approach_side=data['side'];w.results=copy.deepcopy(data['results']);w.activated=data['activated'];w.task=data['task'];mujoco.mj_forward(w.m,w.d);w.frames=[];w.capture();return w
def observation(w,task):
 side=w.approach_side;arm=w.arm[side];tip=w.d.site_xpos[arm['tip']];root=w.d.qpos[:3];R=w.d.xmat[1].reshape(3,3);q=w.d.qpos[arm['qs']]
 return {'domain':'recovery','task':task,'active_arm':side,'joint_error_degrees':np.degrees(q-arm['rest']).round(1).tolist(),'joint_speed_degrees_s':np.degrees(w.d.qvel[arm['vs']]).round(1).tolist(),'hand_body_offset_mm':((R.T@(tip-root))*1000).round(1).tolist(),'body_tilt_degrees':round(math.degrees(math.acos(float(np.clip(w.d.xmat[1,8],-1,1)))),1),'hand_contact':w.contacts(task)[0],'maximum_joint_error_degrees':round(float(np.max(np.abs(np.degrees(q-arm['rest'])))),1)}
def fixture_contact(w):
 desk=w.id('geom','desk');peak=0.;count=0
 for i,c in enumerate(w.d.contact):
  a,b=int(c.geom1),int(c.geom2)
  if desk in [a,b] or (int(w.m.geom_bodyid[a]) in w.robot_bodies)==(int(w.m.geom_bodyid[b]) in w.robot_bodies):continue
  f=np.zeros(6);mujoco.mj_contactForce(w.m,w.d,i,f)
  if f[0]>.01:count+=1;peak=max(peak,float(f[0]))
 return count,peak
def recover(w,task,profile):
 side=w.approach_side;arm=w.arm[side];w.task=None;w.phase='recover';start=float(w.d.time);q0=w.d.qpos[arm['qs']].copy();prevq=q0.copy();prevt=w.d.site_xpos[arm['tip']].copy();travel=0.;path=0.;contacts=0;peak=0.;next_control=-1.;stable=0.;stage=0;target=arm['rest'];initial=observation(w,task);waypoint=None;cartesian=None
 if profile.waypoint=='parking':
  R=w.d.xmat[1].reshape(3,3);point=w.d.qpos[:3]+R@np.array([.012,.045 if side=='left' else -.045,0]);point[2]=.145;waypoint=w.ik(side,point,np.array([0.,0.,1.]),from_home=True)
 elif profile.waypoint=='clearance' and task=='alarm':
  outward=q0.copy();outward[1]=-1.1 if side=='right' else 1.1;lower=arm['rest'].copy();lower[1]=outward[1];waypoint=[outward,lower]
 elif profile.waypoint=='clearance':
  normal=np.array([0.,0.,1.]) if task in ['alarm','laptop'] else np.array([0.,-1.,0.]) if task=='drawer' else prevt-np.array([.47,.22,.123]);normal=normal/max(np.linalg.norm(normal),1e-9);cartesian=[prevt+normal*(.04 if task=='alarm' else .014)];waypoint=None
 ready=lambda:float(np.max(np.abs(w.d.qpos[arm['qs']]-arm['rest'])))<.035 and float(np.max(np.abs(w.d.qvel[arm['vs']])))<.2
 while w.d.time-start<10 and not w.fall:
  elapsed=float(w.d.time)-start
  if ready() and math.degrees(math.acos(float(np.clip(w.d.xmat[1,8],-1,1))))<5:
   stable+=DT
   if stable>.12:break
  else:stable=0.
  if w.d.time>=next_control:
   if elapsed>=profile.pause:
    if cartesian is not None and stage<len(cartesian):
     delta=cartesian[stage]-w.d.site_xpos[arm['tip']]
     if np.linalg.norm(delta)<.005:stage+=1
     delta*=min(1.,.0012/max(float(np.linalg.norm(delta)),1e-9));J=np.zeros((3,w.m.nv));mujoco.mj_jacSite(w.m,w.d,J,None,arm['tip']);J=J[:,arm['vs']];dq=J.T@np.linalg.solve(J@J.T+np.eye(3)*8e-8,delta);target=np.clip(w.d.qpos[arm['qs']]+dq,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
    points=waypoint if isinstance(waypoint,list) else [waypoint] if waypoint is not None else [];target=target if cartesian is not None and stage<len(cartesian) else points[stage] if stage<len(points) else arm['rest'];change=target-w.d.ctrl[arm['acts']];change*=min(1.,profile.slew/max(float(np.max(np.abs(change))),1e-8));w.d.ctrl[arm['acts']]=np.clip(w.d.ctrl[arm['acts']]+change,arm['limits'][:,0]+.001,arm['limits'][:,1]-.001)
    if stage<len(points) and np.max(np.abs(w.d.qpos[arm['qs']]-points[stage]))<.08:stage+=1
   next_control=float(w.d.time)+.02
  w.step(standing=True);nowq=w.d.qpos[arm['qs']].copy();nowt=w.d.site_xpos[arm['tip']].copy();travel+=float(np.sum(np.abs(nowq-prevq)));path+=float(np.linalg.norm(nowt-prevt));prevq=nowq;prevt=nowt;n,force=fixture_contact(w);contacts+=int(n>0);peak=max(peak,force)
  if peak>.8:break
 result={'task':task,'action':profile.code,'success':bool(stable>.12 and not w.fall and contacts==0),'duration_s':float(w.d.time)-start,'arm_joint_travel_rad':travel,'hand_path_m':path,'fixture_contact_steps':contacts,'peak_fixture_force_n':peak,'end_max_joint_error_rad':float(np.max(np.abs(w.d.qpos[arm['qs']]-arm['rest']))),'end_max_joint_speed_rad_s':float(np.max(np.abs(w.d.qvel[arm['vs']]))),'fall':w.fall,'observation':initial,'profile':asdict(profile)};w.recoveries.append(result);w.events.append({'task':task,'phase':'recover','t':float(w.d.time),**result});return result
