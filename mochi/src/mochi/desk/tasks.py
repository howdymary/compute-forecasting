"""Two native-scale, supported humanoid contact tasks. No learned weights yet.

Object joint states are initialized at reset; only arm actuators are controlled
during an episode. The screen/globe are moved by MuJoCo contact.
"""
from dataclasses import dataclass,asdict
from pathlib import Path
import argparse,hashlib,json,math
import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
RIG=json.loads((ROOT/'assets/robot/mini-humanoid.json').read_text())
DT=.002;CONTROL_DT=.02;HORIZON=7.;NA=4;TASKS=('laptop','globe')

@dataclass(frozen=True)
class Controller:
    speed:float=.45  # angular rate cap, rad/s; converted to Cartesian tip speed
    brake:float=.025  # radians before target
    depth:float=.0012
    def validate(self):
        assert .08<=self.speed<=2 and 0<=self.brake<=.15 and .0002<=self.depth<=.0025
        return self

def scenario(task,seed):
    assert task in TASKS
    rng=np.random.default_rng(seed)
    return {'task':task,'seed':seed,'initial_angle':float(math.radians(rng.uniform(66,72))) if task=='laptop' else float(math.radians(rng.uniform(-28,-20))),
      'target_angle':math.pi/2 if task=='laptop' else 0.,'mass':float(rng.uniform(.14,.18) if task=='laptop' else rng.uniform(.035,.05)),
      'hinge_friction':float(rng.uniform(.052,.065) if task=='laptop' else rng.uniform(.000025,.000045)),
      'contact_friction':float(rng.uniform(.55,.85)),
      'robot_position':[.075,.040,.112] if task=='laptop' else [.075,-.005,.112],
      'robot_yaw':-math.pi/2 if task=='laptop' else math.pi/2,
      'hinge_position':[-.12,.070,.014],'globe_position':[.20,.040,.123],'globe_radius':.058,
      'target_tolerance':math.radians(3),'dwell_seconds':.4}

