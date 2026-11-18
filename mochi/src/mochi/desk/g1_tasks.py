"""Contact previews with native seven-DOF G1 arms and scaled link meshes."""
from dataclasses import asdict
import argparse,json,math,time
from pathlib import Path
import mujoco,numpy as np
from scipy.optimize import least_squares
from .tasks import scenario,Controller,DT,CONTROL_DT,HORIZON,TASKS
from .g1_model import ROOT,ARMS,METADATA,model_xml,PAD_RADIUS,station

def object_angle(s,d,q):return math.pi/2-float(d.qpos[q]) if s['task']=='laptop' else float(d.qpos[q])
def quaternion(rot):
    q=np.zeros(4);mujoco.mju_mat2Quat(q,rot.reshape(-1));return q
def rotation_error(target,current):
    q=quaternion(target@current.T)
    if q[0]<0:q=-q
    norm=np.linalg.norm(q[1:]);return q[1:]/max(norm,1e-9)*(2*math.atan2(norm,q[0]))
def target(s,a,stroke,depth,side,approach=False):
    if s['task']=='laptop':
        n=np.array([0,-math.sin(a),-math.cos(a)]);up=np.array([0,-math.cos(a),math.sin(a)])
        p=np.array(s['hinge_position'])+np.array([.138,-.135*math.cos(a),.135*math.sin(a)]);radius=PAD_RADIUS+.0035
    else:
        n=np.array([math.cos(stroke),math.sin(stroke),0]);up=np.array([0.,0.,1.]);p=np.array(s['globe_position']);radius=s['globe_radius']+PAD_RADIUS
    position=p+n*(radius+(.010 if approach else -depth));x=-n;y=np.cross(up,x);y/=np.linalg.norm(y);z=np.cross(x,y)
    return position,np.column_stack([x,y,z])

