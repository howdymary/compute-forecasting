"""Terrain-aware foot references around the fixed pretrained gait.

Only actuator targets change. All inverse kinematics use detached MjData.
This is controller engineering, not training of the native gait network.
"""
import math
import mujoco
import numpy as np
from ..balanced.onnx_walk import HubWalker


class TerrainWalker(HubWalker):
    label='terrain-foot-clearance-around-fixed-gait'
    def __init__(self,w,lift=.010,level_gain=1.,compensation=1.,lookahead=.018,period=.6):
        super().__init__(w)
        self.lift=lift;self.level_gain=level_gain;self.compensation=compensation;self.lookahead=lookahead;self.period=period
        self.residual=np.zeros(29);self.residual_velocity=np.zeros(29);self.levels=np.zeros(2);self.scratch=mujoco.MjData(self.m)
        self.side_indices=[np.array([i for i,n in enumerate(self.names) if n.startswith(side+'_') and any(k in n for k in ['hip_','knee_','ankle_'])]) for side in ['left','right']]
        self.feet=[w.id('body',s+'_ankle_roll_link') for s in ['left','right']]
        self.local=np.array([.005,0,-.00585]);self.terrain_log=[]

    def terrain_offsets(self,phase):
        R=self.d.xmat[1].reshape(3,3);desired=[];swing=[]
        for i,body in enumerate(self.feet):
            p=self.d.xpos[body]+self.d.xmat[body].reshape(3,3)@self.local
            swing_phase=(phase+(.5 if i==0 else 0))%1.
            u=swing_phase*2
            airborne=u<1
            forward=self.lookahead if airborne else 0.
            xy=p[:2]+R[:2,0]*forward
            desired.append(self.w.terrain_height(*xy,margin=.001))
            # Raised clearance applies only around actual book terrain. No
            # book/clock geometry or collision property is edited.
            near=any(self.w.terrain_height(*(p[:2]+R[:2,0]*a))>0 for a in [0.,.02,.04])
            swing.append(self.lift*math.sin(math.pi*u)**2 if airborne and near else 0.)
        self.levels+=np.clip(np.array(desired)-self.levels,-.002,.002)
        return (self.levels-np.mean(self.levels))*self.level_gain+np.array(swing)

    def corrected_target(self,raw,offsets):
        s=self.scratch;s.qpos[:]=self.d.qpos
        for q,v in zip(self.qmap,raw):
            if q is not None:s.qpos[q]=v
        mujoco.mj_forward(self.m,s)
        refs=[]
        for i,b in enumerate(self.feet):
            R=s.xmat[b].reshape(3,3).copy();point=s.xpos[b]+R@self.local
            refs.append((point+np.array([0,0,offsets[i]]),R))
        refs=self.foot_references(refs)
        for _ in range(4):
            for i,indices in enumerate(self.side_indices):
                if abs(offsets[i])<1e-7 and not getattr(self,'planned_swing',False):continue
                b=self.feet[i];mujoco.mj_forward(self.m,s);R=s.xmat[b].reshape(3,3);point=s.xpos[b]+R@self.local
                ptarget,Rtarget=refs[i];rot=.5*sum((np.cross(R[:,j],Rtarget[:,j]) for j in range(3)),np.zeros(3))
                J=np.zeros((3,self.m.nv));Jr=np.zeros_like(J);mujoco.mj_jac(self.m,s,J,Jr,point,b)
                qs=np.array([self.qmap[k] for k in indices]);vs=np.array([self.vmap[k] for k in indices]);A=np.vstack([J[:,vs],Jr[:,vs]*.03])
                delta=A.T@np.linalg.solve(A@A.T+np.eye(6)*2e-8,np.r_[ptarget-point,rot*.03])
                joints=np.array([self.w.id('joint',self.names[k]) for k in indices]);limits=self.m.jnt_range[joints]
                s.qpos[qs]=np.clip(s.qpos[qs]+np.clip(delta,-.12,.12),limits[:,0]+.002,limits[:,1]-.002)
        return np.array([s.qpos[q] if q is not None else raw[i] for i,q in enumerate(self.qmap)])

    def foot_references(self,refs):return refs

    def command(self,velocity):
        d=self.d;m=self.m;interval=.02*self.time_scale
        if d.time-self.last>=interval-1e-9:
            self.last=float(d.time);q=d.qpos[3:7];w,x,y,z=q
            gravity=np.array([2*(-z*x+w*y),-2*(z*y+w*x),1-2*(w*w+z*z)])
            desired=np.array(velocity if self.mode=='walk' else (0,0,0),dtype=float)
            actual=d.xmat[1].reshape(3,3).T@d.qvel[:3]
            desired[:2]=np.clip(desired[:2]+self.feedback*(desired[:2]-actual[:2]),-.12,.12)
            self.filtered_command+=np.clip(desired-self.filtered_command,-np.array([.6,.6,4])*interval,np.array([.6,.6,4])*interval)
            positions=np.array([d.qpos[k] if k is not None else 0. for k in self.qmap])+self.home-self.compensation*self.residual
            speeds=np.array([d.qvel[k] if k is not None else 0. for k in self.vmap])-self.compensation*self.residual_velocity
            phase=(((float(d.time)-self.origin)/self.time_scale%self.period) if self.mode=='walk' else self.stand_phase)/self.period
            self.current_phase=phase
            obs=np.r_[d.qvel[3:6]*self.time_scale,gravity,self.filtered_command*np.array([1/self.time_scale,1/self.time_scale,self.time_scale]),
                      math.sin(2*math.pi*phase),math.cos(2*math.pi*phase),positions-self.default,speeds*self.time_scale,self.action].astype(np.float32)
            self.action=self.session.run(None,{'obs':obs[None]})[0][0];raw=self.default+self.scales*self.action-self.home
            offsets=self.terrain_offsets(phase) if self.mode=='walk' else self.levels-np.mean(self.levels)
            self.target=self.corrected_target(raw,offsets);residual=self.target-raw
            self.residual_velocity=.5*self.residual_velocity+.5*np.clip((residual-self.residual)/interval,-20,20)
            self.residual=residual;self.calls+=1
            if not self.terrain_log or d.time-self.terrain_log[-1]['t']>.04:
                self.terrain_log.append({'t':float(d.time),'offsets_m':offsets.tolist(),'levels_m':self.levels.tolist(),'maximum_joint_residual_rad':float(np.max(abs(self.residual)))})
        legs=set(self.aids)
        for i,a in enumerate(self.amap):
            if a is None or a<0 or (not self.control_arms and a not in legs):continue
            qid,vid=self.qmap[i],self.vmap[i];tau=self.kp[i]*(self.target[i]-d.qpos[qid])-self.kd[i]*d.qvel[vid]
            if a in legs or m.actuator_biastype[a]==mujoco.mjtBias.mjBIAS_NONE:d.ctrl[a]=tau
            else:
                kp=m.actuator_gainprm[a,0];kv=-m.actuator_biasprm[a,2]
                d.ctrl[a]=d.qpos[qid]+(tau-d.qfrc_bias[vid]+kv*d.qvel[vid])/kp

    def description(self):
        return {**super().description(),'terrain_parameters':{k:getattr(self,k) for k in ['lift','level_gain','compensation','lookahead','period']},'terrain_log':self.terrain_log,'native_weights_trained':False}


