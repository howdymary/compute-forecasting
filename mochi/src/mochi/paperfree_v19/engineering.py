"""Bounded, recorded physical checks before opening the new training campaign."""
import argparse
import copy
import fcntl
import gzip
import hashlib
import json
import pickle
import time
from pathlib import Path

from ..curriculum.world import ROOT
from ..integrations import now
from ..smooth_v16.world import state
from .objective import branch_reward, qualify
from .policy import config, execute, observation
from .sequence import run
from .world import restore


OUT = ROOT / 'artifacts/paperfree-v19-engineering'


def ledger_change(ident, value):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'ledger.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = OUT / 'ledger.json'
        data = json.loads(path.read_text()) if path.exists() else {'attempts': {}}
        if ident not in data['attempts']:
            assert len(data['attempts']) < 12, 'Engineering attempt limit'
        data['attempts'][ident] = value
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(data, indent=2) + '\n')
        temporary.replace(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--id', required=True)
    p.add_argument('--seed', type=int, default=185000)
    p.add_argument('--walk', choices=['W8', 'W9', 'W10'], default='W8')
    p.add_argument('--laptop', choices=['P4', 'P5', 'P6'], default='P4')
    p.add_argument('--snapshot')
    p.add_argument('--domain', default='laptop')
    p.add_argument('--task', default='laptop')
    p.add_argument('--action')
    a = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    result_path = OUT / (a.id + '.json.gz')
    assert not result_path.exists() and not (OUT / (a.id + '.started.json')).exists(), 'Preserve previous attempts'
    meta = {'id': a.id, 'status': 'running', 'at': now(), 'physical_attempts': 1, 'parameters': vars(a)}
    sources = ['src/mochi/paperfree_v19/' + name + '.py' for name in
               ['world', 'policy', 'sequence', 'objective', 'engineering']]
    sources += ['configs/paperfree-v19-controls.json', 'configs/richdesk-v19-paperfree.json']
    meta['sources_at_start'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources}
    (OUT / (a.id + '.started.json')).write_text(json.dumps(meta, indent=2) + '\n')
    ledger_change(a.id, meta)
    started = time.perf_counter()
    captured = {}
    cfg = copy.deepcopy(json.loads((ROOT / 'configs/contact-v18-training.json').read_text()))
    cfg['walking_goal']['moving_median_minimum_sole_clearance_m'] = .0045
    try:
        if a.snapshot:
            from ..balanced.sequence import PhysicalStop
            from ..smooth_v16.objective import branch_metrics
            saved = pickle.loads(gzip.decompress(Path(a.snapshot).read_bytes()))
            w = restore(saved, True)
            begin, index = float(w.d.time), len(w.measurements)
            success, failure, detail, recovery = False, None, {}, None
            try:
                detail = execute(w, a.domain, a.task, a.action)
                success = all(r['success'] for r in detail) if a.domain == 'walk' else detail['success']
                if success and a.domain not in ['walk', 'recovery']:
                    recovery = execute(w, 'recovery', a.task, 'R4')
                    success = success and recovery['success']
            except PhysicalStop as exc:
                failure = str(exc)
            e = w.episode()
            row = {'action': a.action, 'success': bool(success), 'failure': failure,
                'result': detail, 'coupled_recovery': recovery, 'duration_s': float(w.d.time) - begin,
                'steps': w.step_counter.summary(since=begin), 'metrics': branch_metrics(w.measurements[index:]),
                'native_smoothness': e['native_smoothness'], 'longest_unsupported_seconds': e['longest_unsupported_seconds'],
                'fall': w.fall, 'invalid_contact': w.invalid_contact, 'flat_foot_clearance': e['flat_foot_clearance'],
                'episode': e, 'snapshot_sha256': hashlib.sha256(Path(a.snapshot).read_bytes()).hexdigest()}
            row['step_reward'] = branch_reward(a.domain, row)
        else:
            def choose(w, domain, task, default, available):
                action = a.walk if domain == 'walk' else a.laptop if domain == 'laptop' else config()['reference_actions'][domain + ':' + task]
                w.decisions.append({'t': float(w.d.time), 'observation': observation(w, domain, task),
                    'action': action, 'source': 'fixed engineering schedule; zero new optimizer updates'})
                return action

            def capture(w, domain, task):
                if (domain, task) not in [('walk', 'drawer'), ('walk', 'laptop'), ('laptop', 'laptop'), ('walk', 'globe')]:
                    return
                path = OUT / (a.id + '-' + domain + '-' + task + '.pickle.gz')
                with path.open('xb') as f:
                    f.write(gzip.compress(pickle.dumps(state(w, include_history=False)), compresslevel=1))
                captured[domain + ':' + task] = str(path)
                print(json.dumps({'id': a.id, 'captured': domain + ':' + task, 't': float(w.d.time)}), flush=True)

            row = run(a.seed, True, choose, capture)
            qualify(row, cfg)
        row.update(scope='Physical engineering only; zero new Tinker optimizer updates.', captured=captured)
        result_path.write_bytes(gzip.compress(json.dumps(row, separators=(',', ':')).encode(), compresslevel=1))
        meta.update(status='completed', wall_seconds=time.perf_counter() - started,
            complete=row.get('complete_sequence_success'), qualified=row.get('qualified_complete'),
            failure=row.get('failure'), steps=row['episode']['steps']['attempts'],
            physical_seconds=row['episode']['duration'], flat_legs=row['episode'].get('flat_legs'),
            step_reward=row['step_reward'], paper_geometry_present=row['episode']['paper_geometry_present'],
            artifact_sha256=hashlib.sha256(result_path.read_bytes()).hexdigest())
    except BaseException as exc:
        meta.update(status='error', wall_seconds=time.perf_counter() - started, error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        ledger_change(a.id, meta)
        (OUT / (a.id + '.metadata.json')).write_text(json.dumps(meta, indent=2) + '\n')
        print(json.dumps(meta), flush=True)


if __name__ == '__main__':
    main()
