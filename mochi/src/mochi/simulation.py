"""Deterministic MuJoCo contact task. No pose writes after episode initialization."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, os
import mujoco
import numpy as np

ROOT = next(p for p in [Path(os.environ.get('MOCHI_ROOT','.')),Path.cwd()/'mochi',Path(__file__).resolve().parents[2]] if (p/'configs/protocol.json').exists()).resolve()
PROTOCOL = json.loads((ROOT / "configs/protocol.json").read_text())
PROTOCOL_SHA = hashlib.sha256((ROOT / "configs/protocol.json").read_bytes()).hexdigest()

@dataclass(frozen=True)
class Policy:
    name: str = "starting-policy"
    speed: float = 0.20
    stop_distance: float = -0.045
    approach_offset: float = 0.045
    contact_height: float = 0.488
    recovery: bool = False

    def validate(self):
        assert 0.025 <= self.speed <= 0.25
        assert -0.06 <= self.stop_distance <= 0.03
        assert 0.035 <= self.approach_offset <= 0.07
        assert 0.481 <= self.contact_height <= 0.50
        return self

def scenario(seed: int, shift=False):
    rng = np.random.default_rng(seed)
    return dict(seed=seed, shift=shift,
                puck=[float(rng.uniform(-0.035, .035)), float(rng.uniform(.015, .045)), .48],
                target=[float(rng.uniform(-.03, .03)), float(rng.uniform(-.08, -.055)), .462],
                friction=float(rng.uniform(.65, 1.05) if shift else rng.uniform(.20, .65)),
                mass=float(rng.uniform(.075, .11) if shift else rng.uniform(.035, .075)))

def model_xml(s):
    x,y,z=s['puck']; tx,ty,tz=s['target']
    return f'''<mujoco model="Mochi original supported humanoid">
    <compiler angle="radian"/><option timestep="0.002" integrator="implicitfast"/>
    <visual><global offwidth="960" offheight="720"/></visual>
    <default><joint damping="1.5" armature="0.015"/><geom friction=".5 .01 .001" solref=".008 1" rgba=".9 .86 .76 1"/></default>
    <worldbody><light pos="0 -1 2"/><camera name="hero" pos="1.0 -1.3 1.1" xyaxes=".8 .6 0 -.3 .4 .86"/>
    <geom name="floor" type="plane" size="2 2 .1" rgba=".83 .81 .75 1"/>
    <geom name="table" type="box" pos="0 .0 .435" size=".36 .29 .025" friction="{s['friction']} .01 .001" rgba=".80 .66 .49 1"/>
    <geom name="target" type="cylinder" pos="{tx} {ty} {tz}" size=".028 .001" contype="0" conaffinity="0" rgba=".27 .65 .51 .5"/>
    <body name="torso" pos="0 .36 .58"><geom name="torso-shell" type="ellipsoid" size=".12 .075 .15" contype="0" conaffinity="0"/>
      <body name="head" pos="0 0 .24"><geom name="head-shell" type="box" size=".145 .09 .115" contype="0" conaffinity="0"/></body>
      <body name="left-upper" pos="-.14 -.015 .075"><geom name="left-upper-shell" type="capsule" fromto="0 0 0 -.045 -.035 -.16" size=".035" contype="0" conaffinity="0"/>
        <body name="left-fore" pos="-.045 -.035 -.16"><geom name="left-fore-shell" type="capsule" fromto="0 0 0 .02 -.11 -.04" size=".03" contype="0" conaffinity="0"/></body>
      </body>
      <body name="right-yaw" pos=".14 -.09 .08"><joint name="yaw" axis="0 0 1" range="-1.8 1.8"/>
       <geom name="right-shoulder" type="sphere" size=".04" mass=".05" contype="0" conaffinity="0"/>
       <body name="right-upper"><joint name="pitch" axis="1 0 0" range="-1.3 2.3"/>
        <geom name="right-upper-shell" type="capsule" fromto="0 0 0 0 -.22 0" size=".029" mass=".12" contype="0" conaffinity="0"/>
        <body name="right-fore" pos="0 -.22 0"><joint name="elbow" axis="1 0 0" range="-2.5 .2"/>
         <geom name="right-fore-shell" type="capsule" fromto="0 0 0 0 -.20 0" size=".024" mass=".09" contype="0" conaffinity="0"/>
         <body name="hand" pos="0 -.20 0"><geom name="paddle" type="sphere" size=".018" mass=".04" rgba=".91 .46 .32 1"/><site name="tip" size=".005"/></body>
        </body>
       </body>
      </body>
    </body>
    <body name="left-leg" pos="-.065 .36 .22"><geom name="left-leg-shell" type="capsule" fromto="0 0 -.12 0 0 .18" size=".04" contype="0" conaffinity="0"/>
      <body name="left-foot" pos="0 -.025 -.15"><geom name="left-foot-shell" type="box" size=".055 .085 .035" contype="0" conaffinity="0"/></body></body>
    <body name="right-leg" pos=".065 .36 .22"><geom name="right-leg-shell" type="capsule" fromto="0 0 -.12 0 0 .18" size=".04" contype="0" conaffinity="0"/>
      <body name="right-foot" pos="0 -.025 -.15"><geom name="right-foot-shell" type="box" size=".055 .085 .035" contype="0" conaffinity="0"/></body></body>
    <body name="puck" pos="{x} {y} {z}"><freejoint/><geom name="puck-shell" type="cylinder" size=".025 .012" mass="{s['mass']}" friction="{s['friction']} .01 .001" rgba=".96 .63 .22 1"/></body>
    </worldbody><actuator>
    <position joint="yaw" kp="70" kv="5" ctrlrange="-1.8 1.8" forcerange="-6 6"/>
    <position joint="pitch" kp="70" kv="5" ctrlrange="-1.3 2.3" forcerange="-6 6"/>
    <position joint="elbow" kp="55" kv="4" ctrlrange="-2.5 .2" forcerange="-5 5"/>
    </actuator></mujoco>'''

def rollout(policy: Policy, seed: int, shift=False, record=False):
    policy.validate(); s=scenario(seed, shift)
    m=mujoco.MjModel.from_xml_string(model_xml(s)); d=mujoco.MjData(m)
    d.qpos[:3]=[.25,1.25,-1.5]; d.ctrl[:]=d.qpos[:3]
    mujoco.mj_forward(m,d)
    site=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_SITE,"tip")
    puck=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,"puck")
    pg=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,"puck-shell")
    hg=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,"paddle")
    target=np.array(s['target'][:2]); initial=np.array(s['puck'][:2])
    direction=(target-initial); direction/=np.linalg.norm(direction)
    phase='approach'; push_start=0.; dwell=0.; success_at=None; effort=0.; contacts=0; max_progress=0.; invalid=False
    frames=[]; phases=[]; contact_flags=[]; jac=np.zeros((3,m.nv)); started=None
    horizon=PROTOCOL['horizon_seconds']; last_ctrl=d.ctrl.copy(); smooth=0.
    for step in range(round(horizon/m.opt.timestep)):
        t=step*m.opt.timestep; pos=d.xpos[puck,:2].copy(); hand=d.site_xpos[site].copy(); distance=float(np.linalg.norm(pos-target))
        if step%10==0:
            behind=pos-direction*policy.approach_offset
            if phase=='approach':
                desired=np.r_[behind,.56]
                if np.linalg.norm(hand-desired)<.018 or t>1.3:phase='lower'
            if phase=='lower':
                desired=np.r_[behind,policy.contact_height]
                if np.linalg.norm(hand-desired)<.012 or t>2.3:
                    phase='push'; push_start=t; started=pos.copy()
            if phase=='push':
                remaining=float(np.dot(target-pos,direction))
                if remaining<=policy.stop_distance:phase='retract'
                desired=np.r_[initial-direction*policy.approach_offset+direction*policy.speed*(t-push_start),policy.contact_height]
                if policy.recovery:
                    delta=target-pos; norm=np.linalg.norm(delta)
                    active_dir=delta/max(norm,1e-9)
                    desired=np.r_[pos-active_dir*.029+active_dir*min(.045,policy.speed*.25),policy.contact_height]
                    if norm<max(.008,policy.stop_distance):phase='retract'
            if phase=='retract':desired=np.r_[hand[:2],.60]
            error=desired-hand
            mujoco.mj_jacSite(m,d,jac,None,site)
            j=jac[:,:3]; dq=j.T@np.linalg.solve(j@j.T+np.eye(3)*.001,error)
            command=np.clip(d.qpos[:3]+np.clip(dq,-.12,.12),m.jnt_range[:3,0],m.jnt_range[:3,1])
            smooth+=float(np.sum((command-last_ctrl)**2)); last_ctrl=command.copy(); d.ctrl[:]=command
        # Documented gravity compensation on the actuated arm, through forces.
        d.qfrc_applied[:3]=d.qfrc_bias[:3]
        mujoco.mj_step(m,d)
        contact=any({int(c.geom1),int(c.geom2)}=={pg,hg} for c in d.contact)
        contacts+=int(contact); effort+=float(np.sum(d.actuator_force**2))*m.opt.timestep
        pos=d.xpos[puck,:2]; distance=float(np.linalg.norm(pos-target))
        invalid|=bool(abs(pos[0])>.345 or abs(pos[1])>.28 or d.xpos[puck,2]<.43 or not np.isfinite(d.qpos).all())
        dwell=dwell+m.opt.timestep if distance<=PROTOCOL['success_radius_m'] and not invalid else 0.
        if dwell>=PROTOCOL['dwell_seconds'] and success_at is None:success_at=t
        max_progress=max(max_progress,float(np.dot(pos-initial,direction)))
        if record and step%20==0:
            frames.append({'t':round(t,4),'positions':d.xpos.tolist(),'quaternions':d.xquat.tolist()})
            phases.append(phase);contact_flags.append(contact)
    final_distance=float(np.linalg.norm(d.xpos[puck,:2]-target))
    # Success must persist through the terminal state, not just cross the ring.
    success=bool(success_at is not None and dwell>=PROTOCOL['dwell_seconds'] and not invalid)
    result={'policy':asdict(policy),'scenario':s,'success':success,'final_distance_m':final_distance,'completion_seconds':success_at if success else None,'invalid':invalid,'contact_steps':contacts,'control_effort':effort,'smoothness':smooth,'overshoot_m':max(0.,max_progress-float(np.linalg.norm(target-initial))),'failure':'success' if success else 'left-table' if invalid else 'no-contact' if contacts==0 else 'overshoot' if max_progress>np.linalg.norm(target-initial)+.028 else 'undershoot','protocol_sha256':PROTOCOL_SHA}
    if record:
        result['trajectory']={'body_names':[mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,i) or 'world' for i in range(m.nbody)],'frames':frames,'phases':phases,'contact':contact_flags,'sample_hz':25,'source':'MuJoCo 3.3.7 body poses; supported base; right arm only'}
        result['model_xml']=model_xml(s)
    return result

def summarize(results):
    n=len(results); k=sum(r['success'] for r in results); p=k/max(n,1); z=1.96; den=1+z*z/max(n,1)
    centre=(p+z*z/(2*max(n,1)))/den; half=z*np.sqrt(p*(1-p)/max(n,1)+z*z/(4*max(n,1)**2))/den
    return {'n':n,'successes':k,'success_rate':p,'wilson_95':[max(0.,centre-half),min(1.,centre+half)],'mean_final_distance_m':float(np.mean([r['final_distance_m'] for r in results])),'invalid':sum(r['invalid'] for r in results)}

def evaluate(policy, seeds, shift=False):return [rollout(policy,seed,shift) for seed in seeds]
