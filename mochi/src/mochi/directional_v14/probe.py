"""Small, bounded physical turn/corner probes before a full route change."""
import argparse
import fcntl
import hashlib
import json
import math
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from ..curriculum.world import ROOT
from ..richdesk.world import scene_spec
from ..terrain_v12.world import TerrainWorld
from ..balanced.onnx_walk import HubWalker, HoldWalker
from ..balanced.sequence import PhysicalStop, average_velocity, navigate as holonomic
from .navigation import navigate, NavigationParameters, travel_metrics

OUT = ROOT / 'artifacts/directional-v14'


@contextmanager
def ledger():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'ledger.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = OUT / 'ledger.json'
        data = json.loads(path.read_text()) if path.exists() else {'local_rollouts': 0, 'attempts': {}}
        yield data
        path.write_text(json.dumps(data, indent=2) + '\n')


def reserve(ident, parameters):
    with ledger() as data:
        assert ident not in data['attempts'], 'Preserve the previous attempt'
        assert data['local_rollouts'] < 20, 'Direction-controller engineering rollout cap'
        assert sum(r.get('wall_seconds', 0) for r in data['attempts'].values()) < 5400, 'Engineering time cap'
        data['local_rollouts'] += 1
        data['attempts'][ident] = {'status': 'reserved', 'parameters': parameters}


def finish(ident, row):
    with ledger() as data:
        data['attempts'][ident].update(row)


class NavigationWorld(TerrainWorld):
    def __init__(self, *args, **kwargs):
        self.direction_samples = []
        self.next_direction_sample = 0.
        super().__init__(*args, **kwargs)

    def step(self, *args, **kwargs):
        super().step(*args, **kwargs)
        if self.d.time >= self.next_direction_sample:
            self.direction_samples.append({'t': float(self.d.time),
                'phase': 'turn-to-path' if self.phase == 'turn' else 'walk-forward',
                'native_walk': isinstance(self.walker, HubWalker) and self.walker.mode == 'walk',
                'yaw_rad': self.yaw(), 'root': self.d.qpos[:3].tolist(),
                'cycle_averaged_velocity_xy': average_velocity(self, .25).tolist()})
            self.next_direction_sample = float(self.d.time) + .04


def run(mode='corner', baseline=False, seed=81000, parameters=None):
    scene = scene_spec()
    scene['initial_pose'] = [-.19, -.18, math.pi / 2]
    w = NavigationWorld(seed, True, scene=scene)
    w.use_native_stand = True
    while w.d.time < .4:
        w.step(standing=True)
    w.walker = HubWalker(w)
    w.walker = HoldWalker(w)
    start_xy = w.d.qpos[:2].copy()
    initial_yaw = w.yaw()
    goals = [(*start_xy, 0.)] if mode == 'turn' else [(*start_xy, math.pi)] if mode == 'left' else [
        (-.19, -.03, math.pi / 2), (-.13, -.03, math.pi / 2), (-.13, .02, math.pi / 2)]
    arrivals, failure = [], None
    started = time.perf_counter()
    parameters = vars(NavigationParameters(**(parameters or {})))
    try:
        for index, goal in enumerate(goals):
            options = {'stop': index == len(goals) - 1, 'position_tolerance': .012,
                       'label': 'direction-probe-' + str(index), 'timeout': 45.}
            if not baseline:
                options['parameters'] = NavigationParameters(**parameters)
            arrivals.append((holonomic if baseline else navigate)(w, goal, **options))
    except PhysicalStop as exc:
        failure = str(exc)
    episode = w.episode()
    return {'study': 'mochi-directional-v14', 'scope': 'Isolated navigation engineering probe, not a seamless task result or trained gain',
        'seed': seed, 'mode': mode, 'baseline': baseline, 'parameters': parameters or {},
        'success': failure is None, 'failure': failure, 'arrivals': arrivals, 'episode': episode,
        'initial_yaw': initial_yaw, 'final_yaw': w.yaw(), 'root_displacement_m': float(np.linalg.norm(w.d.qpos[:2] - start_xy)),
        'direction_metrics': travel_metrics(w.direction_samples), 'direction_samples': w.direction_samples,
        'wall_seconds': time.perf_counter() - started}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--id', required=True)
    p.add_argument('--mode', choices=['turn', 'left', 'corner'], default='corner')
    p.add_argument('--baseline', action='store_true')
    p.add_argument('--seed', type=int, default=81000)
    p.add_argument('--parameters', default='{}')
    args = p.parse_args()
    reserve(args.id, vars(args))
    started = time.perf_counter()
    source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    try:
        row = run(args.mode, args.baseline, args.seed, json.loads(args.parameters))
        row['source_sha256'] = source_hashes
        (OUT / (args.id + '.json')).write_text(json.dumps(row, separators=(',', ':')))
        result = {k: row[k] for k in ['success', 'failure', 'initial_yaw', 'final_yaw', 'root_displacement_m', 'direction_metrics', 'wall_seconds']}
        finish(args.id, {'status': 'completed', **result})
        print(json.dumps(result), flush=True)
    except Exception as exc:
        finish(args.id, {'status': 'failed', 'error': type(exc).__name__, 'wall_seconds': time.perf_counter() - started})
        raise


if __name__ == '__main__':
    main()
