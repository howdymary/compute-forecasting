"""Export the unchanged physical scene for the isolated IK reference worker."""
import hashlib
import json
from pathlib import Path

import mujoco

from mochi.paperfree_v19.world import PaperfreeWorld

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/visual-motion-v22'
assert mujoco.__version__ == '3.3.7'
OUT.mkdir(parents=True, exist_ok=True)
target = OUT / 'reference-model.xml'
if target.exists():
    print('Preserved existing IK model:', hashlib.sha256(target.read_bytes()).hexdigest())
else:
    world = PaperfreeWorld(225000, False)
    assert world.d.time == 0
    mujoco.mj_saveLastXML(str(target), world.m)
    print(json.dumps({'model_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
        'source': 'Unstepped, unchanged PaperfreeWorld', 'mujoco': mujoco.__version__}))
