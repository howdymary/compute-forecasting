"""Retarget a real, attributed CMU walking recording with pinned GMR and mink."""
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import sys
import types

import mink
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.signal import savgol_filter

ROOT = Path(__file__).resolve().parents[3]
UPSTREAM = ROOT / '.cache/visual-motion-v22/GMR'
OUT = ROOT / 'artifacts/visual-motion-v22'


def gmr_core():
    # Load the unchanged core without optional Torch/viewer/streaming imports.
    name = 'general_motion_retargeting'
    package = types.ModuleType(name)
    package.__path__ = [str(UPSTREAM / name)]
    sys.modules[name] = package
    return importlib.import_module(name + '.motion_retarget').GeneralMotionRetargeting


def main():
    path = OUT / 'source/07_01.bvh'
    raw = path.read_bytes()
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == '0e50b7db19c7ea0bf2cd3df942f82642b9b22ebc'
    GMR = gmr_core()
    extract = importlib.import_module('general_motion_retargeting.utils.lafan_vendor.extract')
    utils = importlib.import_module('general_motion_retargeting.utils.lafan_vendor.utils')
    data = extract.read_bvh(str(path))
    quaternions, positions = utils.quat_fk(data.quats, data.pos, data.parents)
    rotation = Rotation.from_euler('x', 90, degrees=True)
    # CMU ASF units retained by this BVH conversion; verified against skeleton height.
    unit_scale = (1 / .45) * 2.54 / 100
    positions = rotation.apply(positions.reshape(-1, 3)).reshape(positions.shape) * unit_scale
    quaternions = (rotation * Rotation.from_quat(quaternions.reshape(-1, 4), scalar_first=True)).as_quat(scalar_first=True).reshape(quaternions.shape)
    indices = {name: i for i, name in enumerate(data.bones)}
    ground = min(float(positions[1:, indices[name], 2].min()) for name in ['LeftFoot', 'RightFoot'])
    origin = positions[1, indices['Hips'], :2].copy()
    positions[:, :, :2] -= origin
    positions[:, :, 2] -= ground
    human_height = float(positions[0, indices['Head'], 2] - min(positions[0, indices[n], 2] for n in ['LeftFoot', 'RightFoot']) + .15)
    assert 1.3 <= human_height <= 2.2, human_height
    retargeter = GMR('bvh_lafan1', 'unitree_g1', actual_human_height=human_height, verbose=False)
    retargeter.max_iter = 3
    counter = {'mink_solve_ik': 0}
    solve = mink.solve_ik

    def measured(*args, **kwargs):
        counter['mink_solve_ik'] += 1
        return solve(*args, **kwargs)

    mink.solve_ik = measured
    rows = []
    frame_indices = list(range(1, len(positions), 2))
    try:
        for frame in frame_indices:
            source = {name: [positions[frame, i].copy(), quaternions[frame, i].copy()] for name, i in indices.items()}
            source['Spine2'] = source['Spine1']
            source['LeftFootMod'] = [source['LeftFoot'][0], source['LeftToeBase'][1]]
            source['RightFootMod'] = [source['RightFoot'][0], source['RightToeBase'][1]]
            rows.append(retargeter.retarget(source, offset_to_ground=True).tolist())
    finally:
        mink.solve_ik = solve
    q = np.asarray(rows)
    filtered = q.copy()
    filtered[:, 7:] = savgol_filter(q[:, 7:], 9, 3, axis=0)
    for joint in range(retargeter.model.njnt):
        if retargeter.model.jnt_type[joint] == mujoco.mjtJoint.mjJNT_HINGE:
            index = int(retargeter.model.jnt_qposadr[joint])
            filtered[:, index] = np.clip(filtered[:, index], *retargeter.model.jnt_range[joint])
    joints = {mujoco.mj_id2name(retargeter.model, mujoco.mjtObj.mjOBJ_JOINT, j): int(retargeter.model.jnt_qposadr[j])
        for j in range(retargeter.model.njnt) if retargeter.model.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE}
    payload = {'source': 'CMU Graphics Lab recording 07_01, Bruce Hahne BVH conversion',
        'source_url': 'https://github.com/una-dinosauria/cmu-mocap/blob/master/data/007/07_01.bvh',
        'permission_url': 'https://mocap.cs.cmu.edu/faqs.php', 'source_sha256': hashlib.sha256(raw).hexdigest(),
        'source_git_blob': '0e50b7db19c7ea0bf2cd3df942f82642b9b22ebc',
        'gmr_commit': '25f56db79ac411258b377b6d4ccba0c8ff3372ac',
        'gmr_core_sha256': hashlib.sha256((UPSTREAM / 'general_motion_retargeting/motion_retarget.py').read_bytes()).hexdigest(),
        'versions': {name: importlib.metadata.version(name) for name in ['mink', 'mujoco', 'numpy', 'scipy', 'qpsolvers']},
        'gmr_retarget_calls': len(rows), **counter, 'dt': 2 / 120, 'source_frames': frame_indices,
        'actual_human_height_m': human_height, 'source_units_to_metres': unit_scale,
        'joint_qpos_indices': joints, 'raw_qpos': q.tolist(), 'filtered_qpos': filtered.tolist(),
        'scope': 'Kinematic reference generation only. Root references are never assigned to the physical executor. No optimizer updates or claim of physical improvement.'}
    (OUT / 'gmr-walking-reference.json').write_text(json.dumps(payload, separators=(',', ':')) + '\n')
    print(json.dumps({key: payload[key] for key in ['gmr_retarget_calls', 'mink_solve_ik', 'versions', 'actual_human_height_m']}))


if __name__ == '__main__':
    main()
