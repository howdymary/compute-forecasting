"""Bounded matched-state probes using measured checkpoint-4 prefix choices."""
import argparse
from dataclasses import replace
import fcntl
import gzip
import hashlib
import json
import pickle
import signal
import time
import types

from ..balanced.sequence import PhysicalStop
from ..control_v8.verification import full_success
from ..contact_v18.policy import PRESSES
from ..curriculum.world import ROOT
from ..integrations import now
from ..paperfree_v19.objective import qualify
from ..paperfree_v19.policy import execute, observation
from ..paperfree_v19.sequence import run
from ..paperfree_v19.world import restore
from ..smooth_v16.world import state

OUT = ROOT / 'artifacts/contact-geometry-v20'


def update(ident, item):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'ledger.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = OUT / 'ledger.json'
        data = json.loads(path.read_text()) if path.exists() else {'attempts': {}}
        if ident not in data['attempts']:
            assert len(data['attempts']) < 8
            assert sum(a.get('wall_seconds', a.get('reserved_seconds', 0.)) for a in data['attempts'].values()) + item['reserved_seconds'] <= 1800.
        data['attempts'][ident] = item
        path.write_text(json.dumps(data, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--id', required=True)
    p.add_argument('--mode', choices=['prefix', 'branch', 'full'], required=True)
    p.add_argument('--seed', type=int, default=212000)
    p.add_argument('--radius', type=float, default=.15)
    p.add_argument('--contact-x', type=float, default=.263)
    a = p.parse_args()
    assert .12 <= a.radius <= .15 and .25 <= a.contact_x <= .263
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / (a.id + '.started.json')).exists()
    reserved = 420. if a.mode != 'branch' else 180.
    meta = {'id': a.id, 'parameters': vars(a), 'created_at': now(), 'status': 'running',
        'reserved_seconds': reserved, 'scope': 'Local diagnostic only; no model training or alteration of C19 results.'}
    (OUT / (a.id + '.started.json')).write_text(json.dumps(meta, indent=2) + '\n')
    update(a.id, meta)
    started = time.perf_counter()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Diagnostic wall limit')))
    signal.setitimer(signal.ITIMER_REAL, reserved)
    source = ROOT / f'.cache/paperfree-v19r1-dev-4-{a.seed}.json.gz'
    original = json.loads(gzip.decompress(source.read_bytes()))
    meta['prefix_source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    actions = {}
    for d in original['model_decisions']:
        o = d['observation']
        task = o.get('station', o.get('task', o['domain']))
        actions[o['domain'] + ':' + task] = d['action']
    cfg = json.loads((ROOT / 'configs/paperfree-v19-training.json').read_text())
    profile = replace(PRESSES['P5'], radius=a.radius, contact_x=a.contact_x)
    prefix = OUT / f'prefix-{a.seed}.pickle.gz'
    captured = False

    def choose(w, domain, task, default, available):
        if a.mode == 'full' and not hasattr(w, '_geometry_contact_override'):
            original_laptop = w.laptop

            def laptop(instance, selected, horizon):
                selected = replace(selected, radius=a.radius, contact_x=a.contact_x) if selected.code == 'P5' else selected
                return original_laptop(selected, horizon)

            w.laptop = types.MethodType(laptop, w)
            w._geometry_contact_override = True
        fallback = 'W10' if domain == 'walk' else 'R4' if domain == 'recovery' else {'alarm': 'H0', 'drawer': 'C', 'laptop': 'P5', 'globe': 'G0'}[task]
        action = 'P5' if domain == 'laptop' else actions.get(domain + ':' + task, fallback)
        w.decisions.append({'t': float(w.d.time), 'observation': observation(w, domain, task),
            'action': action, 'source': 'Recorded checkpoint-4 prefix; fixed declared continuation for diagnostics'})
        return action

    def capture(w, domain, task):
        nonlocal captured
        if domain == 'laptop' and not captured:
            assert not prefix.exists()
            prefix.write_bytes(gzip.compress(pickle.dumps(state(w, include_history=True)), compresslevel=1))
            captured = True
            raise PhysicalStop('diagnostic-prefix-complete')

    try:
        if a.mode in ['prefix', 'full']:
            row = run(a.seed, False, choose, capture if a.mode == 'prefix' else None)
            if a.mode == 'full':
                qualify(row, cfg)
        else:
            w = restore(pickle.loads(gzip.decompress(prefix.read_bytes())), False)
            failure, result = None, {}
            arrivals = json.loads((OUT / f'prefix-{a.seed}.json').read_text())['arrivals']
            try:
                w.contact_force_schedule = True
                w.contact_closing_speed = .40
                result = w.do_task('laptop', profile, max_seconds=32.)
                w.contact_force_schedule = False
                if not result['success']:
                    raise PhysicalStop('laptop-incomplete')
                if not execute(w, 'recovery', 'laptop', 'R4')['success']:
                    raise PhysicalStop('laptop-recovery-incomplete')
                arrivals.extend(execute(w, 'walk', 'globe', 'W10'))
                if not execute(w, 'globe', 'globe', 'G0')['success']:
                    raise PhysicalStop('globe-incomplete')
                if not execute(w, 'recovery', 'globe', 'R4')['success']:
                    raise PhysicalStop('globe-recovery-incomplete')
                until = float(w.d.time) + .5
                while w.d.time < until:
                    w.step()
            except PhysicalStop as exc:
                failure = str(exc)
            e = w.episode()
            row = {'seed': a.seed, 'episode': e, 'arrivals': arrivals, 'failure': failure,
                'direction_metrics': __import__('mochi.smooth_v16.navigation', fromlist=['travel_metrics']).travel_metrics(w.direction_samples),
                'complete_sequence_success': bool(not failure and full_success(e) and not w.invalid_contact and e['efficiency_validity']
                    and len(w.recoveries) == 4 and all(r['success'] for r in w.recoveries)
                    and len(e['flat_legs']) == 3 and all(leg['success'] for leg in e['flat_legs'])
                    and e['maximum_applied_base_force'] == 0 and not e['paper_geometry_present']),
                'diagnostic_contact': result}
            qualify(row, cfg)
        packed = gzip.compress(json.dumps(row, separators=(',', ':')).encode(), compresslevel=1)
        (OUT / (a.id + '.json.gz')).write_bytes(packed)
        if a.mode == 'prefix':
            assert captured
            (OUT / f'prefix-{a.seed}.json').write_text(json.dumps({'arrivals': row['arrivals'], 'source': a.id}) + '\n')
        laptop = row['episode']['results'].get('laptop', {})
        meta.update(status='completed', complete=row.get('complete_sequence_success'), qualified=row.get('qualified_complete'),
            failure=row['failure'], steps=row['episode']['steps']['attempts'],
            laptop={k: laptop.get(k) for k in ['success', 'value', 'duration', 'contacts', 'max_force_n', 'phase', 'contact_progress']},
            artifact_sha256=hashlib.sha256(packed).hexdigest())
    except BaseException as exc:
        meta.update(status='error', error=type(exc).__name__ + ': ' + str(exc))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.)
        meta['wall_seconds'] = time.perf_counter() - started
        update(a.id, meta)
        (OUT / (a.id + '.metadata.json')).write_text(json.dumps(meta, indent=2) + '\n')
        print(json.dumps(meta), flush=True)


if __name__ == '__main__':
    main()