def xml(s):
    task=s['task'];px,py,pz=s['robot_position'];r=s['robot_yaw']
    legs=''
    for side,sign in [('left',-1),('right',1)]:
        legs+=f'''<body name="{side}-hip" pos="{sign*.018} 0 0"><geom type="capsule" fromto="0 0 0 0 0 -.052" size=".007"/>
          <body name="{side}-knee" pos="0 0 -.052"><geom type="capsule" fromto="0 0 0 0 0 -.048" size=".006"/>
          <body name="{side}-ankle" pos="0 0 -.048"><geom type="box" pos="0 -.008 -.006" size=".012 .020 .006"/></body></body></body>'''
    # Root is explicitly fixed. This experiment makes no balance/walking claim.
    arm='''<body name="right-shoulder" pos=".033 0 .047">
       <joint name="arm-yaw" axis="0 0 1" range="-3 3"/><joint name="arm-pitch" axis="1 0 0" range="-1.57 1.57"/><joint name="arm-roll" axis="0 1 0" range="-3.14 3.14"/>
       <geom name="upper-arm" type="capsule" fromto="0 0 0 0 0 -.040" size=".0058" mass=".020"/>
       <body name="right-elbow" pos="0 0 -.040"><joint name="arm-elbow" axis="1 0 0" range=".08 2.9"/>
         <geom name="forearm" type="capsule" fromto="0 0 0 0 0 -.037" size=".0048" mass=".015"/>
         <body name="right-wrist" pos="0 0 -.037"><geom name="palm-contact" type="box" pos="0 0 -.005" size=".0055 .004 .005" mass=".006"/>
           <geom name="hand-contact" type="sphere" pos="0 0 -.014" size=".0045" mass=".003" friction="1 .005 .0001"/><site name="tip" pos="0 0 -.014" size=".001"/>
         </body></body></body>'''
    laptop_joint=f'<joint name="object-angle" axis="1 0 0" range="-.70 1.35" damping=".006" frictionloss="{s["hinge_friction"]}"/>' if task=='laptop' else ''
    laptop_turn='' if task=='laptop' else f'euler="{math.radians(20)} 0 0"'
    globe_joint=f'<joint name="object-angle" axis="0 0 1" limited="false" damping=".00008" frictionloss="{s["hinge_friction"]}"/>' if task=='globe' else ''
    laptopmass=s['mass'] if task=='laptop' else .16;globemass=s['mass'] if task=='globe' else .042
    return f'''<mujoco model="Mochi {task} desk task"><compiler angle="radian"/><option timestep="{DT}" integrator="implicitfast" iterations="90"/>
    <default><joint damping=".025" armature=".00004"/><geom friction=".7 .005 .0001" solref=".006 1" solimp=".95 .99 .001" rgba=".8 .82 .76 1"/></default>
    <worldbody><geom name="desk" type="box" pos="0 0 -.020" size=".60 .40 .020"/>
      <body name="pelvis" pos="{px} {py} {pz}" euler="0 0 {r}"><geom type="box" size=".021 .0135 .011"/>{legs}
       <body name="waist" pos="0 0 .014"><geom type="box" pos="0 0 .028" size=".0235 .014 .028"/>
        <body name="head" pos="0 0 .078" euler="0 0 {-math.pi/2 if task=='globe' else 0}"><geom type="box" size=".0175 .015 .017"/></body>
        <body name="left-shoulder" pos="-.033 0 .047"><geom type="capsule" fromto="0 0 0 0 0 -.040" size=".0058"/>
          <body name="left-elbow" pos="0 0 -.040"><geom type="capsule" fromto="0 0 0 0 0 -.037" size=".0048"/>
           <body name="left-wrist" pos="0 0 -.037"><geom type="box" pos="0 0 -.007" size=".0055 .004 .007"/></body></body></body>
        {arm}</body></body>
      <body name="laptop-base" pos="-.12 -.024 .007"><geom type="box" size=".145 .0975 .007"/></body>
      <body name="laptop-screen" pos="-.12 .070 .014" {laptop_turn}>{laptop_joint}
        <geom name="screen-contact" type="box" pos="0 0 .0925" size=".145 .0035 .0875" mass="{laptopmass}" friction="{s['contact_friction']} .005 .0001"/>
      </body>
      <body name="globe-base" pos=".20 .040 0"><geom type="cylinder" pos="0 0 .006" size=".039 .006"/><geom type="cylinder" pos="0 0 .035" size=".004 .029"/></body>
      <body name="globe" pos=".20 .040 .123">{globe_joint}<geom name="globe-contact" type="sphere" size=".058" mass="{globemass}" friction="{s['contact_friction']} .005 .0001"/></body>
    </worldbody><actuator>
      <position joint="arm-yaw" kp="8" kv=".055" ctrlrange="-3 3" forcerange="-.12 .12"/>
      <position joint="arm-pitch" kp="8" kv=".055" ctrlrange="-1.57 1.57" forcerange="-.12 .12"/>
      <position joint="arm-roll" kp="8" kv=".055" ctrlrange="-3.14 3.14" forcerange="-.12 .12"/>
      <position joint="arm-elbow" kp="6" kv=".045" ctrlrange=".08 2.9" forcerange="-.10 .10"/>
    </actuator></mujoco>'''

def angle(s,d,qi):return math.pi/2-float(d.qpos[qi]) if s['task']=='laptop' else float(d.qpos[qi])
def contact_target(s,a,stroke,depth,approach=False):
    clearance=.012 if approach else -depth
    if s['task']=='laptop':
        n=np.array([0,-math.sin(a),-math.cos(a)])
        p=np.array(s['hinge_position'])+np.array([.138,-.145*math.cos(a),.145*math.sin(a)])
        return p+n*(.0045+.0035+clearance)
    n=np.array([math.cos(stroke),math.sin(stroke),0.])
    return np.array(s['globe_position'])+n*(s['globe_radius']+.0045+clearance)

