"""Bounded local physical diagnostics and complete from-reset attempts."""
import argparse
from contextlib import ExitStack
import fcntl
import gzip
import hashlib
import json
import pickle
import signal
import time
from pathlib import Path

from mochi.balanced.sequence import PhysicalStop
from mochi.curriculum.world import ROOT
from mochi.integrations import now
from mochi.paperfree_v19 import policy, sequence
from mochi.paperfree_v19.objective import qualify
from mochi.paperfree_v19.world import restore
from mochi.paperfree_v19r1.objective import valid_branch
from mochi.smooth_v16.objective import branch_metrics
from mochi.smooth_v16.world import state
from .controls import apply, validate

OUT = ROOT / 'artifacts/inkling-v21/physics'


def account(ident, value):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'ledger.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        target = OUT / 'ledger.json'
        ledger = json.loads(target.read_text()) if target.exists() else {'attempts': {}}
        if ident not in ledger['attempts']:
            assert len(ledger['attempts']) < 24, 'Physical attempt ceiling'
            used = sum(v.get('wall_seconds', v['reserved_seconds']) for v in ledger['attempts'].values())
            assert used + value['reserved_seconds'] <= 10800, 'Simulation time ceiling'
        ledger['attempts'][ident] = value
        target.write_text(json.dumps(ledger, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--id', required=True)
    p.add_argument('--mode', choices=['full', 'prefix', 'branch'], required=True)
    p.add_argument('--seed', type=int, default=221000)
    p.add_argument('--candidate', action='append', default=[])
    p.add_argument('--snapshot')
    p.add_argument('--domain', choices=['walk', 'laptop', 'recovery'], default='laptop')
    p.add_argument('--task', choices=['laptop', 'globe'], default='laptop')
    p.add_argument('--laptop-action', choices=['P5', 'P6'], default='P5')
    a = p.parse_args()
    candidates = [validate(json.loads(Path(f).read_text())) for f in a.candidate]
    assert len(candidates) <= 3
    cfg = json.loads((ROOT / 'configs/paperfree-v19-training.json').read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / (a.id + '.json.gz')
    assert not target.exists() and not (OUT / (a.id + '.started.json')).exists()
    reserved = 180. if a.mode == 'branch' else 600.
    meta = {'id': a.id, 'created_at': now(), 'status': 'running', 'reserved_seconds': reserved,
        'arguments': vars(a), 'candidates': candidates,
        'scope': f'Inkling-proposed numeric controller engineering. Reference action vector H0/C/{a.laptop_action}/G0, W10 and R4, with explicit candidate overrides; no new trained weights or live neural selection during physics.',
        'experiment_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'adapter_sha256': hashlib.sha256((Path(__file__).with_name('controls.py')).read_bytes()).hexdigest()}
    (OUT / (a.id + '.started.json')).write_text(json.dumps(meta, indent=2) + '\n')
    account(a.id, meta)
    began = time.perf_counter()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Physical attempt wall limit')))
    signal.setitimer(signal.ITIMER_REAL, reserved)
    captures = {}

    def choose(w, domain, task, default, available):
        action = 'W10' if domain == 'walk' else 'R4' if domain == 'recovery' else {'alarm': 'H0', 'drawer': 'C', 'laptop': a.laptop_action, 'globe': 'G0'}[task]
        w.decisions.append({'t': float(w.d.time), 'observation': policy.observation(w, domain, task),
            'action': action, 'source': 'Declared fixed control vector for engineering comparison',
            'candidate_ids': [c['id'] for c in candidates]})
        return action

    def capture(w, domain, task):
        if a.mode == 'prefix' and (domain, task) in [('walk', 'laptop'), ('laptop', 'laptop'), ('walk', 'globe'), ('recovery', 'laptop')]:
            path = OUT / f'{a.id}-{domain}-{task}.pickle.gz'
            assert not path.exists()
            path.write_bytes(gzip.compress(pickle.dumps(state(w, include_history=True)), compresslevel=1))
            captures[domain + ':' + task] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    try:
        with ExitStack() as stack:
            for candidate in candidates:
                stack.enter_context(apply(candidate))
            if a.mode != 'branch':
                row = sequence.run(a.seed, True, choose, capture)
                qualify(row, cfg)
                row['model_decisions'] = row['episode'].get('decisions', [])
            else:
                path = Path(a.snapshot)
                saved = path.read_bytes()
                meta['snapshot_sha256'] = hashlib.sha256(saved).hexdigest()
                w = restore(pickle.loads(gzip.decompress(saved)), True)
                begin, index = float(w.d.time), len(w.measurements)
                failure, detail, withdrawal = None, {}, None
                success = False
                try:
                    # Pose proposals are tracked through actuators, never assigned.
                    if a.domain == 'laptop' and any(c['domain'] == 'laptop' and any(k in c['changes'] for k in ['station_x_m', 'station_y_m', 'station_position_tolerance_m']) for c in candidates):
                        from mochi.smooth_v16.navigation import NavigationParameters
                        goal = policy.config()['routes']['laptop'][-1]
                        detail['pose_arrival'] = policy.navigate(w, goal, speed=.06, stop=True, label='laptop-station',
                            parameters=NavigationParameters(**policy.walking_profile('W10', 'laptop')['navigation']))
                    action = 'W10' if a.domain == 'walk' else 'R4' if a.domain == 'recovery' else a.laptop_action
                    result = policy.execute(w, a.domain, a.task, action)
                    detail['result'] = result
                    success = all(r['success'] for r in result) if a.domain == 'walk' else result['success']
                    if success and a.domain == 'laptop':
                        withdrawal = policy.execute(w, 'recovery', 'laptop', 'R4')
                        success = success and withdrawal['success']
                except PhysicalStop as exc:
                    failure = str(exc)
                episode = w.episode()
                local = {'success': bool(success), 'fall': w.fall, 'invalid_contact': w.invalid_contact,
                    'metrics': branch_metrics(w.measurements[index:]),
                    'longest_unsupported_seconds': episode['longest_unsupported_seconds'],
                    'flat_foot_clearance': episode['flat_foot_clearance']}
                row = {'seed': a.seed, 'failure': failure, 'episode': episode, 'detail': detail,
                    'withdrawal': withdrawal, 'branch_success': bool(success),
                    'branch_valid': valid_branch(local, a.domain),
                    'branch_steps': w.step_counter.summary(since=begin), 'branch_seconds': float(w.d.time) - begin,
                    'complete_sequence_success': None, 'qualified_complete': None,
                    'scope': 'Matched restored-state diagnostic. Not a continuous from-reset demonstration.'}
        row['engineering_candidates'] = candidates
        row['controller_scope'] = meta['scope']
        packed = gzip.compress(json.dumps(row, separators=(',', ':')).encode(), compresslevel=1, mtime=0)
        target.write_bytes(packed)
        e = row['episode']
        meta.update(status='completed', artifact_sha256=hashlib.sha256(packed).hexdigest(), captures=captures,
            complete=row['complete_sequence_success'], qualified=row['qualified_complete'],
            branch_success=row.get('branch_success'), branch_valid=row.get('branch_valid'),
            failure=row['failure'], steps=e['steps']['attempts'], branch_steps=row.get('branch_steps'),
            seconds=e['duration'], branch_seconds=row.get('branch_seconds'),
            tasks={t: {k: v.get(k) for k in ['success', 'value', 'duration', 'max_force_n', 'phase']} for t, v in e['results'].items()})
    except BaseException as exc:
        meta.update(status='error', error_type=type(exc).__name__, error=str(exc)[:300], captures=captures)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.)
        meta['wall_seconds'] = time.perf_counter() - began
        account(a.id, meta)
        (OUT / (a.id + '.metadata.json')).write_text(json.dumps(meta, indent=2) + '\n')
        print(json.dumps(meta), flush=True)


if __name__ == '__main__':
    main()
