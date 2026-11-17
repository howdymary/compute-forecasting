"""Native-scale desk eraser task. The robot and eraser share the actual desktop."""
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,math,os
import mujoco
import numpy as np

ROOT=Path(os.environ.get('MOCHI_ROOT',Path(__file__).resolve().parents[3])).resolve()
PROTOCOL=json.loads((ROOT/'desk-protocol.json').read_text())
PROTOCOL_SHA=hashlib.sha256((ROOT/'desk-protocol.json').read_bytes()).hexdigest()

@dataclass(frozen=True)
class Controller:
    code:str
    speed:float
    brake:float
    align:float=.015
    tracking:bool=True
    def validate(self):
        assert .008<=self.speed<=.16 and -.025<=self.brake<=.025 and 0<=self.align<=.04
        return self

CATALOG=[Controller('A',.020,.002),Controller('B',.030,.003),Controller('C',.045,.004),Controller('D',.065,.006),Controller('E',.085,.010),Controller('F',.110,.014),Controller('G',.040,.004,.030),Controller('H',.070,.008,.030)]
REFERENCE=Controller('reference',.13,-.018,0,False)

def scenario(seed:int):
    rng=np.random.default_rng(seed);surface='wood' if seed%2==0 else 'felt'
    return {'seed':seed,'surface':surface,'object_xy':[float(rng.uniform(-.018,.018)),float(rng.uniform(-.012,.008))],'object_yaw':float(rng.uniform(-.50,.50)),'target_xy':[float(rng.uniform(-.025,.025)),float(rng.uniform(-.065,-.040))],'mass':float(rng.uniform(.009,.022)),'friction':float(rng.uniform(.13,.28) if surface=='wood' else rng.uniform(.55,.85))}

def xml(s):
    x,y=s['object_xy'];tx,ty=s['target_xy'];yaw=s['object_yaw'];shade='.48 .34 .21 1' if s['surface']=='wood' else '.24 .30 .27 1'
    return f'''<mujoco model="Mochi direct desk eraser">
    <compiler angle="radian"/><option timestep="0.002" integrator="implicitfast" iterations="70"/>
    <default><joint damping=".025" armature=".00008"/><geom friction=".5 .005 .0001" solref=".006 1" solimp=".95 .99 .001" rgba=".84 .85 .81 1"/></default>
    <worldbody>
      <geom name="desk" type="box" pos="0 0 -.02" size=".60 .40 .02" friction="{s['friction']} .005 .0001" rgba="{shade}"/>
      <geom name="target" type="box" pos="{tx} {ty} .00015" size=".031 .023 .0001" contype="0" conaffinity="0" rgba=".4 .7 .5 .2"/>
      <body name="pelvis" pos="0 .079 .035"><geom type="box" size=".023 .017 .012"/></body>
      <body name="torso" pos="0 .058 .064" euler=".35 0 0"><geom type="box" size=".026 .016 .033"/>
        <body name="head" pos="0 0 .056"><geom type="box" size=".021 .018 .019"/></body>
      </body>
      <body name="left-thigh" pos="-.018 .085 .035"><geom type="capsule" fromto="0 0 0 -.007 -.035 -.022" size=".009"/></body>
      <body name="right-thigh" pos=".018 .085 .035"><geom type="capsule" fromto="0 0 0 .007 -.035 -.022" size=".009"/></body>
      <body name="left-shin" pos="-.025 .05 .013"><geom type="capsule" fromto="0 0 0 0 .057 -.006" size=".007"/></body>
      <body name="right-shin" pos=".025 .05 .013"><geom type="capsule" fromto="0 0 0 0 .057 -.006" size=".007"/></body>
      <body name="left-foot" pos="-.025 .117 .008"><geom type="box" size=".012 .020 .008"/></body>
      <body name="right-foot" pos=".025 .117 .008"><geom type="box" size=".012 .020 .008"/></body>
      <body name="left-upper" pos="-.033 .031 .065"><geom type="capsule" fromto="0 0 0 -.030 -.022 -.030" size=".006"/></body>
      <body name="left-fore" pos="-.063 .009 .035"><geom type="capsule" fromto="0 0 0 -.005 -.034 -.025" size=".005"/>
        <body name="left-hand" pos="-.005 -.034 -.025"><geom type="sphere" size=".006"/></body>
      </body>
      <body name="right-yaw" pos=".033 .031 .065"><joint name="yaw" axis="0 0 1" range="-2.4 2.4"/><geom type="sphere" size=".010" mass=".015" contype="0" conaffinity="0"/>
        <body name="right-upper"><joint name="pitch" axis="1 0 0" range="-1.6 2.4"/><geom type="capsule" fromto="0 0 0 0 -.070 0" size=".006" mass=".025"/>
          <body name="right-fore" pos="0 -.070 0"><joint name="elbow" axis="1 0 0" range="-.6 2.9"/><geom type="capsule" fromto="0 0 0 0 -.065 0" size=".005" mass=".020"/>
            <body name="hand" pos="0 -.065 0"><geom name="contact-pad" type="sphere" size=".0055" mass=".008"/><site name="tip" size=".001"/></body>
          </body>
        </body>
      </body>
      <body name="eraser" pos="{x} {y} .0065" euler="0 0 {yaw}"><freejoint/><geom name="eraser-contact" type="box" size=".018 .010 .006" mass="{s['mass']}" friction="{s['friction']} .005 .0001" rgba=".81 .47 .35 1"/></body>
      <geom name="mug-proxy" type="cylinder" pos=".17 .04 .045" size=".036 .045"/>
    </worldbody>
    <actuator><position joint="yaw" kp="8" kv=".055" ctrlrange="-2.4 2.4" forcerange="-.12 .12"/><position joint="pitch" kp="8" kv=".055" ctrlrange="-1.6 2.4" forcerange="-.12 .12"/><position joint="elbow" kp="6" kv=".045" ctrlrange="-.6 2.9" forcerange="-.10 .10"/></actuator>
    </mujoco>'''

