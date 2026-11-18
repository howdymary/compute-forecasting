"""Read-only route diagnostics and 25 Hz conservative visual-clearance audit."""
import math
import mujoco,numpy as np
from ..curriculum.world import World,TASKS,wrap
from ..curriculum.motion_metrics import episode_motion
from .follower import projection
from .geometry import ConfigurationSpace,quat_product

def metrics(row,route):
 ep=row['episode'];motion=episode_motion(ep);frames=ep['trajectory']['frames'];distances=[]
 for f in frames:
  if f['phase']!='walk':continue
  t=f['t'];index=sum(t>a['t'] for a in row['arrivals']);leg=route['legs'][min(index,len(route['legs'])-1)];distances.append(min(projection(f['positions'][1][:2],s['from'],s['to'])[2] for s in leg['segments']))
 complete=bool(all(ep['results'].get(t,{}).get('success',False) for t in TASKS) and not ep['fall'] and ep['final_object_states']['drawer']<.002 and ep['final_object_states']['laptop']<math.radians(5) and abs(ep['final_object_states']['globe'])<math.radians(3) and all(abs(ep['final_object_speeds'][t])<v for t,v in [('drawer',.01),('laptop',.15),('globe',.07)]))
 navigation=len(row['arrivals'])==len(route['legs']) and not ep['fall']
 task_arrivals=[a for a in row['arrivals'] if a['station']!='transit']
 return {**motion,'navigation_success':navigation,'full_sequence_success':complete,'task_success':{t:ep['results'].get(t,{}).get('success',False) for t in TASKS},'arrivals':len(row['arrivals']),'required_arrivals':len(route['legs']),'planned_path_m':route['length_m'],'excess_path_m_successful_only':motion['walking_path_m']-route['length_m'] if navigation else None,'cross_track_rms_mm':float(np.sqrt(np.mean(np.square(distances)))*1000) if distances else None,'cross_track_max_mm':max(distances)*1000 if distances else None,'arrival_position_mean_mm':float(np.mean([a['position_error_mm'] for a in task_arrivals])) if task_arrivals else None,'arrival_heading_mean_degrees':float(np.mean([a['heading_error_degrees'] for a in task_arrivals])) if task_arrivals else None,'fall':ep['fall'],'episode_duration_s':ep['duration'],'maximum_applied_base_force':ep['maximum_applied_base_force'],'efficiency_caveat':'Only compare excess distance and whole-route time for completed matched routes. Pelvis path includes native gait sway; this is not a footstep distance. Arrival means cover task stations, excluding the old extra transit stop.'}

def replay_clearance(row):
 """Reconstruct generalized coordinates from recorded body poses, then verify
 FK agreement before using those coordinates for a detached geometry audit.
 No dynamics state is changed in the source rollout.
 """
 ep=row['episode'];space=ConfigurationSpace(ep['scenario']['seed'],clearance=.0001,walking_envelope=False);m,d=space.m,space.d;names=ep['trajectory']['body_names'];indices={n:i for i,n in enumerate(names)};max_error=0.;overlap=[];edge=[];n=0
 for f in ep['trajectory']['frames']:
  if f['phase']!='walk':continue
  d.qpos[:]=space.initial;d.qpos[:3]=f['positions'][1];d.qpos[3:7]=f['quaternions'][1]
  for j in range(1,m.njnt):
   typ=m.jnt_type[j];body=int(m.jnt_bodyid[j]);parent=int(m.body_parentid[body]);qb=np.array(f['quaternions'][body]);qp=np.array(f['quaternions'][parent]);relative=quat_product(qp*np.array([1,-1,-1,-1]),qb);rotation=quat_product(m.body_quat[body]*np.array([1,-1,-1,-1]),relative)
   if typ==mujoco.mjtJoint.mjJNT_HINGE:d.qpos[m.jnt_qposadr[j]]=wrap(2*math.atan2(float(np.dot(rotation[1:],m.jnt_axis[j])),float(rotation[0])))
   elif typ==mujoco.mjtJoint.mjJNT_SLIDE:
    jointname=mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_JOINT,j);task='alarm' if jointname=='alarm-slider' else 'drawer';d.qpos[m.jnt_qposadr[j]]=f['objects'][task]
  mujoco.mj_forward(m,d);error=float(np.max(np.abs(d.xpos[:len(names)]-np.asarray(f['positions']))));max_error=max(max_error,error)
  if error>2e-5:raise ValueError('Body-pose reconstruction error exceeds 20 micrometres')
  n+=1
  for g in space.foot_geoms:
   lo,hi=space.bounds(g)
   if lo[0]<-.6 or hi[0]>.6 or lo[1]<-.4 or hi[1]>.4:edge.append(f['t']);break
  for c in d.contact:
   a,b=int(c.geom1),int(c.geom2)
   if space.desk in [a,b] or (a in space.robot_geoms)==(b in space.robot_geoms) or c.dist>=-.0003:continue
   other=b if a in space.robot_geoms else a;overlap.append({'t':f['t'],'depth_mm':-float(c.dist)*1000,'fixture':mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_GEOM,other)});break
 return {'walking_frames':n,'sample_hz':25,'maximum_reconstruction_error_m':max_error,'visual_envelope_overlap_frames':len(overlap),'foot_outside_desk_frames':len(edge),'first_overlaps':overlap[:12],'first_edge_times':edge[:12],'scope':'Sampled replay audit, not continuous collision certification. Visual GLB parts use conservative boxes; robot meshes use convex contact hulls.'}