def rollout(task,seed=9000,controller=Controller(.35,.025,.0007),record=False,free_base=False,base_xy=None):
    started=time.perf_counter();controller.validate();s=scenario(task,seed);s['hinge_damping']=.006 if task=='laptop' else .0005;s['robot_position'],s['robot_yaw']=station(task,free_base,base_xy)
    if base_xy is not None:s['free_base_xy']=list(base_xy)
    m=mujoco.MjModel.from_xml_string(model_xml(s,free_base=free_base));d=mujoco.MjData(m);viz=mujoco.MjData(m) if record else None;side='left' if task=='laptop' else 'right'
    jids=[mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,n) for n in ARMS[side]];qids=np.array([m.jnt_qposadr[i] for i in jids]);vids=np.array([m.jnt_dofadr[i] for i in jids]);aids=np.array([mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_ACTUATOR,n) for n in ARMS[side]])
    all_dofs=[int(m.jnt_dofadr[mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,n)]) for n in sum(ARMS.values(),[])];limits=m.jnt_range[jids]
    oj=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,'object-angle');oq=int(m.jnt_qposadr[oj]);ov=int(m.jnt_dofadr[oj]);d.qpos[oq]=math.pi/2-s['initial_angle'] if task=='laptop' else s['initial_angle']
    tip=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_SITE,side+'-push-tip');og=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,'screen-contact' if task=='laptop' else 'globe-contact');hand=set()
    for g in range(m.ngeom):
        meshname=mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_MESH,int(m.geom_dataid[g])) if m.geom_type[g]==mujoco.mjtGeom.mjGEOM_MESH else ''
        if side+'_hand_' in (meshname or '') or mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_GEOM,g)==side+'-push-pad':hand.add(g)
    def is_hand(c):return og in [int(c.geom1),int(c.geom2)] and bool(hand.intersection([int(c.geom1),int(c.geom2)]))
    jp=np.zeros((3,m.nv));jr=np.zeros((3,m.nv));stroke=math.pi-.25
    def solve_position(position,cap=.12):
        # Differential position IK. Contact geometry, not hand orientation,
        # supplies the task impulse. Native joint ranges remain enforced.
        mujoco.mj_jacSite(m,d,jp,jr,tip);J=jp[:,vids];ep=position-d.site_xpos[tip]
        dq=J.T@np.linalg.solve(J@J.T+np.eye(3)*8e-8,ep)
        return np.clip(d.qpos[qids]+np.clip(dq,-cap,cap),limits[:,0]+.001,limits[:,1]-.001)
    position,orientation=target(s,s['initial_angle'],stroke,controller.depth,side,True)
    def residual(q):
        d.qpos[qids]=q;mujoco.mj_forward(m,d)
        return np.r_[d.site_xpos[tip]-position,.001*(d.site_xmat[tip].reshape(3,3)[:,0]-orientation[:,0])]
    best=None;rng=np.random.default_rng(1729)
    for attempt in range(24):
        x0=np.zeros(7) if attempt==0 else rng.normal(0,1.,7);x0=np.clip(x0,limits[:,0]+.002,limits[:,1]-.002)
        opt=least_squares(residual,x0,bounds=(limits[:,0]+.001,limits[:,1]-.001),max_nfev=180,ftol=1e-9,gtol=1e-10,xtol=1e-9)
        residual(opt.x);pe=float(np.linalg.norm(position-d.site_xpos[tip]));re=math.acos(float(np.clip(orientation[:,0]@d.site_xmat[tip].reshape(3,3)[:,0],-1,1)))
        collision=sum(max(0,-float(c.dist)) for c in d.contact)
        score=pe+.0002*re+10*collision+.000001*float(opt.x@opt.x)
        if best is None or score<best[0]:best=(score,opt.x.copy())
        if pe<.0002 and re<.03 and collision<.000001:break
    d.qpos[qids]=best[1]
    mujoco.mj_forward(m,d);d.ctrl[aids]=d.qpos[qids];initial_error=float(np.linalg.norm(position-d.site_xpos[tip]));initial_rotation=math.acos(float(np.clip(orientation[:,0]@d.site_xmat[tip].reshape(3,3)[:,0],-1,1)))
    initial_pairs=[(mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,int(m.geom_bodyid[c.geom1])),mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,int(m.geom_bodyid[c.geom2])),float(c.dist)) for c in d.contact if c.dist<-.00001]
    phase='approach';hold_time=None;hold_pose=None;contacts=0;other=0;dwell=0.;frames=[];pairs={};invalid=initial_error>.004;effort=0.;max_speed=0.
    pelvis=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,'pelvis');desk=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,'desk');start_position=d.xpos[pelvis].copy();max_tilt=0.;min_height=float(start_position[2]);max_drift=0.;body_ground_steps=0;foot_steps=0;base_force_max=0.;feet=set()
    free_dof=int(m.jnt_dofadr[mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,'free-base')]) if free_base else None
    def support_feet():
        feet=set();bad=False
        for c in d.contact:
            if desk not in [int(c.geom1),int(c.geom2)]:continue
            other=int(c.geom2) if int(c.geom1)==desk else int(c.geom1);name=mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,int(m.geom_bodyid[other])) or ''
            if 'ankle_roll_link' in name:feet.add(name)
            elif name not in ['laptop-base','globe-base']:bad=True
        return feet,bad
    def capture(t):
        if not record:return
        viz.qpos[:]=d.qpos;viz.qvel[:]=d.qvel;mujoco.mj_forward(m,viz)
        frames.append({'t':round(t,4),'positions':viz.xpos.tolist(),'quaternions':viz.xquat.tolist(),'angle':object_angle(s,d,oq),'angular_velocity':float(d.qvel[ov]),'phase':phase,'hand_contact':any(is_hand(c) for c in d.contact),'base_tilt_degrees':math.degrees(math.acos(float(np.clip(viz.xmat[pelvis].reshape(3,3)[2,2],-1,1)))),'support_feet':sorted(support_feet()[0])})
    capture(0.)
    for step in range(int(HORIZON/DT)):
        t=step*DT;a=object_angle(s,d,oq);error=s['target_angle']-a
        if step%10==0:
            if phase=='approach' and t>=.6:phase='engage'
            if phase=='engage' and contacts>=5:phase='push'
            if phase=='push' and error<=controller.brake:phase='hold';hold_time=t;hold_pose=(d.site_xpos[tip].copy(),d.site_xmat[tip].reshape(3,3).copy())
            if phase=='hold' and t-hold_time>.45:phase='retract'
            if task=='globe' and phase=='push':stroke=min(math.pi+.48,stroke+controller.speed*CONTROL_DT)
            p,R=target(s,a,stroke,controller.depth,side,phase in ['approach','retract'] or (phase=='hold' and task=='laptop'))
            if phase=='hold' and task=='globe':p,R=hold_pose
            if phase=='retract':p=p+np.array([0,0,.012])
            delta=p-d.site_xpos[tip];limit=(.145 if task=='laptop' else s['globe_radius'])*controller.speed*CONTROL_DT
            if phase in ['approach','retract']:limit=.0012
            length=np.linalg.norm(delta)
            if length>limit:delta*=limit/length
            d.ctrl[aids]=solve_position(d.site_xpos[tip]+delta,.10)
        d.qfrc_applied[all_dofs]=d.qfrc_bias[all_dofs];mujoco.mj_step(m,d)
        if free_base:
            tilt=math.acos(float(np.clip(d.xmat[pelvis].reshape(3,3)[2,2],-1,1)));max_tilt=max(max_tilt,tilt);min_height=min(min_height,float(d.xpos[pelvis,2]));max_drift=max(max_drift,float(np.linalg.norm(d.xpos[pelvis,:2]-start_position[:2])));feet,bad=support_feet();body_ground_steps+=int(bad);foot_steps+=int(len(feet)==2);base_force_max=max(base_force_max,float(np.max(np.abs(d.qfrc_applied[free_dof:free_dof+6]))))
            invalid|=tilt>math.radians(30) or float(d.xpos[pelvis,2])<start_position[2]-.025 or bad
        contacts+=int(any(is_hand(c) for c in d.contact));other+=int(any(og in [int(c.geom1),int(c.geom2)] and not is_hand(c) for c in d.contact))
        for c in d.contact:
            if og in [int(c.geom1),int(c.geom2)]:
                g=int(c.geom2) if int(c.geom1)==og else int(c.geom1);name=mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,int(m.geom_bodyid[g]));pairs[name]=pairs.get(name,0)+1
        a=object_angle(s,d,oq);err=abs(s['target_angle']-a);speed=abs(float(d.qvel[ov]));max_speed=max(max_speed,speed);invalid|=not np.isfinite(d.qpos).all() or abs(a)>4
        good=err<=s['target_tolerance'] and speed<=.07 and not invalid;dwell=dwell+DT if good else 0.;effort+=float(np.sum(d.actuator_force**2))*DT
        if record and (step+1)%20==0:capture(float(d.time))
    result={'initial_collision_pairs':initial_pairs,'final_q':d.qpos[qids].tolist(),'final_ctrl':d.ctrl[aids].tolist(),'task':task,'scenario':s,'controller':asdict(controller),'success':bool(dwell>=.4 and contacts>0 and other==0 and not invalid),'error_degrees':math.degrees(err),'final_angle':a,'contact_steps':contacts,'other_object_contact_steps':other,'contact_pairs':pairs,'dwell_seconds':dwell,'invalid':bool(invalid),'initial_ik_error_m':initial_error,'initial_ik_rotation_error_rad':initial_rotation,'control_effort':effort,'max_angular_speed':max_speed,'duration_seconds':time.perf_counter()-started,'source':'Local MuJoCo G1 contact preview; no model post-training','robot':{'name':'Unitree G1 miniature supported model','height_m':METADATA['height_m'],'scale':METADATA['scale'],'source_revision':METADATA['source']['revision'],'active_arm':side,'active_arm_dofs':7,'fingers':'fixed stand pose','scope':METADATA['scope']}}
    if free_base:
        result['success']=bool(result['success'] and len(feet)==2 and base_force_max==0)
        result['robot'].update(name='Unitree G1 miniature free-base model',base='free',base_dofs=6,legs='rigid stand configuration',scope='Free six-DOF pelvis supported by foot contact only. Native arm feedback and joint gravity compensation; legs, waist and fingers held rigid. No external support force or learned balance controller.')
        result['balance']={'max_tilt_degrees':math.degrees(max_tilt),'minimum_pelvis_height_m':min_height,'maximum_horizontal_drift_m':max_drift,'non_foot_ground_contact_steps':body_ground_steps,'both_feet_contact_fraction':foot_steps/(HORIZON/DT),'terminal_support_feet':sorted(feet),'maximum_applied_base_generalized_force':base_force_max,'fall':bool(max_tilt>math.radians(30) or min_height<start_position[2]-.025 or body_ground_steps>0)}
    else:result['robot']['base']='fixed'
    if record:result['trajectory']={'body_names':[mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,i) or 'world' for i in range(m.nbody)],'frames':frames,'sample_hz':25}
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--task',choices=TASKS+('both',),default='both');parser.add_argument('--seed',type=int,default=9000);parser.add_argument('--out',default=str(ROOT/'artifacts/realism-v4'));args=parser.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    for task in TASKS if args.task=='both' else [args.task]:
        r=rollout(task,args.seed,record=True);(out/(task+'.json')).write_text(json.dumps(r));print(task,{k:r[k] for k in ['success','error_degrees','contact_steps','other_object_contact_steps','initial_ik_error_m','initial_ik_rotation_error_rad','duration_seconds','contact_pairs']},flush=True)
