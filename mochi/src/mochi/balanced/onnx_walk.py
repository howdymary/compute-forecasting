"""Adapter for a pinned, Apache-2.0 external G1 velocity policy.

This is fixed pretrained inference, not Mochi/Tinker training. Missing waist
DOFs are explicitly represented at their fixed zero pose in this first probe.
"""
import hashlib,json,math
import mujoco,numpy as np
import onnxruntime as ort
from ..curriculum.world import ROOT,SCALE


class HubWalker:
    label='external-fixed-g1-29dof-velocity-policy'
    def __init__(self,world):
        old=world.walker;self.w=world;self.m=world.m;self.d=world.d
        for k in ['qids','vids','aids','offsets','scale','time_scale']:setattr(self,k,getattr(old,k))
        options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
        model=ROOT/'assets/robot/g1-v11-policy/exported/policy.onnx'
        self.source=json.loads((model.parents[1]/'source.json').read_text())
        if hashlib.sha256(model.read_bytes()).hexdigest()!=self.source['files']['exported/policy.onnx']['sha256']:
            raise RuntimeError('Pinned gait model checksum mismatch')
        self.session=ort.InferenceSession(str(model),sess_options=options,providers=['CPUExecutionProvider'])
        meta=self.session.get_modelmeta().custom_metadata_map;self.names=meta['joint_names'].split(',')
        floats=lambda k:np.array([float(x) for x in meta[k].split(',')])
        self.default=floats('default_joint_pos');self.scales=floats('action_scale');self.kp=floats('joint_stiffness')*SCALE**4;self.kd=floats('joint_damping')*SCALE**4.5
        self.qmap=[];self.vmap=[];self.amap=[];self.home=[]
        for name in self.names:
            j=world.id('joint',name)
            self.qmap.append(int(self.m.jnt_qposadr[j]) if j>=0 else None);self.vmap.append(int(self.m.jnt_dofadr[j]) if j>=0 else None)
            self.amap.append(world.id('actuator',name) if j>=0 else None);self.home.append(world.meta['home_joint_offsets'].get(name,0.))
        self.home=np.array(self.home);self.action=np.zeros(29,dtype=np.float32);self.target=self.default-self.home
        self.velocity_integral=np.zeros(2);self.yaw_integral=0.;self.last=-1.;self.origin=float(self.d.time);self.calls=0;self.filtered_command=np.zeros(3)
        self.feedback=.7
        self.mode='walk';self.control_arms=True;self.stand_phase=None;self.stage='native-walk'

    def hold(self):
        self.stand_phase=(float(self.d.time)-self.origin)/self.time_scale%.6
        self.mode='phase-frozen-balance';self.control_arms=False;self.stage='native-supported-stop'
        for arm in self.w.arm.values():self.d.ctrl[arm['acts']]=self.d.qpos[arm['qs']]

    def resume(self):
        if self.mode!='walk':
            self.origin=float(self.d.time)-self.stand_phase*self.time_scale
        self.mode='walk';self.control_arms=True;self.stage='native-walk'

    def command(self,velocity):
        m,d=self.m,self.d;interval=.02*self.time_scale
        if d.time-self.last>=interval-1e-9:
            self.last=float(d.time);q=d.qpos[3:7];w,x,y,z=q
            gravity=np.array([2*(-z*x+w*y),-2*(z*y+w*x),1-2*(w*w+z*z)])
            desired=np.array(velocity if self.mode=='walk' else (0,0,0),dtype=float)
            actual=d.xmat[1].reshape(3,3).T@d.qvel[:3]
            desired[:2]=np.clip(desired[:2]+self.feedback*(desired[:2]-actual[:2]),-.12,.12)
            self.filtered_command+=np.clip(desired-self.filtered_command,-np.array([.6,.6,4])*interval,np.array([.6,.6,4])*interval)
            positions=np.array([d.qpos[k] if k is not None else 0. for k in self.qmap])+self.home
            speeds=np.array([d.qvel[k] if k is not None else 0. for k in self.vmap])
            phase=(((float(d.time)-self.origin)/self.time_scale%.6) if self.mode=='walk' else self.stand_phase)/.6
            obs=np.r_[d.qvel[3:6]*self.time_scale,gravity,
                self.filtered_command*np.array([1/self.time_scale,1/self.time_scale,self.time_scale]),
                math.sin(2*math.pi*phase),math.cos(2*math.pi*phase),positions-self.default,speeds*self.time_scale,self.action].astype(np.float32)
            self.action=self.session.run(None,{'obs':obs[None]})[0][0];self.target=self.default+self.scales*self.action-self.home;self.calls+=1
        legs=set(self.aids)
        for i,a in enumerate(self.amap):
            if a is None or a<0:continue
            if not self.control_arms and a not in legs:continue
            qid,vid=self.qmap[i],self.vmap[i]
            tau=self.kp[i]*(self.target[i]-d.qpos[qid])-self.kd[i]*d.qvel[vid]
            if a in legs or m.actuator_biastype[a]==mujoco.mjtBias.mjBIAS_NONE:d.ctrl[a]=tau
            else:
                # Existing arm position actuators plus the world's explicit
                # joint gravity compensation reproduce the policy's PD torque.
                kp=m.actuator_gainprm[a,0];kv=-m.actuator_biasprm[a,2]
                d.ctrl[a]=d.qpos[qid]+(tau-d.qfrc_bias[vid]+kv*d.qvel[vid])/kp

    def description(self):
        return {'controller':self.label,'inference_calls':self.calls,'model_source':json.loads((ROOT/'assets/robot/g1-v11-policy/source.json').read_text()),
            'missing_fixed_joints':[n for n,k in zip(self.names,self.qmap) if k is None],
            'native_weights_trained':False,'tinker_optimizer_updates':0,'mode':self.mode}


