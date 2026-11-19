"""Full four-task physical reference with forward-facing flat-desk travel."""
import argparse
import hashlib
import json
import math
import pickle
import shutil
import time
from pathlib import Path

from ..curriculum.world import PROFILES, TASKS
from ..balanced.onnx_walk import HubWalker, HoldWalker
from ..balanced.sequence import PhysicalStop, navigate as clearance_move
from ..balanced.recovery import RECOVERIES, recover
from ..control_v8.manipulation import PRESSES
from ..control_v8.verification import full_success
from ..terrain_v12.sequence import book_leg, prepare_flat_walking
from ..terrain_v12.legs import BASE, WALKS
from ..terrain_v12.tasks import press_alarm
from ..terrain_v12.development import state, restore
from .navigation import navigate, NavigationParameters, travel_metrics
from .probe import NavigationWorld, OUT, reserve, finish


def leg(w, task, code='W0', nav_parameters=None):
    p = {**BASE, **WALKS[code]}
    speed = p.pop('flat_speed')
    arrivals = []
    if task == 'alarm':
        return [book_leg(w, 1, p)]
    if task == 'drawer':
        arrivals += [book_leg(w, -1, p), prepare_flat_walking(w, p)]
        points = [(-.19, -.18, 0.), (-.19, -.03, math.pi/2),
                  (-.13, -.03, 0.), (-.13, .02, math.pi/2)]
    elif task == 'laptop':
        points = [(.08, .02, 0.), (.08, -.055, -math.pi/2),
                  (.30, -.055, 0.), (.30, .02, math.pi/2), (.305, .155, math.pi/2)]
    elif task == 'globe':
        # A short, physically executed clearance step keeps the turn's foot
        # sweep clear of the laptop edge. Long transit then faces forward.
        row = clearance_move(w, (.32, .105, math.pi/2), timeout=20., speed=.035,
                             position_tolerance=.012, label='laptop-clearance')
        arrivals.append(row)
        points = [(.32, .02, -math.pi/2), (.32, -.145, -math.pi/2), (.35, -.145, 0.)]
    else:
        raise ValueError(task)
    for index, point in enumerate(points):
        arrivals.append(navigate(w, point, stop=index == len(points)-1, speed=speed,
            label=task+('-station' if index == len(points)-1 else '-corridor-'+str(index)),
            parameters=nav_parameters))
    return arrivals


def run(ident, seed=41001, nav_parameters=None, resume=None, until='all', laptop='P0'):
    if resume:
        path = OUT / 'states' / resume
        with path.open('rb') as stream:
            saved = pickle.load(stream)  # only this project's saved simulator state
        w = restore(saved, record=True)
        w.__class__ = NavigationWorld
        start_task = TASKS.index(resume.rsplit('-', 1)[-1].replace('.pickle', '')) + 1
        w.frames = []
        w.capture()
        w.direction_samples = []
        w.next_direction_sample = float(w.d.time)
    else:
        w = NavigationWorld(seed, True)
        w.terrain_controller_history = []
        w.use_native_stand = True
        while w.d.time < .4:
            w.step(standing=True)
        w.walker = HubWalker(w)
        w.walker = HoldWalker(w)
        start_task = 0
    arrivals, failure = [], None
    started = time.perf_counter()
    try:
        for task in TASKS[start_task:]:
            arrivals += leg(w, task, nav_parameters=nav_parameters)
            code = {'alarm': 'F', 'drawer': 'B', 'laptop': laptop, 'globe': 'A'}[task]
            profile = next(p for p in (PRESSES if task == 'laptop' else PROFILES) if p.code == code)
            result = press_alarm(w, profile) if task == 'alarm' else w.do_task(task, profile)
            print(json.dumps({'task': result}), flush=True)
            if not result['success']:
                raise PhysicalStop('task-failed:' + task)
            recovery = recover(w, task, next(r for r in RECOVERIES if r.code == ('R1' if task == 'alarm' else 'R0')))
            if not recovery['success']:
                raise PhysicalStop('recovery-failed:' + task)
            directory = OUT / 'states'
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / (ident + '-' + task + '.pickle')
            assert not path.exists(), 'Preserve saved supported state'
            path.write_bytes(pickle.dumps(state(w, include_history=False)))
            if until == task:
                break
        end = float(w.d.time) + .5
        while w.d.time < end:
            w.step()
    except PhysicalStop as exc:
        failure = str(exc)
    episode = w.episode()
    complete = (not resume and until == 'all' and failure is None and full_success(episode)
        and not w.invalid_contact and episode['maximum_applied_base_force'] == 0
        and len(w.recoveries) == 4 and all(r['success'] for r in w.recoveries)
        and all(w.foot_touching(side) for side in ['left', 'right'])
        and any(a['label'] == 'book-ascent' for a in arrivals)
        and any(a['label'] == 'book-descent' for a in arrivals))
    return {'study': 'mochi-directional-v14', 'seed': seed,
        'scope': 'Navigation engineering with fixed native gait and task profiles; zero new Tinker updates. '+('Diagnostic continuation from a saved supported state; not a full sequence.' if resume else 'One uninterrupted physical episode.'),
        'complete_sequence_success': bool(complete), 'failure': failure, 'resume_source': resume,
        'navigation_parameters': vars(nav_parameters or NavigationParameters()),
        'arrivals': arrivals, 'episode': episode, 'direction_samples': w.direction_samples,
        'direction_metrics': travel_metrics(w.direction_samples),
        'book_descent': 'validated backward contact controller; flat-desk travel turns toward the path',
        'wall_seconds': time.perf_counter()-started}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--id', required=True)
    p.add_argument('--seed', type=int, default=41001)
    p.add_argument('--parameters', default='{}')
    p.add_argument('--resume')
    p.add_argument('--until', choices=[*TASKS, 'all'], default='all')
    p.add_argument('--laptop', choices=['P0', 'P1', 'P2'], default='P0')
    args = p.parse_args()
    reserve(args.id, vars(args))
    sources = {str(p.relative_to(Path(__file__).parent)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in Path(__file__).parent.glob('*.py')}
    directory = OUT / 'source' / args.id
    directory.mkdir(parents=True, exist_ok=False)
    for path in Path(__file__).parent.glob('*.py'):
        shutil.copy2(path, directory / path.name)
    start = time.perf_counter()
    try:
        row = run(args.id, args.seed, NavigationParameters(**json.loads(args.parameters)), args.resume, args.until, args.laptop)
        row['source_sha256'] = sources
        (OUT / (args.id+'.json')).write_text(json.dumps(row, separators=(',', ':')))
        result = {'status': 'completed', 'complete': row['complete_sequence_success'], 'failure': row['failure'],
            'wall_seconds': row['wall_seconds'], 'duration_s': row['episode']['duration'], 'direction_metrics': row['direction_metrics']}
        finish(args.id, result)
        print(json.dumps(result), flush=True)
    except Exception as exc:
        finish(args.id, {'status': 'failed', 'error': type(exc).__name__, 'wall_seconds': time.perf_counter()-start})
        raise


if __name__ == '__main__':
    main()
