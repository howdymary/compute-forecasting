"""Slow contact-gated stepping using the supported-stance torque servo."""
import math
import mujoco,numpy as np
from ..richdesk.stepping import FootstepController,StepParameters


class QuasiWalker(FootstepController):
    label='contact-gated-steps-with-supported-stance-servo'
    def __init__(self,w,crouch=.012,gain=6.,shift=1.2,stride=.025,landings=None):
        super().__init__(w,StepParameters(crouch=crouch,shift_seconds=shift,stride=stride))
        self.gain=gain;self.landings=landings

    def start_shift(self,velocity):
        super().start_shift(velocity)
        if self.landings and self.steps<len(self.landings):
            self.swing_goal=np.array(self.landings[self.steps]['position'],dtype=float)
            self.phase_log[-1]['target']=self.swing_goal.tolist()

    def command(self,velocity):
        # The parent generates only kinematic references and provisional
        # torques. Replace those torques before the next physical step.
        super().command(velocity)
        d=self.d;m=self.m
        kp=np.array([100,100,100,150,40,40]*2)*self.scale**4*self.gain
        kd=np.array([2,2,2,4,2,2]*2)*self.scale**4.5*self.gain
        tau=kp*(self.target-d.qpos[self.qids])-kd*d.qvel[self.vids]+d.qfrc_bias[self.vids]
        R=d.xmat[1].reshape(3,3);error=R.T@(d.subtree_com[1]-self.com_target)
        pitch=math.asin(float(np.clip(-R[2,0],-1,1)));roll=math.atan2(R[2,1],R[2,2]);mass=m.body_subtreemass[1]
        load=self.w.loads();total=max(sum(load.values()),.001)
        for i,side in enumerate(['left','right']):
            weight=load[side]/total
            tau[6*i+4]+=weight*(mass*9.81*error[0]+.22*pitch+.012*d.qvel[4])
            tau[6*i+5]+=weight*(-mass*9.81*error[1]+.22*roll+.012*d.qvel[3])
        limits=m.actuator_forcerange[self.aids];d.ctrl[self.aids]=np.clip(tau,limits[:,0],limits[:,1])

    def description(self):return {**super().description(),'servo_gain':self.gain,'native_weights_trained':False}
