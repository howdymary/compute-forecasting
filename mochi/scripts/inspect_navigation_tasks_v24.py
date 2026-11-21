"""Static task-pose checks only; no physical rollout or training claim."""
import hashlib
import argparse
import copy
import math
import json
from pathlib import Path
import time

from mochi.balanced.sequence import PhysicalStop
from mochi.navigation_tasks_v24.world import RelativeTaskWorld
from mochi.navigation_tasks_v24.approaches import candidate_approach
from mochi.navigation_tasks_v24.approaches import task_pose
import mujoco

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--id', required=True)
args = parser.parse_args()
assert args.id.replace('-', '').isalnum()
out = ROOT / 'artifacts/navigation-tasks-v24' / (args.id + '.json')
assert not out.exists()
out.parent.mkdir(parents=True, exist_ok=True)
layouts = json.loads((ROOT / 'configs/navigation-v23/development.json').read_text())
report = {'scope': 'Static development geometry from neutral reset posture. No dynamics or reachable-task-success claim.',
    'approach_source_sha256': hashlib.sha256((ROOT / 'src/mochi/navigation_tasks_v24/approaches.py').read_bytes()).hexdigest(), 'cases': []}
for index, layout in enumerate(layouts):
    w = RelativeTaskWorld(layout, 231000, False)
    for task in ['drawer', 'laptop', 'globe']:
        started = time.perf_counter()
        # These are explicit hypothetical station starts for static checking,
        # not claimed physical arrivals. Dynamics is validated separately.
        origin = [-.375, -.235, -math.pi / 2] if task == 'drawer' else w.station_goal('drawer' if task == 'laptop' else 'laptop')
        proxy = copy.copy(w)
        proxy.d = copy.copy(w.d)
        proxy.d.qpos[:2] = origin[:2]
        proxy.d.qpos[3:7] = [math.cos(origin[2] / 2), 0., 0., math.sin(origin[2] / 2)]
        mujoco.mj_forward(w.m, proxy.d)
        goal, reason, staging = proxy.station_goal(task), None, None
        try:
            goal = task_pose(proxy, task)
            staging = candidate_approach(proxy, goal)
        except PhysicalStop as error:
            reason = str(error)
        row = {'layout_sha256': layout['layout_sha256'], 'task': task, 'goal': goal,
            'staging': staging, 'static_feasible': staging is not None, 'reason': reason,
            'wall_seconds': time.perf_counter() - started, 'physics_steps': 0,
            'hypothetical_previous_station_pose': origin}
        report['cases'].append(row)
        out.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'index': index, 'task': task, 'static_feasible': row['static_feasible'], 'reason': reason}), flush=True)
