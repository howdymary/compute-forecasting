"""Continuous physics with ordinary desk walking between drawer and laptop."""
import time

from ..balanced.onnx_walk import HubWalker, HoldWalker
from ..balanced.sequence import PhysicalStop
from ..control_v8.verification import full_success
from ..curriculum.world import TASKS
from ..smooth_v16.policy import WALKS
from ..smooth_v16.terrain import clear_and_turn, forward_descent
from ..smooth_v16.navigation import travel_metrics
from ..terrain_v12.legs import BASE
from ..terrain_v12.sequence import book_leg
from .policy import choices, execute, fixed
from .world import PaperfreeWorld


def run(seed, record=True, choose=None, capture=None):
    w = PaperfreeWorld(seed, record)
    w.terrain_controller_history = []
    w.use_native_stand = True
    start = time.perf_counter()
    arrivals, failure = [], None
    try:
        while w.d.time < .4:
            w.step(standing=True)
        w.walker = HubWalker(w)
        w.walker = HoldWalker(w)
        for task in TASKS:
            if task == 'alarm':
                w.efficiency_segment = 'book_ascent'
                arrivals.append(book_leg(w, 1, {**BASE, **{k: v for k, v in WALKS['W2'].items() if k != 'flat_speed'}}))
            else:
                if task == 'drawer':
                    book_parameters = {**BASE, **{k: v for k, v in WALKS['W5'].items() if k != 'flat_speed'}}
                    arrivals.extend(clear_and_turn(w, book_parameters))
                    arrivals.extend(forward_descent(w, book_parameters))
                if capture:
                    capture(w, 'walk', task)
                action = (choose or fixed)(w, 'walk', task, 'W8', choices('walk', task))
                result = execute(w, 'walk', task, action)
                if not all(a['success'] for a in result):
                    raise PhysicalStop('walk-failed:' + task)
                arrivals.extend(result)
            for domain, default in [(task, {'alarm': 'H0', 'drawer': 'C', 'laptop': 'P4', 'globe': 'G0'}[task]), ('recovery', 'R4')]:
                if capture:
                    capture(w, domain, task)
                action = (choose or fixed)(w, domain, task, default, choices(domain, task))
                result = execute(w, domain, task, action)
                if not result['success']:
                    raise PhysicalStop(domain + '-failed:' + task)
        end = float(w.d.time) + .5
        while w.d.time < end:
            w.step()
    except PhysicalStop as exc:
        failure = str(exc)
    e = w.episode()
    complete = bool(not failure and full_success(e) and not w.invalid_contact and e['efficiency_validity']
        and e['maximum_applied_base_force'] == 0 and len(w.recoveries) == 4
        and all(r['success'] for r in w.recoveries) and all(w.foot_touching(s) for s in ['left', 'right'])
        and any(a['label'] == 'book-ascent' for a in arrivals)
        and any(a['label'] == 'book-top-turnaround' and a['success'] for a in arrivals)
        and any(a['label'] == 'book-forward-descent' for a in arrivals)
        and len(e['flat_legs']) == 3 and all(leg['success'] for leg in e['flat_legs'])
        and not e['paper_geometry_present'])
    return {'study': 'mochi-paperfree-v19', 'seed': seed, 'complete_sequence_success': complete,
            'failure': failure, 'arrivals': arrivals, 'episode': e, 'terrain_conditions': w.terrain_conditions,
            'direction_metrics': travel_metrics(w.direction_samples), 'wall_seconds': time.perf_counter() - start,
            'scope': 'Uninterrupted paper-free MuJoCo attempt. Fixed book controller; learned flat/task/recovery selection only when supplied by caller.'}
