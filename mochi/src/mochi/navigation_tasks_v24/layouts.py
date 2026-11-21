"""Explicit task-layout revision with articulated-object workspace checks."""
import copy
import math

import mujoco
import numpy as np

from mochi.navigation_v23.layouts import fingerprint


def task_layout(original):
    layout = copy.deepcopy(original)
    layout['parent_navigation_layout_sha256'] = original['layout_sha256']
    scene = layout['scene']
    scene['version'] = 'navigation-tasks-v24-workspace-r1'
    # The original navigation generator did not require an unobstructed lid
    # sweep. Put this existing desk object on the reference notebook at reset.
    stapler = next(p for p in scene['props'] if p['name'] == 'stapler')
    stapler['pos'] = [-.47, .335, .022]
    scene['task_workspace_revision'] = 'Stapler on notebook, outside the relocated laptop closing volume.'
    layout['layout_sha256'] = fingerprint({'scene': scene, 'goal': layout['goal']})
    return layout


def articulated_workspace(w):
    """Geometric check on scratch data. No physical world state is advanced."""
    scratch = copy.copy(w.d)
    rejected = []
    targets = [('laptop', np.linspace(0., math.pi / 2, 91)),
        ('drawer', np.linspace(0., .033, 18))]
    for task, values in targets:
        for value in values:
            scratch.qpos[:] = w.d.qpos
            scratch.qpos[w.q[task]] = value
            mujoco.mj_forward(w.m, scratch)
            for contact in scratch.contact:
                ids = [int(contact.geom1), int(contact.geom2)]
                names = [mujoco.mj_id2name(w.m, mujoco.mjtObj.mjOBJ_GEOM, i) or '' for i in ids]
                if task + '-contact' not in names or contact.dist >= -.0001:
                    continue
                index = names.index(task + '-contact')
                other = ids[1-index]
                if int(w.m.geom_bodyid[other]) in w.robot_bodies:
                    continue  # Station approach/arm checks are separate.
                name = names[1-index]
                if task == 'laptop' and name == 'laptop-base-contact':
                    continue
                if task == 'drawer' and (name.startswith('cabinet-') or name.startswith('drawer-')):
                    continue
                rejected.append({'task': task, 'joint_position': float(value), 'fixture': name,
                    'penetration_m': float(-contact.dist)})
    return {'valid': not rejected, 'rejections': rejected,
        'scope': 'One-degree laptop and approximately two-millimetre drawer geometric samples; not dynamic manipulation success or continuous collision certification.'}
