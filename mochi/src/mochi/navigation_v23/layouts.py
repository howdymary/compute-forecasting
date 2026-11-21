"""Meaningful scene variations, with separate deterministic split generators."""
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def generate(seed, partition, index):
    rng = np.random.default_rng(seed)
    scene = json.loads((ROOT / 'configs/richdesk-v19-paperfree.json').read_text())
    scene['version'] = 'navigation-v23-state-based'
    scene['initial_pose'] = [-.43 + float(rng.uniform(-.015, .015)), -.25 + float(rng.uniform(-.015, .015)), 0.]
    # Distinct blocked corridors and assembly placements, not seed-only changes.
    family = index % 4
    printer = [float(rng.uniform(.035, .16)), [-.045, -.115, -.025, -.085][family] + float(rng.uniform(-.012, .012)), 0.]
    if partition.startswith('final') and family == 1:
        # The original entry-blocked combination also closed the lower route.
        # Keep the alternate corridor open before sealing any evaluation set.
        printer[1] += .070
    mug_family = (family + 1) % 4 if partition.startswith('final') else family
    mug = [[.10, .12], [.12, -.305], [-.12, -.15], [.31, .055]][mug_family]
    mug = [mug[0] + float(rng.uniform(-.045, .045)), mug[1] + float(rng.uniform(-.025, .025)), 0.]
    shift_x = float(rng.uniform(-.035, .035))
    scene['station_offsets'] = {
        'drawer-cabinet': [shift_x, .15, 0.], 'drawer': [shift_x, .15, 0.],
        'laptop-base': [-shift_x, .13, 0.], 'laptop-screen': [-shift_x, .13, 0.],
        'globe-base': [float(rng.uniform(-.025, .025)), .43, 0.],
    }
    scene['station_offsets']['globe'] = scene['station_offsets']['globe-base'].copy()
    # Preserve the printed-paper/tray assembly's displacement with the printer.
    delta = np.asarray(printer) - [.435, .29, 0.]
    for prop in scene['props']:
        if prop['name'] in ['printer', 'printer-output-tray', 'printer-printout']:
            prop['pos'] = (np.asarray(prop['pos']) + delta).tolist()
        elif prop['name'] == 'coffee-mug':
            prop['pos'] = mug
        elif prop['name'] == 'spiral-notebook':
            prop['pos'] = [-.43, .285, .015]
        elif prop['asset'] in ['pen', 'pencil', 'glasses']:
            prop['pos'] = [-.45 + float(rng.uniform(-.045, .045)), .28 + float(rng.uniform(-.025, .025)), .023]
        elif prop['name'].startswith('loose-page'):
            prop['pos'] = [-.43, .29, .022]
        if prop.get('title') == 'FIELD NOTES':
            prop['title'] = 'ROBOTICS'
    headings = [0., math.pi / 2, -math.pi / 2] if partition.startswith('final') else [0., math.pi / 2]
    goal = [float(rng.uniform(.40, .46)), float(rng.uniform(-.23, -.15)), headings[index % len(headings)]]
    layout = {'scene': scene, 'goal': goal, 'generation_seed': seed, 'partition': partition,
        'index': index, 'family': ['upper-mouth', 'lower-mouth', 'entry-obstruction', 'exit-obstruction'][family],
        'scope': 'Phase A flat navigation; existing 8 mm book steps remain obstacles. Height/traversal variants require a separate validated gate.'}
    layout['layout_sha256'] = fingerprint({'scene': scene, 'goal': goal})
    return layout


def candidates(partition, count=8):
    offsets = {'engineering': 230000, 'training': 231000, 'development': 232000,
        'final_navigation': 233000, 'final_sequence': 234000}
    for index in range(count):
        yield generate(offsets[partition] + index * 101, partition, index)
