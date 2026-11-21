"""Isolated mink process: output bounded joint references, never step physics."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

import mink
import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / 'artifacts/visual-motion-v22/reference-model.xml'
model = mujoco.MjModel.from_xml_path(str(MODEL))
original_limited = model.jnt_limited.copy()


def plan(request):
    q0 = np.asarray(request['qpos'], dtype=float)
    active = np.asarray(request['qids'], dtype=int)
    dofs = np.asarray(request['vids'], dtype=int)
    target = np.asarray(request['target'], dtype=float)
    duration = float(request['duration'])
    assert q0.shape == (model.nq,) and target.shape == active.shape
    assert 0 < len(active) <= 14 and .3 <= duration <= 5.
    assert np.isfinite(q0).all() and np.isfinite(target).all()
    model.jnt_limited[:] = original_limited
    active_set = set(active.tolist())
    for j in range(model.njnt):
        if int(model.jnt_qposadr[j]) not in active_set:
            model.jnt_limited[j] = False
    configuration = mink.Configuration(model, q=q0)
    cost = np.zeros(model.nv)
    cost[dofs] = 1.
    task = mink.PostureTask(model, cost=cost, gain=.9)
    frozen = mink.DofFreezingTask(model, [i for i in range(model.nv) if i not in set(dofs.tolist())])
    names = {mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j): 2.
        for j in range(model.njnt) if int(model.jnt_qposadr[j]) in active_set}
    limits = [mink.ConfigurationLimit(model), mink.VelocityLimit(model, names)]
    dt = .02
    rows, velocities = [q0[active].tolist()], [np.zeros(len(active)).tolist()]
    count = int(np.ceil(duration / dt))
    for i in range(1, count + 1):
        u = min(1., i / count)
        ease = u * u * u * (10 + u * (-15 + 6 * u))
        desired = q0.copy()
        desired[active] = q0[active] + (target - q0[active]) * ease
        task.set_target(desired)
        velocity = mink.solve_ik(configuration, [task], dt, 'daqp', damping=1e-5,
            limits=limits, constraints=[frozen])
        configuration.integrate_inplace(velocity, dt)
        rows.append(configuration.q[active].tolist())
        velocities.append(velocity[dofs].tolist())
    held = [i for i in range(model.nq) if i not in active_set]
    drift = float(np.max(np.abs(configuration.q[held] - q0[held])))
    assert drift < 1e-9
    return {'id': request['id'], 'q': rows, 'v': velocities, 'dt': dt,
        'mink_solve_ik_calls': count, 'frozen_configuration_drift': drift,
        'model_sha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
        'versions': {name: importlib.metadata.version(name) for name in ['mink', 'mujoco']}}


for line in sys.stdin:
    try:
        request = json.loads(line)
        result = plan(request)
        print(json.dumps(result, separators=(',', ':')), flush=True)
    except Exception as error:
        print(json.dumps({'error_type': type(error).__name__, 'error': str(error)[:300]}), flush=True)
