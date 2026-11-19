"""Bounded actuator-level touchdown search; never edits an object or root."""
import numpy as np
from ..richdesk.terrain import PlannedTerrainWalker


class LandingWalker(PlannedTerrainWalker):
    label='planned-footsteps-with-measured-touchdown-search'
    def __init__(self,*args,**kwargs):
        self.landing_search=[];self.landing_depth=0.
        super().__init__(*args,**kwargs)

    def solve(self,root,feet,yaw):
        targets=[np.asarray(p).copy() for p in feet]
        if self.stage=='land' and not self.w.foot_touching(['left','right'][self.swing]):
            age=max(0.,float(self.d.time)-self.stage_t)
            self.landing_depth=min(.002,.001*age)
            targets[self.swing][2]-=self.landing_depth
            if not self.landing_search or self.d.time-self.landing_search[-1]['t']>.05:
                self.landing_search.append({'t':float(self.d.time),'step':self.steps,'depth_m':self.landing_depth,
                    'loads_n':self.w.loads()})
        else:self.landing_depth=0.
        return super().solve(root,targets,yaw)

    def description(self):return {**super().description(),'landing_search':self.landing_search}


from .reachable import ReachableMixin

class ReachableLandingWalker(ReachableMixin,LandingWalker):
    label='reachable-footsteps-with-measured-touchdown-search'
    def start_shift(self,velocity):
        if self.steps==0:return LandingWalker.start_shift(self,velocity)
        return super().start_shift(velocity)