def inverse_kinematics(s,shoulder,target):
    """Four actuated DOFs choose an elbow plane as well as reaching the tip.

    Keeping the laptop elbow in front of the panel avoids reaching through it.
    Upper arm=40 mm, forearm+hand=51 mm in both the visual and physical rig.
    """
    L1=RIG['upper_arm'];L2=RIG['forearm']+RIG['hand_length'];delta=target-shoulder
    distance=float(np.linalg.norm(delta));u=delta/max(distance,1e-8);distance=float(np.clip(distance,abs(L2-L1)+.0001,L1+L2-.0001))
    preferred=np.array([0.,-1.,0.]) if s['task']=='laptop' else np.array([0.,0.,1.])
    bend=preferred-u*float(preferred@u);bend/=max(np.linalg.norm(bend),1e-8)
    along=(L1*L1-L2*L2+distance*distance)/(2*distance);height=math.sqrt(max(0,L1*L1-along*along))
    elbow=shoulder+u*along+bend*height;tip=shoulder+u*distance
    upper=(elbow-shoulder)/L1;fore=(tip-elbow)/L2;x=np.cross(upper,fore);x/=max(np.linalg.norm(x),1e-8);z=-upper;y=np.cross(z,x)
    world=np.column_stack([x,y,z]);yaw=s['robot_yaw'];root=np.array([[math.cos(yaw),-math.sin(yaw),0],[math.sin(yaw),math.cos(yaw),0],[0,0,1]])
    rot=root.T@world
    pitch=math.asin(float(np.clip(rot[2,1],-1,1)));syaw=math.atan2(-rot[0,1],rot[1,1]);roll=math.atan2(-rot[2,0],rot[2,2]);elbow_angle=math.acos(float(np.clip(upper@fore,-1,1)))
    return np.array([syaw,pitch,roll,elbow_angle])

