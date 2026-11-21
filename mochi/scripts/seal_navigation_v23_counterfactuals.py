"""Geometry-only diagnostic pairs, sealed before trained checkpoints are seen."""
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from mochi.navigation_v23.engine import inspect
from mochi.navigation_v23.layouts import fingerprint

root = Path(__file__).resolve().parents[1]
target = root / 'configs/navigation-v23-counterfactuals.json'
assert not target.exists(), 'Preserve diagnostic pairs'
development = json.loads((root / 'configs/navigation-v23/development.json').read_text())
pairs, rejected = [], []
for index in range(len(development)):
    base = copy.deepcopy(development[index])
    _, envelope, obstacles, plans = inspect(base, 231000)
    turn = plans['planner']['points'][1]
    for dx, dy in [(0, .04), (.03, .05), (-.03, .05), (.05, .08), (-.05, .08), (.07, 0), (-.07, 0), (.10, -.03), (-.10, -.03), (.12, 0), (-.12, 0)]:
        changed = copy.deepcopy(base)
        mug = next(p for p in changed['scene']['props'] if p['name'] == 'coffee-mug')
        mug['pos'] = [turn[0] + dx, turn[1] + dy, 0.]
        changed['partition'] = 'counterfactual-diagnostic'
        changed['layout_sha256'] = fingerprint({'scene': changed['scene'], 'goal': changed['goal']})
        w, _, obs, paths = inspect(changed, 231000)
        current = next(o for o in obs if o['name'] == 'coffee-mug-contact')
        a, b = np.asarray(current['minimum']), np.asarray(current['maximum'])
        overlaps = [o['name'] for o in obs if o['name'] != current['name']
            and np.all(np.minimum(b, o['maximum']) - np.maximum(a, o['minimum']) > .0005)]
        on_desk = bool(np.all(a[:2] >= [-.60, -.40]) and np.all(b[:2] <= [.60, .40]))
        valid = paths['planner']['feasible'] and not overlaps and on_desk
        route_changed = valid and fingerprint(paths['planner']['points']) != fingerprint(plans['planner']['points'])
        if valid and route_changed:
            pairs.append({'base': base, 'mug_in_turning_area': changed,
                'physics_seed': 231000, 'base_planner': plans['planner'], 'changed_planner': paths['planner'],
                'question': 'Does mug relocation change the chosen profile, the planner route, and physical execution? A planner reroute alone is not learned adaptation.'})
            break
        rejected.append({'base_development_index': index, 'offset': [dx, dy],
            'overlaps': overlaps, 'on_desk': on_desk, 'planner_feasible': paths['planner']['feasible'], 'route_changed': bool(route_changed)})
    (root / 'artifacts/navigation-v23/counterfactual-generation.json').write_text(json.dumps({'accepted_pairs': len(pairs), 'static_rejections': rejected}, indent=2) + '\n')
    if len(pairs) == 2:
        break
assert len(pairs) == 2, 'No two statically feasible counterfactual pairs; generation log preserved'
result = {'scope': 'Exploratory counterfactual diagnostic, not the unopened final cohort. Geometry-only selection before inspecting any trained checkpoint.',
    'pairs': pairs, 'static_rejections': rejected}
target.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'pairs': len(pairs), 'static_rejections': len(rejected), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}))
