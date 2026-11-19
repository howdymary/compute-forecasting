"""Predeclared stair landing plans tracked by contact-constrained actuation."""
import numpy as np
from .wholebody import WholeBodyWalker


class PlannedTerrainWalker(WholeBodyWalker):
    label='planned-stair-landings-with-inverse-dynamics'

    def __init__(self,world,landings,parameters=None):
        self.landings=landings
        super().__init__(world,parameters)

    def start_shift(self,velocity):
        super().start_shift(velocity)
        if self.steps>=len(self.landings):return
        p=self.landings[self.steps]
        assert ['left','right'][self.swing]==p['side']
        self.swing_goal=np.array(p['position'],dtype=float);self.swing_goal[2]-=.00015
        self.phase_log[-1]['target']=self.swing_goal.tolist()