class HoldWalker:
    """Capture a supported stance and stabilize it using joint torques."""
    label='captured-supported-stance'
    def __init__(self,world,neutral=False):
        self.w=world;self.m=world.m;self.d=world.d;old=world.walker
        for name in ['qids','vids','aids','offsets','scale','time_scale']:setattr(self,name,getattr(old,name))
        self.target=self.d.qpos[self.qids].copy();self.initial_target=self.target.copy();self.neutral=neutral;self.origin=float(self.d.time)
        from ..curriculum.locomotion import DEFAULT
        self.final_target=DEFAULT-self.offsets if neutral else self.target.copy()
        self.action=np.zeros(12);self.last=-1.;self.velocity_integral=np.zeros(2);self.yaw_integral=0.;self.stage='hold'
        self.standing_target=self.target.copy()
        self.previous_description=old.description()
        for arm in world.arm.values():self.d.ctrl[arm['acts']]=self.d.qpos[arm['qs']]

    def command(self,velocity):
        d=self.d;m=self.m;kp=np.array([100,100,100,150,40,40]*2)*SCALE**4*6;kd=np.array([2,2,2,4,2,2]*2)*SCALE**4.5*6
        u=float(np.clip((d.time-self.origin)/.35,0,1));u=u**3*(10+u*(-15+6*u))
        self.target=self.initial_target+(self.final_target-self.initial_target)*u
        self.standing_target=self.target.copy()
        tau=kp*(self.target-d.qpos[self.qids])-kd*d.qvel[self.vids]+d.qfrc_bias[self.vids]
        R=d.xmat[1].reshape(3,3);feet=[d.xpos[self.w.id('body',s+'_ankle_roll_link')] for s in ['left','right']]
        center=np.mean(feet,axis=0)+R@np.array([.0058,0,0]);error=R.T@(d.subtree_com[1]-center);mass=m.body_subtreemass[1]
        pitch=math.asin(float(np.clip(-R[2,0],-1,1)));roll=math.atan2(R[2,1],R[2,2])
        for i in [4,10]:tau[i]+=mass*9.81*error[0]/2+.22*pitch+.012*d.qvel[4]
        for i in [5,11]:tau[i]+=-mass*9.81*error[1]/2+.22*roll+.012*d.qvel[3]
        limits=m.actuator_forcerange[self.aids];d.ctrl[self.aids]=np.clip(tau,limits[:,0],limits[:,1])
        for q,v,a in getattr(self.w,'waist',[]):d.ctrl[a]=-100*SCALE**4*d.qpos[q]-6*SCALE**4.5*d.qvel[v]+d.qfrc_bias[v]

    def description(self):return {'controller':self.label,'stance_reference':'neutral-blend' if self.neutral else 'captured',
                                  'walking_controller':self.previous_description,'native_weights_trained':False}