def wrap(a):return float((a+math.pi)%(2*math.pi)-math.pi)
def observation(s):
    return {'surface':s['surface'],'object_xy_mm':[round(v*1000,1) for v in s['object_xy']],'object_yaw_degrees':round(math.degrees(s['object_yaw']),1),'target_xy_mm':[round(v*1000,1) for v in s['target_xy']]}

def rollout(controller:Controller,seed:int,record=False):
    controller.validate();s=scenario(seed);m=mujoco.MjModel.from_xml_string(xml(s));d=mujoco.MjData(m)
    d.qpos[:3]=[0.,-.75,1.45];d.ctrl[:]=d.qpos[:3];mujoco.mj_forward(m,d)
    tip=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_SITE,'tip');obj=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,'eraser');pad=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,'contact-pad');og=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,'eraser-contact')
    goal=np.asarray(s['target_xy']);initial=np.asarray(s['object_xy']);direction=goal-initial;direction/=np.linalg.norm(direction);phase='approach';push_at=None;start_contact=None;dwell=0.;contacts=0;invalid=False;effort=0.;frames=[];phases=[];jac=np.zeros((3,m.nv));last_desired=None
    for step in range(int(PROTOCOL['horizon_seconds']/m.opt.timestep)):
        t=step*m.opt.timestep;pos=d.xpos[obj,:2].copy();hand=d.site_xpos[tip].copy();yaw=math.atan2(d.xmat[obj,3],d.xmat[obj,0]);delta=goal-pos;distance=float(np.linalg.norm(delta));vel=d.qvel[3:6];speed=float(np.linalg.norm(vel[:2]));yawerr=abs(wrap(yaw))
        if step%10==0:
            active=delta/max(distance,1e-8) if controller.tracking else direction
            normal=np.array([-active[1],active[0]]);axis=np.array([math.cos(yaw),math.sin(yaw)]);side=np.array([-axis[1],axis[0]])
            lateral=float(np.clip(controller.align*wrap(yaw),-.007,.007));local_dir=np.array([axis@(-active),side@(-active)]);local_offset=np.array([axis@(normal*lateral),side@(normal*lateral)])
            support=float(np.min((np.array([.0235,.0155])-np.sign(local_dir)*local_offset)/np.maximum(np.abs(local_dir),1e-8)));behind=pos-active*(support+.002)+normal*lateral
            if phase=='approach':
                desired=np.r_[behind,.043]
                if np.linalg.norm(hand-desired)<.006 or t>.9:phase='lower'
            if phase=='lower':
                desired=np.r_[behind,.007]
                if np.linalg.norm(hand-desired)<.004 or t>1.65:phase='push';push_at=t;start_contact=behind.copy()
            if phase=='push':
                if distance<=controller.brake or float((goal-pos)@direction)<controller.brake:phase='retract'
                if controller.tracking:desired=np.r_[pos-active*(support-.002)+normal*lateral,.007]
                else:desired=np.r_[start_contact+direction*controller.speed*(t-push_at),.007]
            if phase=='retract':desired=np.r_[hand[:2],.060]
            error=desired-hand;max_step=(controller.speed if phase=='push' else .16)*PROTOCOL['control_dt'];norm=np.linalg.norm(error)
            if norm>max_step:error*=max_step/norm
            mujoco.mj_jacSite(m,d,jac,None,tip);j=jac[:,:3];dq=j.T@np.linalg.solve(j@j.T+np.eye(3)*.000015,error)
            d.ctrl[:]=np.clip(d.qpos[:3]+np.clip(dq,-.15,.15),m.jnt_range[:3,0],m.jnt_range[:3,1]);last_desired=desired
        d.qfrc_applied[:3]=d.qfrc_bias[:3];mujoco.mj_step(m,d)
        contacts+=int(any({int(c.geom1),int(c.geom2)}=={pad,og} for c in d.contact));effort+=float(np.sum(d.actuator_force**2))*m.opt.timestep
        pos=d.xpos[obj,:2];yaw=math.atan2(d.xmat[obj,3],d.xmat[obj,0]);yawerr=abs(wrap(yaw));distance=float(np.linalg.norm(pos-goal));speed=float(np.linalg.norm(d.qvel[3:5]));invalid|=bool(abs(pos[0])>.58 or abs(pos[1])>.38 or d.xpos[obj,2]<-.01 or not np.isfinite(d.qpos).all())
        extent=np.array([.018*abs(math.cos(yaw))+.010*abs(math.sin(yaw)),.018*abs(math.sin(yaw))+.010*abs(math.cos(yaw))]);inside=bool(np.all(np.abs(pos-goal)+extent<=np.array(PROTOCOL['target_half_size_m'])))
        settled=inside and yawerr<=PROTOCOL['orientation_tolerance_rad'] and speed<=PROTOCOL['max_terminal_speed_m_s'] and not invalid;dwell=dwell+m.opt.timestep if settled else 0.
        if record and step%20==0:frames.append({'t':round(t,4),'positions':d.xpos.tolist(),'quaternions':d.xquat.tolist(),'joints':d.qpos[:3].tolist(),'desired':last_desired.tolist() if last_desired is not None else None,'collisions':[[mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_GEOM,int(c.geom1)),mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_GEOM,int(c.geom2))] for c in d.contact]});phases.append(phase)
    success=bool(dwell>=PROTOCOL['dwell_seconds'] and not invalid);error=distance+.018*yawerr
    result={'controller':asdict(controller),'scenario':s,'observation':observation(s),'success':success,'inside':inside,'distance_m':distance,'yaw_error_rad':yawerr,'pose_error':error,'terminal_speed_m_s':speed,'dwell_seconds':dwell,'contact_steps':contacts,'invalid':invalid,'control_effort':effort,'failure':'success' if success else 'invalid' if invalid else 'no-contact' if contacts==0 else 'misaligned' if inside else 'overshoot' if float((goal-pos)@direction)<0 else 'undershoot','protocol_sha256':PROTOCOL_SHA}
    if record:result['trajectory']={'body_names':[mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,i) or 'world' for i in range(m.nbody)],'frames':frames,'phases':phases,'sample_hz':25,'source':'MuJoCo direct-on-desk eraser; native meters; supported crouch'}
    return result

def summary(rows):
    n=len(rows);k=sum(x['success'] for x in rows);p=k/max(n,1);z=1.96;den=1+z*z/max(n,1);center=(p+z*z/(2*max(n,1)))/den;half=z*math.sqrt(p*(1-p)/max(n,1)+z*z/(4*max(n,1)**2))/den
    return {'n':n,'successes':k,'success_rate':p,'wilson_95':[max(0,center-half),min(1,center+half)],'mean_pose_error':float(np.mean([x['pose_error'] for x in rows])),'invalid':sum(x['invalid'] for x in rows)}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--seed',type=int,default=7000);parser.add_argument('--out',default='mochi/artifacts/desk-local');args=parser.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    for c in [REFERENCE,*CATALOG]:
        r=rollout(c,args.seed,record=True);(out/(c.code+'.json')).write_text(json.dumps(r));print(c.code,{k:r[k] for k in ['success','distance_m','yaw_error_rad','failure','contact_steps']})
