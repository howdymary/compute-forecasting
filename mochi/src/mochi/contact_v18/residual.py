"""Contact-gated, rate-limited swing-foot lift through leg actuator targets.

The native network stays fixed. Residuals are joint references, never body
positions. Small station-alignment commands use the original gait so braking
and support capture do not compete with added swing clearance.
"""
import math
import mujoco
import numpy as np
from ..balanced.onnx_walk import HubWalker

class LiftedHubWalker(HubWalker):
    def command(self,velocity):
        super().command(velocity)
        if not hasattr(self,'lift_started'):
            self.lift_started={'left':None,'right':None};self.lift_delta={s:np.zeros(6) for s in self.lift_started}
            self.lift_calls=0;self.last_lift_t=float(self.d.time)
        dt=max(0.,min(.01,float(self.d.time)-self.last_lift_t));self.last_lift_t=float(self.d.time)
        loads=self.w.loads()
        moving=self.mode=='walk' and (abs(velocity[0])>=.020 or abs(velocity[2])>=.20)
        for i,side in enumerate(['left','right']):
            other='right' if side=='left' else 'left';requested=np.zeros(6)
            if not moving or loads[side]>.20:self.lift_started[side]=None
            elif loads[other]>=.65:
                if self.lift_started[side] is None:self.lift_started[side]=float(self.d.time)
                u=(float(self.d.time)-self.lift_started[side])/.12
                if 0<u<1:
                    lift=getattr(self.w,'swing_lift_reference',.006)*math.sin(math.pi*u)**2
                    forward=getattr(self.w,'swing_forward_reference',0.)*(u*u*(3-2*u)) if abs(velocity[0])>=.020 else 0.
                    b=self.w.id('body',side+'_ankle_roll_link')
                    point=self.d.xpos[b]+self.d.xmat[b].reshape(3,3)@np.array([.0058,0,-.00585])
                    J=np.zeros((3,self.m.nv));mujoco.mj_jac(self.m,self.d,J,None,point,b)
                    A=J[:,self.vids[i*6:(i+1)*6]];direction=self.d.xmat[1].reshape(3,3)[:,0]
                    requested=A.T@np.linalg.solve(A@A.T+np.eye(3)*1e-7,np.array([0.,0.,lift])+direction*forward)
                    limit=getattr(self.w,'swing_joint_residual_limit',.10);requested=np.clip(requested,-limit,limit)
                    self.lift_calls+=1
            self.lift_delta[side]+=np.clip(requested-self.lift_delta[side],-2.*dt,2.*dt)
            for j,a in enumerate(self.aids[i*6:(i+1)*6]):
                index=self.amap.index(int(a))
                self.d.ctrl[a]=np.clip(self.d.ctrl[a]+self.kp[index]*self.lift_delta[side][j],*self.m.actuator_forcerange[a])

    def description(self):
        return {**super().description(),'swing_clearance_residual':{
                'command_peak_m':getattr(self.w,'swing_lift_reference',.006),
                'forward_reference_m':getattr(self.w,'swing_forward_reference',0.),
                'period_s':.12,'requires_other_foot_load_n':.65,'joint_reference_rate_rad_s':2.,
                'max_joint_residual_rad':getattr(self.w,'swing_joint_residual_limit',.10),
                'calls':getattr(self,'lift_calls',0),'weights_trained':False}}
