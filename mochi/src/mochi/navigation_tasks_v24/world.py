"""Object-relative hand targets; no change to mechanics or task verification."""
import math
import numpy as np
import mujoco

from mochi.curriculum.world import PAD_RADIUS
from mochi.navigation_v23.world import NavigationWorld
from mochi.paperfree_v19.world import PaperfreeWorld


class RelativeTaskWorld(NavigationWorld):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # mj_setConst in the layout adapter resets generalized coordinates to
        # qpos0. Restore the sampled original physical initialization, once at
        # reset, after constants are rebuilt. The frozen Phase A remains intact.
        initial = PaperfreeWorld(self.s['seed'], False, scene=self.layout['scene'])
        fields = mujoco.mjtState.mjSTATE_FULLPHYSICS | mujoco.mjtState.mjSTATE_CTRL
        saved = np.empty(mujoco.mj_stateSize(initial.m, fields))
        mujoco.mj_getState(initial.m, initial.d, saved, fields)
        mujoco.mj_setState(self.m, self.d, saved, fields)
        mujoco.mj_forward(self.m, self.d)
        self.initialization_revision = 'task-v24-r1: preserve sampled generalized state after static layout rebuild'
        self.frames = []
        self.capture()
        self.task_poses = {}

    def hand_target(self, task, phase):
        if task not in ['drawer', 'globe']:
            return super().hand_target(task, phase)
        hover = phase in ['approach', 'hover', 'release']
        if task == 'drawer':
            normal = np.array([0., -1., 0.])
            point = self.d.xpos[self.id('body', 'drawer')] + [.008, 0., .010]
            return point + normal * (.0025 + PAD_RADIUS + (.014 if hover else -self.profile.depth)), normal
        normal = np.array([math.cos(self.stroke), math.sin(self.stroke), 0.])
        point = self.d.xpos[self.id('body', 'globe')]
        target = point + normal * (.058 + PAD_RADIUS + (.014 if hover else -self.profile.depth))
        if phase == 'hold' and self.hold_pose is not None:
            target = self.hold_pose.copy()
        if phase == 'release':
            target[2] += .012
        return target, normal

    def laptop(self, profile, horizon):
        from .relative_laptop import adaptive_laptop
        return adaptive_laptop(self, profile, horizon)

    def station_goal(self, task):
        if task in self.task_poses:
            return self.task_poses[task]
        if task == 'drawer':
            p = self.d.xpos[self.id('body', 'drawer-cabinet')]
            return [float(p[0] - .030), float(p[1] - .130), math.pi / 2]
        if task == 'laptop':
            p = self.d.xpos[self.id('body', 'laptop-base')]
            return [float(p[0] + .175), float(p[1] - .015), math.pi / 2]
        if task == 'globe':
            p = self.d.xpos[self.id('body', 'globe-base')]
            # Reach with the right arm from southwest; avoid a ninety-degree
            # turn immediately beside the globe after leaving the laptop.
            return [float(p[0] - .120), float(p[1] - .040), math.pi / 3]
        return [-.375, .040, math.pi / 2]