def rollout(task,seed=8000,controller=Controller(),record=False):
    controller.validate();s=scenario(task,seed);m=mujoco.MjModel.from_xml_string(xml(s));d=mujoco.MjData(m);viz=mujoco.MjData(m) if record else None
    jid=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,'object-angle');qi=int(m.jnt_qposadr[jid]);vi=int(m.jnt_dofadr[jid]);tip=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_SITE,'tip')
    pad=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,'hand-contact');objectgeom=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,'screen-contact' if task=='laptop' else 'globe-contact')
    hand_geoms={pad,mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,'palm-contact')}
    def hand_contact(c):return objectgeom in [int(c.geom1),int(c.geom2)] and bool(hand_geoms.intersection([int(c.geom1),int(c.geom2)]))
    d.qpos[qi]=math.pi/2-s['initial_angle'] if task=='laptop' else s['initial_angle'];stroke=math.pi-.25
    mujoco.mj_forward(m,d);initial_target=contact_target(s,s['initial_angle'],stroke,controller.depth,True)
    shoulder=d.xpos[mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,'right-shoulder')].copy()
    d.qpos[:NA]=inverse_kinematics(s,shoulder,initial_target);d.ctrl[:]=d.qpos[:NA];mujoco.mj_forward(m,d)
    initial_error=float(np.linalg.norm(d.site_xpos[tip]-initial_target));phase='approach';hold_at=None;hold_tip=None;dwell=0;contact_steps=0;other_contacts=0;frames=[];invalid=False;max_speed=0.;effort=0.;stopped_angle=None;contact_pairs={}
    for step in range(int(HORIZON/DT)):
        t=step*DT;a=angle(s,d,qi);error=s['target_angle']-a;omega=(-1 if task=='laptop' else 1)*float(d.qvel[vi]);max_speed=max(max_speed,abs(omega))
        if step%10==0:
            if phase=='approach' and t>=.7:phase='engage'
            if phase=='engage' and contact_steps>=5:phase='push'
            if phase=='push' and error<=controller.brake:phase='hold';hold_at=t;stopped_angle=a;hold_tip=d.site_xpos[tip].copy()
            if phase=='hold' and t-hold_at>.45:phase='retract'
            if task=='globe' and phase=='push':stroke=min(math.pi+.48,stroke+controller.speed*CONTROL_DT)
            desired=contact_target(s,a,stroke,controller.depth,phase in ['approach','retract'])
            if phase=='hold' and task=='globe':desired=hold_tip.copy()
            if phase=='hold' and task=='laptop':desired=contact_target(s,a,stroke,controller.depth,True)
            if phase=='retract':desired[2]+=.016
            delta=desired-d.site_xpos[tip];limit=(.145 if task=='laptop' else s['globe_radius'])*controller.speed*CONTROL_DT
            if phase=='approach':limit=.0012
            if phase=='retract':limit=.0015
            norm=np.linalg.norm(delta)
            if norm>limit:delta*=limit/norm
            targets=inverse_kinematics(s,shoulder,d.site_xpos[tip]+delta)
            d.ctrl[:]=np.clip(d.qpos[:NA]+np.clip(targets-d.qpos[:NA],-.12,.12),m.jnt_range[:NA,0],m.jnt_range[:NA,1])
        d.qfrc_applied[:NA]=d.qfrc_bias[:NA];mujoco.mj_step(m,d)
        contact_steps+=int(any(hand_contact(c) for c in d.contact))
        for c in d.contact:
            if objectgeom in [int(c.geom1),int(c.geom2)]:
                other=int(c.geom2) if int(c.geom1)==objectgeom else int(c.geom1);name=mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_GEOM,other) or mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,int(m.geom_bodyid[other]));contact_pairs[name]=contact_pairs.get(name,0)+1
        other_contacts+=int(any(objectgeom in [int(c.geom1),int(c.geom2)] and not hand_geoms.intersection([int(c.geom1),int(c.geom2)]) for c in d.contact))
        a=angle(s,d,qi);err=abs(s['target_angle']-a);omega=abs(float(d.qvel[vi]));invalid|=not np.isfinite(d.qpos).all() or abs(a)>4
        settled=err<=s['target_tolerance'] and omega<=.07 and not invalid;dwell=dwell+DT if settled else 0.;effort+=float(np.sum(d.actuator_force**2))*DT
        if record and step%20==0:
            viz.qpos[:]=d.qpos;viz.qvel[:]=d.qvel;mujoco.mj_forward(m,viz)
            frames.append({'t':round(t,4),'positions':viz.xpos.tolist(),'quaternions':viz.xquat.tolist(),'angle':a,'angular_velocity':float(d.qvel[vi]),'phase':phase,'hand_contact':any(hand_contact(c) for c in d.contact)})
    result={'task':task,'scenario':s,'controller':asdict(controller),'success':bool(dwell>=s['dwell_seconds'] and contact_steps>0 and other_contacts==0 and not invalid),'final_angle':a,'error_degrees':math.degrees(err),'contact_steps':contact_steps,'contact_pairs':contact_pairs,'other_object_contact_steps':other_contacts,'dwell_seconds':dwell,'max_angular_speed':max_speed,'initial_ik_error_m':initial_error,'invalid':bool(invalid),'control_effort':effort,'stopped_angle':stopped_angle,'contact_definition':'Right-hand finger pad or palm. Forearm and other object contacts invalidate an episode.','source':'Local MuJoCo contact preview; untrained controller','rig_sha256':hashlib.sha256(json.dumps(RIG,sort_keys=True).encode()).hexdigest()}
    if record:result['trajectory']={'body_names':[mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,i) or 'world' for i in range(m.nbody)],'frames':frames,'sample_hz':25}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--task',choices=TASKS+('both',),default='both');p.add_argument('--seed',type=int,default=8000);p.add_argument('--speed',type=float,default=.45);p.add_argument('--brake',type=float,default=.025);p.add_argument('--out',default=str(ROOT/'artifacts/two-tasks'));args=p.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    for task in TASKS if args.task=='both' else [args.task]:
        r=rollout(task,args.seed,Controller(args.speed,args.brake),True);(out/(task+'.json')).write_text(json.dumps(r));(out/(task+'.xml')).write_text(xml(r['scenario']));print(task,{k:r[k] for k in ['success','error_degrees','contact_steps','other_object_contact_steps','initial_ik_error_m','final_angle']})
