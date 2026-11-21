"""Track GMR/mink references through the existing physical actuators."""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/visual-motion-v22'


class ReferenceClient:
    def __init__(self):
        env = os.environ.copy()
        env.update(PYTHONPATH=str(ROOT / 'src'), OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
        self.process = subprocess.Popen([str(ROOT / '.cache/visual-motion-v22/motion-env/bin/python'),
            '-u', '-m', 'mochi.visual_motion_v22.ik_worker'], env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.receipts = []

    def plan(self, w, sides, target, duration):
        qs = np.concatenate([w.arm[side]['qs'] for side in sides])
        vs = np.concatenate([w.arm[side]['vs'] for side in sides])
        request = {'id': len(self.receipts), 'qpos': w.d.qpos.tolist(),
            'qids': qs.tolist(), 'vids': vs.tolist(), 'target': np.asarray(target).tolist(), 'duration': duration}
        self.process.stdin.write(json.dumps(request) + '\n')
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('Isolated IK worker stopped: ' + self.process.stderr.read()[:300])
        response = json.loads(line)
        if 'error' in response:
            raise RuntimeError('Isolated IK: ' + response['error_type'] + ': ' + response['error'])
        assert response['id'] == request['id']
        self.receipts.append({k: v for k, v in response.items() if k not in ['q', 'v']})
        response['q'] = np.asarray(response['q'])
        response['v'] = np.asarray(response['v'])
        return response

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=10)


def reference_at(plan, elapsed):
    q, v, dt = np.asarray(plan['q']), np.asarray(plan['v']), plan['dt']
    index = min(int(max(0., elapsed) / dt), len(q) - 1)
    if index == len(q) - 1:
        return q[-1]
    u = min(1., max(0., elapsed / dt - index))
    return ((2 * u**3 - 3 * u**2 + 1) * q[index] + (u**3 - 2 * u**2 + u) * dt * v[index]
        + (-2 * u**3 + 3 * u**2) * q[index + 1] + (u**3 - u**2) * dt * v[index + 1])


@contextmanager
def apply(candidate):
    if candidate is None:
        yield None
        return
    assert set(candidate) <= {'id', 'walking', 'recovery', 'gmr_leg_blend', 'gmr_arm_blend', 'recovery_scale', 'arm_quiet_blend', 'clearance_gate'}
    assert candidate['walking'] or candidate['recovery']
    for key, low, high in [('gmr_leg_blend', 0., .2), ('gmr_arm_blend', 0., .15), ('recovery_scale', .7, 1.2)]:
        assert low <= candidate.get(key, 1. if key == 'recovery_scale' else 0.) <= high
    assert 0. <= candidate.get('arm_quiet_blend', 1.) <= 1.
    from mochi.balanced.onnx_walk import HubWalker
    from mochi.balanced.recovery import fixture_contact
    from mochi.control_v8.recovery import observation
    from mochi.smooth_v16 import recovery
    from mochi.curriculum.world import SCALE
    original_command, original_recovery = HubWalker.command, recovery.recover
    reference_path = OUT / 'gmr-walking-reference-calibrated.json'
    ref = json.loads(reference_path.read_text())
    samples = np.asarray(ref['filtered_qpos'])
    medians = np.median(samples, axis=0)
    columns = ref['joint_qpos_indices']
    client = ReferenceClient()
    summary = {'candidate': candidate, 'gmr_reference_sha256': hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        'gmr_reference_frames': len(samples), 'gmr_reference_uses': 0, 'native_weights_trained': False,
        'optimizer_updates': 0, 'scope': 'Bounded reference/controller experiment; authoritative physics remains MuJoCo 3.3.7.'}

    def command(walker, velocity):
        original_command(walker, velocity)
        w = walker.w
        eligible = candidate['walking'] and walker.mode == 'walk' and w.phase in ['walk', 'turn']
        if not eligible:
            return
        if not hasattr(walker, '_v22_arm_plan'):
            goals = []
            for side in ['left', 'right']:
                arm = w.arm[side]
                goal = arm['rest'].copy()
                for i, qid in enumerate(arm['qs']):
                    import mujoco
                    jid = int(w.m.dof_jntid[arm['vs'][i]])
                    name = mujoco.mj_id2name(w.m, mujoco.mjtObj.mjOBJ_JOINT, jid)
                    if name in columns:
                        native = float(medians[columns[name]]) - w.meta['home_joint_offsets'].get(name, 0.)
                        goal[i] += np.clip(native, -.8, .8) * candidate.get('gmr_arm_blend', 0.)
                goals.extend(np.clip(goal, arm['limits'][:, 0] + .002, arm['limits'][:, 1] - .002))
            walker._v22_arm_plan = client.plan(w, ['left', 'right'], goals, .8)
            walker._v22_arm_start = float(w.d.time)
        target = reference_at(walker._v22_arm_plan, float(w.d.time) - walker._v22_arm_start)
        requested_blend = candidate.get('arm_quiet_blend', 1.)
        if candidate.get('clearance_gate', False):
            import mujoco
            if not hasattr(walker, '_v22_gate_time') or w.d.time - walker._v22_gate_time >= .04:
                points = [w.d.site_xpos[arm['tip']] for arm in w.arm.values()]
                distance = float('inf')
                for gid in range(w.m.ngeom):
                    if int(w.m.geom_bodyid[gid]) in w.robot_bodies or gid in w.support_geoms or not w.m.geom_contype[gid]:
                        continue
                    for point in points:
                        local = w.d.geom_xmat[gid].reshape(3, 3).T @ (point - w.d.geom_xpos[gid])
                        if w.m.geom_type[gid] == mujoco.mjtGeom.mjGEOM_BOX:
                            separation = float(np.linalg.norm(np.maximum(np.abs(local) - w.m.geom_size[gid], 0.)))
                        else:
                            separation = float(np.linalg.norm(local) - w.m.geom_rbound[gid])
                        distance = min(distance, separation)
                walker._v22_safe = distance >= .025
                walker._v22_gate_time = float(w.d.time)
            requested_blend *= float(walker._v22_safe)
        age = float(w.d.time) - getattr(walker, '_v22_blend_time', float(w.d.time))
        walker._v22_blend_time = float(w.d.time)
        walker._v22_blend = getattr(walker, '_v22_blend', 0.) + np.clip(requested_blend - getattr(walker, '_v22_blend', 0.), -2. * age, .5 * age)
        offset = 0
        for side in ['left', 'right']:
            arm = w.arm[side]
            n = len(arm['qs'])
            native = w.d.ctrl[arm['acts']].copy()
            bounded_reference = np.clip(target[offset:offset + n], arm['limits'][:, 0] + .001, arm['limits'][:, 1] - .001)
            # Native position-actuator commands also encode PD torque and gravity
            # compensation. Preserve them exactly at zero reference blend.
            if walker._v22_blend > 0.:
                w.d.ctrl[arm['acts']] = native + walker._v22_blend * (bounded_reference - native)
            offset += n
        blend = candidate.get('gmr_leg_blend', 0.)
        if blend:
            phase = ((float(w.d.time) - walker.origin) / walker.time_scale % .6) / .6
            sample = samples[int(phase * (len(samples) - 1))]
            for i, name in enumerate(walker.names):
                actuator = walker.amap[i]
                if actuator not in set(walker.aids) or name not in columns:
                    continue
                residual = np.clip((sample[columns[name]] - medians[columns[name]]) * blend, -.025, .025)
                w.d.ctrl[actuator] = np.clip(w.d.ctrl[actuator] + walker.kp[i] * residual, *w.m.actuator_forcerange[actuator])
        summary['maximum_arm_blend'] = max(summary.get('maximum_arm_blend', 0.), float(walker._v22_blend))
        summary['arm_reference_active_steps'] = summary.get('arm_reference_active_steps', 0) + int(walker._v22_blend > 1e-6)
        if blend or (candidate.get('gmr_arm_blend', 0.) and walker._v22_blend > 1e-6):
            summary['gmr_reference_uses'] += 1

    def recover(w, task, code):
        if not candidate['recovery'] or code != 'R4':
            return original_recovery(w, task, code)
        side, arm = w.approach_side, w.arm[w.approach_side]
        w.task, w.phase = None, 'recover'
        start = float(w.d.time)
        initial = observation(w, task)
        q0 = w.d.qpos[arm['qs']].copy()
        points = []
        if task == 'alarm':
            outside = q0.copy()
            outside[1] = min(q0[1], -.55) if side == 'right' else max(q0[1], .55)
            points.append(outside)
        points.append(arm['rest'].copy())
        segment, segment_start, plan = 0, start, None
        previous, previous_tip = q0.copy(), w.d.site_xpos[arm['tip']].copy()
        travel = path = stable = peak = 0.
        contacts = 0
        while w.d.time - start < 8. and not w.fall:
            if segment < len(points):
                if plan is None:
                    duration = max(.35, 1.2 * candidate.get('recovery_scale', 1.) * float(np.max(abs(points[segment] - w.d.qpos[arm['qs']]))))
                    plan = client.plan(w, [side], points[segment], min(5., duration))
                    segment_start = float(w.d.time)
                target = reference_at(plan, float(w.d.time) - segment_start)
                w.d.ctrl[arm['acts']] = np.clip(target, arm['limits'][:, 0] + .001, arm['limits'][:, 1] - .001)
                if w.d.time - segment_start >= (len(plan['q']) - 1) * plan['dt'] and np.max(abs(w.d.qpos[arm['qs']] - points[segment])) < .04:
                    segment += 1
                    plan = None
            else:
                w.d.ctrl[arm['acts']] = arm['rest']
            w.step(standing=True)
            q, tip = w.d.qpos[arm['qs']].copy(), w.d.site_xpos[arm['tip']].copy()
            travel += float(np.sum(abs(q - previous)))
            path += float(np.linalg.norm(tip - previous_tip))
            previous, previous_tip = q, tip
            count, force = fixture_contact(w)
            contacts += int(count > 0)
            peak = max(peak, force)
            ready = (segment == len(points) and np.max(abs(q - arm['rest'])) < .035
                and np.max(abs(w.d.qvel[arm['vs']])) < .2
                and math.degrees(math.acos(float(np.clip(w.d.xmat[1, 8], -1, 1)))) < 5.)
            stable = stable + w.m.opt.timestep if ready else 0.
            if stable >= .12 or peak > .8:
                break
        result = {'task': task, 'action': 'V22-MINK-R4', 'success': bool(stable >= .12 and not w.fall and contacts == 0),
            'duration_s': float(w.d.time) - start, 'arm_joint_travel_rad': travel, 'hand_path_m': path,
            'fixture_contact_steps': contacts, 'peak_fixture_force_n': peak,
            'end_max_joint_error_rad': float(np.max(abs(w.d.qpos[arm['qs']] - arm['rest']))),
            'end_max_joint_speed_rad_s': float(np.max(abs(w.d.qvel[arm['vs']]))), 'fall': w.fall,
            'observation': initial, 'profile': candidate}
        w.recoveries.append(result)
        w.events.append({'phase': 'recover', 't': float(w.d.time), **result})
        return result

    HubWalker.command, recovery.recover = command, recover
    try:
        yield (summary, client)
    finally:
        HubWalker.command, recovery.recover = original_command, original_recovery
        summary['mink_plan_receipts'] = client.receipts
        summary['mink_solve_ik_calls'] = sum(r['mink_solve_ik_calls'] for r in client.receipts)
        client.close()
