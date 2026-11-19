"""Contact-consistent diagnostic servo; only leg actuator torques are applied.

MuJoCo's inverse contact model solves the floating-base acceleration that
requires zero external base force. Scratch state is never copied to physics.
"""
import mujoco
import numpy as np
from ..richdesk.stepping import FootstepController


class ContactInverseWalker(FootstepController):
    label='mujoco-contact-inverse-servo'

    def __init__(self,world,parameters=None):
        super().__init__(world,parameters)
        self.inverse=mujoco.MjData(self.m);self.last_inverse=-1.;self.torque=np.zeros(12)
        self.inverse_log=[]

    def command(self,velocity):
        super().command(velocity)
        self.servo()

    def servo(self):
        m,d,s=self.m,self.d,self.inverse
        if d.time-self.last_inverse<.004:
            d.ctrl[self.aids]=self.torque;return
        self.last_inverse=float(d.time)
        s.qpos[:]=d.qpos;s.qvel[:]=d.qvel;s.qacc[:]=d.qacc
        s.qacc[self.vids]=np.clip(160*(self.target-d.qpos[self.qids])-24*d.qvel[self.vids],-600,600)
        mujoco.mj_inverse(m,s)
        for iteration in range(6):
            f=s.qfrc_inverse[:6].copy()
            if np.linalg.norm(f)<1e-6:break
            base=s.qacc[:6].copy();A=np.zeros((6,6));h=.001
            for j in range(6):
                s.qacc[:6]=base;s.qacc[j]+=h
                mujoco.mj_inverseSkip(m,s,mujoco.mjtStage.mjSTAGE_VEL,1)
                A[:,j]=(s.qfrc_inverse[:6]-f)/h
            update=np.linalg.lstsq(A,-f,rcond=1e-9)[0]
            s.qacc[:6]=base+np.clip(update,-100,100)
            mujoco.mj_inverseSkip(m,s,mujoco.mjtStage.mjSTAGE_VEL,1)
        limits=m.actuator_forcerange[self.aids]
        desired=s.qfrc_inverse[self.vids]-d.qfrc_applied[self.vids]
        self.torque=np.clip(desired,limits[:,0],limits[:,1]);d.ctrl[self.aids]=self.torque
        if not self.inverse_log or d.time-self.inverse_log[-1]['t']>.1:
            self.inverse_log.append({'t':float(d.time),'virtual_base_residual':float(np.linalg.norm(s.qfrc_inverse[:6])),
                'torque_clipped':bool(np.any(abs(desired-self.torque)>1e-6)),'iterations':iteration+1})

    def description(self):return {**super().description(),'inverse_log':self.inverse_log}


class PlannedContactInverseWalker(ContactInverseWalker):
    def __init__(self,world,landings,parameters=None):
        self.landings=landings
        super().__init__(world,parameters)

    def start_shift(self,velocity):
        super().start_shift(velocity)
        if self.steps<len(self.landings):
            landing=self.landings[self.steps]
            self.swing_goal=np.array(landing['position'],dtype=float);self.swing_goal[2]-=.00015
            self.phase_log[-1]['target']=self.swing_goal.tolist()
