"""Real paper-free physics and measured step-reward teaching branches."""
import asyncio
import gzip
import hashlib
import json
import time
from pathlib import Path

import modal
import numpy as np

from ..balanced.sequence import PhysicalStop
from ..smooth_v16.objective import branch_metrics
from ..smooth_v16.public import rounded
from ..smooth_v16.world import state
from ..terrain_v12.learning_remote import image, receipt as inherited_receipt, secret
from ..terrain_v13.remote import Selector as BaseSelector
from .objective import branch_reward, qualify, valid_branch
from ..paperfree_v19.policy import choices, decision, execute, fixed, observation
from ..paperfree_v19.sequence import run
from ..paperfree_v19.world import restore


VOLUME = 'mochi-paperfree-v19r1-artifacts'
volume = modal.Volume.from_name(VOLUME, create_if_missing=True)
app = modal.App('mochi-paperfree-v19r1-learning')


def physical_hash(w):
    return hashlib.sha256(np.r_[w.d.qpos, w.d.qvel, w.d.ctrl, w.d.time].tobytes()).hexdigest()


def receipt(start, count):
    return {**inherited_receipt(start, count), 'memory_mib': 4096}


def archive(row, run_id, name):
    raw = json.dumps(row, separators=(',', ':')).encode()
    path = Path('/artifacts') / run_id / (name + '.json.gz')
    assert not path.exists(), 'Preserve immutable evidence'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(raw, compresslevel=1, mtime=0))
    volume.commit()
    return {'volume': VOLUME, 'path': str(path.relative_to('/artifacts')),
            'uncompressed_sha256': hashlib.sha256(raw).hexdigest()}


