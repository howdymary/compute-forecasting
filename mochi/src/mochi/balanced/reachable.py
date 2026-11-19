"""Select reachable support-transfer poses inside the stance-foot region.

All searches use detached IK data. The output is a controller reference, not
an assignment to the physical floating base or feet.
"""
import math
import mujoco
import numpy as np
from ..richdesk.terrain import PlannedTerrainWalker
from .inverse import PlannedContactInverseWalker


class ReachableMixin:
    def start_shift(self,velocity):
        super().start_shift(velocity)
        if not hasattr(self,'reachability'):self.reachability=[]
        stance=1-self.swing;anchor=self.anchors[stance];best=None
        original=self.joint_target.copy();candidates=[]
        # Lateral offsets stay inside the actual narrow foot-pad support.
        # A slight rearward target preserves trailing-leg reach on ascent.
        for lateral in [-.0035,-.0025,.0025,.0035]:
            for forward in [-.010,-.006,-.002]:
                target=anchor+self.rotation@np.array([forward,lateral,0.])
                root=target-self.rotation@self.com_offset
                root[2]=self.base_clearance+min(a[2] for a in self.anchors)
                self.joint_target=original.copy()
                for _ in range(4):
                    self.joint_target=self.solve(root,self.anchors,self.yaw_goal)
                    mujoco.mj_forward(self.m,self.scratch)
                    root[:2]+=np.clip(target[:2]-self.scratch.subtree_com[1,:2],-.004,.004)
                self.joint_target=self.solve(root,self.anchors,self.yaw_goal);mujoco.mj_forward(self.m,self.scratch)
                error=max(float(np.linalg.norm(self.anchors[i]-(self.scratch.xpos[b]+self.scratch.xmat[b].reshape(3,3)@self.local))) for i,b in enumerate(self.feet))
                angles=self.scratch.qpos[self.qids];margin=float(np.min(np.minimum(angles-self.limits[:,0],self.limits[:,1]-angles)))
                com=self.scratch.subtree_com[1].copy();local=self.rotation[:2,:2].T@(com[:2]-anchor[:2])
                inside=abs(local[0])<.011 and abs(local[1])<.004
                valid=error<.0005 and margin>.025 and inside
                score=abs((self.rotation.T@(root-np.mean(self.anchors,axis=0)))[1])+abs(forward)*.1+error*20
                row={'foot_error_m':error,'joint_margin_rad':margin,'support_local_m':local.tolist(),'valid':bool(valid),'root':root.tolist()};candidates.append(row)
                if valid and (best is None or score<best[0]):best=(score,root.copy(),com.copy(),self.joint_target.copy(),row)
        self.joint_target=original
        if best is not None:
            _,self.root_goal,self.com_goal,_,chosen=best
        else:
            chosen=None;self.failed_reason='no_reachable_support_pose'
        self.reachability.append({'t':float(self.d.time),'step':self.steps,'chosen':chosen,'candidates':candidates})

    def description(self):return {**super().description(),'reachability':getattr(self,'reachability',[])}


class ReachableWalker(ReachableMixin,PlannedTerrainWalker):
    label='reachable-support-transfer-and-actuated-footsteps'


class ReachableInverseWalker(ReachableMixin,PlannedContactInverseWalker):
    label='reachable-support-transfer-and-contact-inverse-servo'
