"""Real Modal rollouts, guarded student visitation and exact-state probes.

The immutable V12 simulator/controllers are imported, never edited here.
Private state snapshots are made by our own simulator; they are not demos.
"""
import asyncio
import gzip
import hashlib
import json
import pickle
import time
from pathlib import Path

import modal
import numpy as np

from ..terrain_v12.learning_remote import image, secret, compact, receipt
from ..terrain_v12.policy import observation, decision, execute, fixed
from ..terrain_v12.sequence import run, PhysicalStop
from ..terrain_v12.snapshot import branch
from ..terrain_v12.development import state, restore
from ..balanced.verification import metrics
from .objective import branch_rank

app = modal.App('mochi-terrain-v13-continuation')
volume = modal.Volume.from_name('mochi-terrain-v13-artifacts', create_if_missing=True)


def archive(row, run_id, name):
    raw = json.dumps(row, separators=(',', ':')).encode()
    path = Path('/artifacts') / run_id / (name + '.json.gz')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RuntimeError('Refuse to overwrite a V13 physics artifact')
    path.write_bytes(gzip.compress(raw, compresslevel=1))
    volume.commit()
    return {'volume': 'mochi-terrain-v13-artifacts',
            'path': str(path.relative_to('/artifacts')),
            'uncompressed_sha256': hashlib.sha256(raw).hexdigest()}


class Selector:
    def __init__(self, payload, cap=24000):
        self.payload = payload
        self.cap = cap
        self.used = 0
        self.cache = {}

    def setup(self):
        from tinker.lib.public_interfaces.sampling_client import _unpickle_sampling_client
        from tinker_cookbook import model_info, renderers
        from tinker_cookbook.recipes.decisions import DecisionRenderer
        self.sampler = _unpickle_sampling_client(pickle.loads(self.payload))
        self.renderer = DecisionRenderer(renderers.get_renderer(
            model_info.get_recommended_renderer_name('Qwen/Qwen3.5-4B'), self.sampler.get_tokenizer()))
        self.loop = asyncio.get_running_loop()

    async def select(self, obs):
        from tinker_cookbook.recipes.decisions import sample_decision
        key = json.dumps(obs, sort_keys=True)
        if key not in self.cache:
            rendering = self.renderer.render(decision(obs))
            tokens = len(rendering.tokens) + 1
            if self.used + tokens > self.cap:
                raise PhysicalStop('inference_token_limit')
            self.used += tokens
            probabilities = await sample_decision(self.sampler, rendering)
            self.cache[key] = (max(probabilities, key=probabilities.get), probabilities)
        return self.cache[key]

    def sync(self, obs):
        return asyncio.run_coroutine_threadsafe(self.select(obs), self.loop).result()


@app.function(image=image, secrets=[secret], cpu=1, memory=3072,
              max_containers=4, timeout=4500, volumes={'/artifacts': volume})
def collect(seed, payload, run_id):
    """Label real alternatives on student-visited states, with a safety guard."""
    started = time.perf_counter()

    async def body():
        selector = Selector(payload)
        selector.setup()
        count = 1
        examples, trials = [], []

        def choose(w, domain, task, default, choices):
            nonlocal count
            observed = observation(w, domain, task)
            preferred, probabilities = selector.sync(observed)
            assert preferred in choices
            initial = hashlib.sha256(np.r_[w.d.qpos, w.d.qvel, w.d.ctrl, w.d.time].tobytes()).hexdigest()
            outcomes = []
            for action in choices:
                count += 1
                if count > 37:
                    raise RuntimeError('Physical branch cap')
                clone = branch(w)
                actual = hashlib.sha256(np.r_[clone.d.qpos, clone.d.qvel, clone.d.ctrl, clone.d.time].tobytes()).hexdigest()
                assert initial == actual, 'Counterfactual initial state differs'
                start, index = float(clone.d.time), len(clone.measurements)
                result, withdrawal, failure = {}, None, None
                try:
                    result = execute(clone, domain, task, action)
                    success = all(x['success'] for x in result) if domain == 'walk' else result['success']
                    if success and domain not in ['walk', 'recovery']:
                        withdrawal = execute(clone, 'recovery', task, 'R0')
                        success = success and withdrawal['success']
                except PhysicalStop as exc:
                    success, failure = False, str(exc)
                outcomes.append({'action': action, 'success': bool(success), 'failure': failure,
                    'duration_s': float(clone.d.time) - start,
                    'metrics': metrics(clone.measurements[index:]), 'result': result,
                    'coupled_recovery': withdrawal, 'fall': clone.fall,
                    'invalid_contact': clone.invalid_contact, 'initial_state_sha256': initial})
            valid = [r for r in outcomes if r['success'] and not r['fall'] and not r['invalid_contact']]
            trials.append({'domain': domain, 'task': task, 'observation': observed,
                           'student_preference': preferred, 'outcomes': outcomes})
            if not valid:
                raise PhysicalStop('no_valid_training_action:' + domain + ':' + task)
            best = min(valid, key=lambda r: branch_rank(domain, r))['action']
            # The continuation actually visits the student's selected state
            # when it is safe; unsafe preferences are replaced by the oracle.
            executed = preferred if any(r['action'] == preferred for r in valid) else best
            examples.append({'domain': domain, 'task': task, 'observation': observed,
                'action': best, 'executed_action': executed, 'guard_intervened': executed != preferred,
                'student_distribution': probabilities, 'initial_state_sha256': initial})
            w.decisions.append({'t': float(w.d.time), 'observation': observed, 'action': executed,
                'source': 'guarded student visitation with physical counterfactual labels'})
            return executed

        row = await asyncio.to_thread(run, seed, True, choose=choose)
        answer = {'seed': seed, 'valid': row['complete_sequence_success'], 'examples': examples,
                  'trials': trials, 'row': row, 'receipt': {**receipt(started, count),
                  'inference_input_plus_max_output_tokens': selector.used}}
        answer['archive'] = archive(answer, run_id, 'teacher-' + str(seed))
        compact(row)
        return answer

    return asyncio.run(body())