def export_clip(row, run_id, name):
    e = row['episode']
    clip = {k: v for k, v in e.items() if k not in ['control_telemetry', 'book_motion_samples', 'balance_measurements']}
    clip['balance_measurements'] = [{k: v for k, v in m.items() if k in
        ['t', 'phase', 'gait_phase', 'roll_rad', 'loads_n', 'step_category']} for m in e['balance_measurements']]
    clip['model_decisions'] = row.get('model_decisions', [])
    raw = json.dumps(rounded(clip), separators=(',', ':')).encode()
    data = gzip.compress(raw, compresslevel=6, mtime=0)
    path = Path('/artifacts') / run_id / 'public' / (name + '.json.gz')
    assert not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    volume.commit()
    return {'volume': VOLUME, 'path': str(path.relative_to('/artifacts')),
            'sha256': hashlib.sha256(data).hexdigest(), 'uncompressed_sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(data), 'scope': 'Uninterrupted MuJoCo body transforms. No paper geometry or scripted paper crossing.'}


def compact(row):
    for key in ['trajectory', 'balance_measurements', 'control_telemetry']:
        row['episode'].pop(key, None)
    return row


class Selector(BaseSelector):
    async def select(self, obs):
        from tinker_cookbook.recipes.decisions import sample_decision
        key = json.dumps(obs, sort_keys=True)
        if key not in self.cache:
            rendered = self.renderer.render(decision(obs))
            n = len(rendered.tokens) + 1
            if self.used + n > self.cap:
                raise PhysicalStop('inference_token_limit')
            self.used += n
            distribution = await sample_decision(self.sampler, rendered)
            self.cache[key] = (max(distribution, key=distribution.get), distribution)
        return self.cache[key]


def evaluate_impl(seed, models, run_id, group, cfg):
    started = time.perf_counter()

    async def body():
        rows, tokens = {}, 0
        for label, payload, static in models:
            selector = Selector(payload) if payload else None
            if selector:
                selector.setup()
            decisions = []

            def choose(w, domain, task, default, available):
                obs = observation(w, domain, task)
                if selector:
                    action, distribution = selector.sync(obs)
                elif static:
                    action, distribution = static[domain + ':' + task], None
                else:
                    return fixed(w, domain, task, default, available)
                item = {'t': float(w.d.time), 'observation': obs, 'action': action,
                        'distribution': distribution, 'initial_physical_state_sha256': physical_hash(w),
                        'source': 'Tinker saved checkpoint' if selector else 'training-derived static control'}
                decisions.append(item)
                w.decisions.append(item)
                return action

            row = await asyncio.to_thread(run, seed, True, choose)
            row['model_decisions'] = decisions
            qualify(row, cfg)
            name = f'{group}-{seed}-{label}'
            row['archive'] = archive(row, run_id, name)
            row['public_recording'] = export_clip(row, run_id, name)
            rows[label] = compact(row)
            tokens += selector.used if selector else 0
        return {'seed': seed, 'rows': rows, 'receipt': {**receipt(started, len(models)),
            'inference_input_plus_max_output_tokens': tokens, 'paired_same_process': len(models) > 1}}

    return asyncio.run(body())


@app.function(image=image, secrets=[secret], cpu=1, memory=4096, max_containers=4,
              timeout=2400, retries=0, volumes={'/artifacts': volume})
def evaluate(seed, models, run_id, group, cfg):
    return evaluate_impl(seed, models, run_id, group, cfg)


@app.function(image=image, secrets=[secret], cpu=1, memory=4096, max_containers=4,
              timeout=3600, retries=0, volumes={'/artifacts': volume})
def evaluate_pair(seed, models, run_id, group, cfg):
    assert len(models) == 2
    return evaluate_impl(seed, models, run_id, group, cfg)


@app.function(image=image, secrets=[secret], cpu=1, memory=4096, max_containers=4,
              timeout=5400, retries=0, volumes={'/artifacts': volume})
def collect(seed, payload, run_id, cfg):
    started = time.perf_counter()

    async def body():
        selector = Selector(payload)
        selector.setup()
        count, examples, trials = 1, [], []

        def choose(w, domain, task, default, available):
            nonlocal count
            observed = observation(w, domain, task)
            preferred, distribution = selector.sync(observed)
            # One alternative plus the measured reference keeps the remaining
            # campaign budget bounded. The final recovery has one validated target.
            reference = 'W10' if domain == 'walk' else {'alarm': 'H0', 'drawer': 'C', 'laptop': 'P5', 'globe': 'G0'}[task] if domain != 'recovery' else 'R4'
            alternate = 'W8' if domain == 'walk' else 'P6' if task == 'laptop' and domain != 'recovery' else 'F' if task == 'alarm' and domain != 'recovery' else 'R0' if domain == 'recovery' else reference
            planned = [reference] if domain == 'recovery' and task == 'globe' else [preferred, reference] if preferred != reference else [reference, alternate]
            candidates = [x for x in dict.fromkeys(planned) if x in available]
            saved, initial, outcomes = state(w, include_history=False), physical_hash(w), []
            for action in candidates:
                count += 1
                if count > 22:
                    raise PhysicalStop('collection_attempt_ceiling')
                clone = restore(saved, False)
                assert physical_hash(clone) == initial
                begin, index = float(clone.d.time), len(clone.measurements)
                detail, withdrawal, failure, success = {}, None, None, False
                print(json.dumps({'seed': seed, 'domain': domain, 'task': task, 'action': action, 'attempt': count}), flush=True)
                try:
                    detail = execute(clone, domain, task, action)
                    success = all(r['success'] for r in detail) if domain == 'walk' else detail['success']
                    if success and domain not in ['walk', 'recovery']:
                        withdrawal = execute(clone, 'recovery', task, 'R4')
                        success = success and withdrawal['success']
                except PhysicalStop as exc:
                    failure = str(exc)
                e = clone.episode()
                result = {'action': action, 'success': bool(success), 'failure': failure,
                    'result': detail, 'coupled_recovery': withdrawal, 'duration_s': float(clone.d.time) - begin,
                    'steps': clone.step_counter.summary(since=begin), 'metrics': branch_metrics(clone.measurements[index:]),
                    'native_smoothness': {**e['native_smoothness'], 'scope': 'Restored partial-history diagnostic only. Full-route aggregate thresholds apply to complete reference and evaluation runs.'}, 'longest_unsupported_seconds': e['longest_unsupported_seconds'],
                    'fall': clone.fall, 'invalid_contact': clone.invalid_contact,
                    'initial_state_sha256': initial, 'flat_foot_clearance': e['flat_foot_clearance']}
                result['step_reward'] = branch_reward(domain, result)
                result['archive'] = archive(result, run_id, f'branch-{seed}-{domain}-{task}-{action}')
                outcomes.append(result)
            trial = {'domain': domain, 'task': task, 'observation': observed,
                     'student_preference': preferred, 'student_distribution': distribution, 'outcomes': outcomes}
            trials.append(trial)
            valid = [r for r in outcomes if valid_branch(r, domain)]
            if not valid:
                raise PhysicalStop('teacher_no_valid_action:' + domain + ':' + task)
            best = max(valid, key=lambda r: r['step_reward'])
            action = best['action']
            examples.append({'domain': domain, 'task': task, 'observation': observed, 'action': action,
                'student_preference': preferred, 'student_distribution': distribution,
                'initial_state_sha256': initial,
                'outcomes_sha256': hashlib.sha256(json.dumps(outcomes, sort_keys=True).encode()).hexdigest()})
            assert any(r['action'] == reference for r in valid), 'Reference action failed local validity'
            w.decisions.append({'t': float(w.d.time), 'observation': observed, 'action': reference,
                'training_target': action, 'source': 'fixed W10/P5/R4 reference; separate measured step-reward target'})
            return reference

        row = await asyncio.to_thread(run, seed, False, choose)
        qualify(row, cfg)
        result = {'seed': seed, 'valid': row['qualified_complete'], 'row': row, 'examples': examples, 'trials': trials}
        result['archive'] = archive(result, run_id, f'teacher-{seed}')
        compact(row)
        result['receipt'] = {**receipt(started, count), 'inference_input_plus_max_output_tokens': selector.used}
        return result

    return asyncio.run(body())