class PlannedSwingWalker(TerrainWalker):
    label='explicit-whole-sole-landings-around-fixed-balance-gait'
    planned_swing=True
    def __init__(self,w,stride=.018,tracking_gain=.5,**kwargs):
        super().__init__(w,**kwargs);self.stride=stride;self.tracking_gain=tracking_gain;self.active_swing=None;self.start=None;self.goal=None;self.landings=[]

    def foot_references(self,refs):
        from ..richdesk.stepping import ease
        phase=self.current_phase;i=1 if phase<.5 else 0;u=(phase% .5)*2
        R=self.d.xmat[1].reshape(3,3);yaw=self.w.yaw();c,s=math.cos(yaw),math.sin(yaw)
        orientation=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
        if not any(self.w.terrain_height(*(self.d.qpos[:2]+orientation[:2,0]*a))>0 for a in [0.,.03,.05]):
            self.active_swing=None;return refs
        if self.active_swing!=i:
            self.active_swing=i;b=self.feet[i];self.start=self.d.xpos[b]+self.d.xmat[b].reshape(3,3)@self.local
            other=self.feet[1-i];stance=self.d.xpos[other]+self.d.xmat[other].reshape(3,3)@self.local
            direction=orientation[:,0];side=orientation[:,1]
            goal=stance+direction*self.stride+side*(.038 if i==0 else -.038)
            # Search only a short reachable corridor for a flat whole-sole
            # patch. Forward progress cannot be certified by a toe on a riser.
            candidates=[]
            for advance in np.arange(0,.046,.002):
                point=goal+direction*advance;heights=[]
                for a in [-.020,.020]:
                    for b in [-.008,.008]:heights.append(self.w.terrain_height(*(point+direction*a+side*b)[:2]))
                if max(heights)-min(heights)<.0001:
                    candidates.append((advance,point,max(heights)))
            if candidates:
                _,goal,height=candidates[0];goal[2]=height-.00015
            else:goal=self.start.copy()
            self.goal=goal;self.landings.append({'t':float(self.d.time),'side':['left','right'][i],'start':self.start.tolist(),'goal':goal.tolist()})
        target=(1-ease(u))*self.start+ease(u)*self.goal
        peak=max(self.start[2],self.goal[2])+self.lift
        if u<.45:target[2]=(1-ease(u/.45))*self.start[2]+ease(u/.45)*peak
        else:target[2]=(1-ease((u-.55)/.45))*peak+ease((u-.55)/.45)*self.goal[2]
        actual=self.d.xpos[self.feet[i]]+self.d.xmat[self.feet[i]].reshape(3,3)@self.local
        # Preserve the native policy's force-producing position bias. An
        # absolute Cartesian replacement removed that bias and failed flat
        # walking. Apply only a bounded swing-position tracking residual.
        refs[i]=(refs[i][0]+np.clip((target-actual)*self.tracking_gain,-.012,.012),refs[i][1])
        return refs

    def description(self):return {**super().description(),'stride_m':self.stride,'landing_references':self.landings}
