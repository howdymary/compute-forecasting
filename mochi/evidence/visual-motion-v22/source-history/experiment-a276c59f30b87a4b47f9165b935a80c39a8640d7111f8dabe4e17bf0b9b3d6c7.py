"""Bounded physical tests of isolated GMR/mink-generated controller references."""
import argparse
from contextlib import ExitStack
import fcntl
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import signal
import time

import numpy as np

from mochi.balanced.sequence import PhysicalStop
from mochi.inkling_v21.controls import apply as clearance
from mochi.paperfree_v19 import policy, sequence
from mochi.paperfree_v19.world import restore
from mochi.paperfree_v19.objective import qualify
from mochi.paperfree_v19r1.objective import valid_branch
from mochi.smooth_v16.objective import branch_metrics
from mochi.visual_motion_v22.controller import ROOT, apply

OUT = ROOT / 'artifacts/visual-motion-v22/physics'


def account(ident, value):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'ledger.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        file = OUT / 'ledger.json'
        ledger = json.loads(file.read_text()) if file.exists() else {'attempts': {}}
        if ident not in ledger['attempts']:
            assert len(ledger['attempts']) < 32
            assert sum(v.get('wall_seconds', v['reserved_seconds']) for v in ledger['attempts'].values()) + value['reserved_seconds'] <= 14400
        ledger['attempts'][ident] = value
        file.write_text(json.dumps(ledger, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    parser.add_argument('--mode', choices=['branch', 'full'], required=True)
    parser.add_argument('--domain', choices=['walk', 'turn', 'recovery'], default='walk')
    parser.add_argument('--snapshot')
    parser.add_argument('--candidate')
    parser.add_argument('--seed', type=int, default=221000)
    args = parser.parse_args()
    candidate = json.loads(Path(args.candidate).read_text()) if args.candidate else None
    reserved = 900. if args.mode == 'full' else 300.
    target = OUT / (args.id + '.json.gz')
    assert not target.exists() and not (OUT / (args.id + '.started.json')).exists()
    meta = {'id': args.id, 'status': 'running', 'reserved_seconds': reserved, 'arguments': vars(args),
        'candidate': candidate, 'physical_mujoco_version': '3.3.7', 'optimizer_updates': 0,
        'controller_sha256': hashlib.sha256(Path(__file__).with_name('controller.py').read_bytes()).hexdigest()}
    account(args.id, meta)
    (OUT / (args.id + '.started.json')).write_text(json.dumps(meta, indent=2) + '\n')
    began = time.perf_counter()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('V22 physical attempt wall limit')))
    signal.setitimer(signal.ITIMER_REAL, reserved)

    def choose(w, domain, task, default, available):
        action = 'W10' if domain == 'walk' else 'R4' if domain == 'recovery' else {'alarm': 'H0', 'drawer': 'C', 'laptop': 'P5', 'globe': 'G0'}[task]
        w.decisions.append({'t': float(w.d.time), 'observation': policy.observation(w, domain, task), 'action': action,
            'source': 'V22 fixed reference vector, with declared optional GMR/mink controller adapter'})
        return action

    references = None
    try:
        with ExitStack() as stack:
            stack.enter_context(clearance(json.loads((ROOT / 'configs/inkling-v21-selected.json').read_text())))
            references = stack.enter_context(apply(candidate))
            if args.mode == 'full':
                row = sequence.run(args.seed, True, choose)
                qualify(row, json.loads((ROOT / 'configs/paperfree-v19-training.json').read_text()))
                start = 0.
            else:
                snapshot = Path(args.snapshot)
                saved = snapshot.read_bytes()
                meta['snapshot_sha256'] = hashlib.sha256(saved).hexdigest()
                w = restore(pickle.loads(gzip.decompress(saved)), True)
                start = float(w.d.time)
                # Rendering history is not control state. Keep the recent physical
                # measurements needed by cycle-averaged feedback; never alter qpos.
                w.frames = []
                w.last_frame = start - .04
                w.next_frame = start
                w.measurements = w.measurements[-50:]
                w.control_telemetry = w.control_telemetry[-50:]
                index = len(w.measurements)
                telemetry_index = len(w.control_telemetry)
                slip = dict(w.foot_slip_m)
                failure, detail, success = None, None, False
                task = 'globe' if args.domain == 'turn' else 'laptop'
                domain = 'recovery' if args.domain == 'recovery' else 'walk'
                try:
                    detail = policy.execute(w, domain, task, 'R4' if domain == 'recovery' else 'W10')
                    success = detail['success'] if isinstance(detail, dict) else all(v['success'] for v in detail)
                except PhysicalStop as error:
                    failure = str(error)
                episode = w.episode()
                metrics = branch_metrics(w.measurements[index:])
                validity = {'success': bool(success), 'fall': w.fall, 'invalid_contact': w.invalid_contact,
                    'metrics': metrics, 'longest_unsupported_seconds': episode['longest_unsupported_seconds'],
                    'flat_foot_clearance': episode['flat_foot_clearance']}
                arms = 0.
                samples = w.control_telemetry[telemetry_index:]
                for a, b in zip(samples, samples[1:]):
                    arms += sum(float(np.sum(abs(np.asarray(b['q'][s]) - a['q'][s]))) for s in ['left', 'right'])
                row = {'seed': args.seed, 'failure': failure, 'episode': episode, 'detail': detail,
                    'component_success': bool(success), 'component_valid': valid_branch(validity, domain),
                    'component_domain': args.domain, 'start_time': start,
                    'component_metrics': metrics, 'component_steps': w.step_counter.summary(since=start),
                    'component_seconds': float(w.d.time) - start, 'component_arm_travel_rad': arms,
                    'component_slip_m': sum(w.foot_slip_m[s] - slip[s] for s in slip),
                    'scope': 'Restored-state component diagnostic. This is not a continuous four-task demonstration.'}
        if references:
            row['reference_receipts'] = references[0]
        row['candidate'] = candidate
        row['start_time'] = start
        packed = gzip.compress(json.dumps(row, separators=(',', ':')).encode(), compresslevel=1, mtime=0)
        target.write_bytes(packed)
        meta.update(status='completed', artifact_sha256=hashlib.sha256(packed).hexdigest(),
            complete=row.get('complete_sequence_success'), qualified=row.get('qualified_complete'),
            component_success=row.get('component_success'), component_valid=row.get('component_valid'),
            failure=row['failure'], steps=row['episode']['steps']['attempts'],
            component_steps=row.get('component_steps'), seconds=row['episode']['duration'],
            component_seconds=row.get('component_seconds'), component_arm_travel_rad=row.get('component_arm_travel_rad'),
            component_metrics=row.get('component_metrics'),
            reference_receipts=row.get('reference_receipts'))
    except BaseException as error:
        meta.update(status='error', error_type=type(error).__name__, error=str(error)[:500])
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.)
        meta['wall_seconds'] = time.perf_counter() - began
        account(args.id, meta)
        (OUT / (args.id + '.metadata.json')).write_text(json.dumps(meta, indent=2) + '\n')
        print(json.dumps(meta), flush=True)


if __name__ == '__main__':
    main()
