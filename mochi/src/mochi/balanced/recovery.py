"""V11 recovery fork: intended foot support is not a fixture collision.

V8 recovery and its verifier remain unchanged. All other robot/fixture contact
is still counted, including hand/book and foot/riser collision.
"""
import math
from dataclasses import asdict
import mujoco
import numpy as np
from ..curriculum.world import DT
from ..control_v8.recovery import RECOVERIES, observation


def fixture_contact(w):
    peak=0.;count=0
    for i,c in enumerate(w.d.contact):
        a,b=int(c.geom1),int(c.geom2)
        ra=int(w.m.geom_bodyid[a]) in w.robot_bodies
        rb=int(w.m.geom_bodyid[b]) in w.robot_bodies
        if ra==rb:
            continue
        robot,fixture=(a,b) if ra else (b,a)
        name=mujoco.mj_id2name(w.m,mujoco.mjtObj.mjOBJ_BODY,int(w.m.geom_bodyid[robot])) or ''
        if (fixture in w.support_geoms and name in ['left_ankle_roll_link','right_ankle_roll_link']
                and abs(float(c.frame[2]))>.7):
            continue
        force=np.zeros(6);mujoco.mj_contactForce(w.m,w.d,i,force)
        if force[0]>.01:
            count+=1;peak=max(peak,float(force[0]))
    return count,peak


def recover(w,task,profile):
 side=w.approach_side;arm=w.arm[side];w.task=None;w.phase='recover';start=float(w.d.time);q0=w.d.qpos[arm['qs']].copy();prevq=q0.copy();prevt=w.d.site_xpos[arm['tip']].copy();travel=0.;path=0.;contacts=0;peak=0.;next_control=-1.;stable=0.;stage=0;target=arm['rest'];initial=observation(w,task);waypoint=None;cartesian=None
 if profile.waypoint=='parking':
  R=w.d.xmat[1].reshape(3,3);point=w.d.qpos[:3]+R@np.array([.012,.045 if side=='left' else -.045,0]);point[2]=.145;waypoint=w.ik(side,point,np.array([0.,0.,1.]),from_home=True)
 elif profile.waypoint=='clearance' and task=='alarm':
  outward=q0.copy();outward[1]=-1.1 if side=='right' else 1.1;lower=arm['rest'].copy();lower[1]=outward[1];waypoint=[outward,lower]
 elif profile.waypoint=='clearance':
  normal=np.array([0.,0.,1.]) if task in ['alarm','laptop'] else np.array([0.,-1.,0.]) if task=='drawer' else prevt-w.d.xpos[w.id('body','globe')];normal=normal/max(np.linalg.norm(normal),1e-9);cartesian=[prevt+normal*(.04 if task=='alarm' else .014)];waypoint=None
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