@app.function(image=image, secrets=[secret], cpu=1, memory=3072,
              max_containers=4, timeout=1500, volumes={'/artifacts': volume})
def evaluate(seed, label, payload, run_id, group, static=None, capture_states=False):
    started = time.perf_counter()

    async def body():
        selector = Selector(payload) if payload else None
        if selector:
            selector.setup()
        records, snapshots = [], {}

        def choose(w, domain, task, default, choices):
            if capture_states:
                snapshots[domain + ':' + task] = state(w, include_history=False)
            obs = observation(w, domain, task)
            if selector:
                action, distribution = selector.sync(obs)
            elif static:
                action, distribution = static[domain + ':' + task], None
            else:
                return fixed(w, domain, task, default, choices)
            assert action in choices
            record = {'t': float(w.d.time), 'observation': obs, 'action': action,
                      'distribution': distribution,
                      'source': 'Tinker saved weights' if selector else 'training-only static preference'}
            records.append(record)
            w.decisions.append(record)
            return action

        row = await asyncio.to_thread(run, seed, True, choose=choose)
        row['model_decisions'] = records
        row['inference'] = {'input_plus_max_output_tokens': selector.used if selector else 0}
        if capture_states:
            path = Path('/artifacts') / run_id / f'{group}-{seed}-states.pickle'
            assert not path.exists(), 'Private supported states already archived'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(pickle.dumps(snapshots))
            volume.commit()
            row['supported_states'] = {'path': str(path.relative_to('/artifacts')),
                                       'keys': list(snapshots), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        row['archive'] = archive(row, run_id, f'{group}-{seed}-{label}')
        return {'seed': seed, 'label': label, 'group': group, 'row': compact(row), 'receipt': {**receipt(started, 1),
                'inference_input_plus_max_output_tokens': selector.used if selector else 0}}

    return asyncio.run(body())


@app.function(image=image, secrets=[secret], cpu=1, memory=3072,
              max_containers=4, timeout=3000, volumes={'/artifacts': volume})
def components(seed, task, models, run_id, state_reference):
    """Both weights act from exactly the same independently generated state.

    These diagnostic branches cannot be spliced into a continuous demo.
    """
    started = time.perf_counter()

    async def body():
        volume.reload()
        path = Path('/artifacts') / state_reference['path']
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == state_reference['sha256']
        snapshots = pickle.loads(raw)  # trusted local simulator artifact only
        results, count, tokens = [], 0, 0
        for domain in ['walk', task, 'recovery']:
            key = domain + ':' + task
            if key not in snapshots:
                results.append({'domain': domain, 'task': task, 'status': 'reference_not_reached'})
                continue
            initial_ids = []
            for label, payload in models:
                selector = Selector(payload)
                selector.setup()
                w = restore(snapshots[key], record=False)
                initial = hashlib.sha256(np.r_[w.d.qpos, w.d.qvel, w.d.ctrl, w.d.time].tobytes()).hexdigest()
                initial_ids.append(initial)
                obs = observation(w, domain, task)
                action, distribution = await selector.select(obs)
                start, index = float(w.d.time), len(w.measurements)
                count += 1
                result, failure = None, None
                try:
                    result = await asyncio.to_thread(execute, w, domain, task, action)
                    success = all(x['success'] for x in result) if domain == 'walk' else result['success']
                except PhysicalStop as exc:
                    success, failure = False, str(exc)
                tokens += selector.used
                results.append({'domain': domain, 'task': task, 'model': label,
                    'scope': 'exact-state component diagnostic, not a full episode',
                    'initial_state_sha256': initial, 'action': action, 'distribution': distribution,
                    'success': bool(success), 'failure': failure, 'result': result,
                    'fall': w.fall, 'invalid_contact': w.invalid_contact,
                    'duration_s': float(w.d.time) - start, 'metrics': metrics(w.measurements[index:])})
            assert len(set(initial_ids)) == 1, 'Component models did not share initial state'
        answer = {'seed': seed, 'task': task, 'results': results,
                  'reference': state_reference, 'receipt': {**receipt(started, count),
                  'inference_input_plus_max_output_tokens': tokens}}
        answer['archive'] = archive(answer, run_id, f'components-{seed}-{task}')
        return answer

    return asyncio.run(body())
