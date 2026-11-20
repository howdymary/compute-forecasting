"""Budgeted engineering probes. Saved-state branches are never demo episodes."""
import argparse
import fcntl
import hashlib
import json
import math
import pickle
import time
from pathlib import Path

from ..curriculum.world import ROOT

OUT = ROOT / 'artifacts/smooth-v16-engineering'


def reserve(ident, arguments):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'ledger.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = OUT / 'ledger.json'
        ledger = json.loads(path.read_text()) if path.exists() else {}
        assert ident not in ledger and len(ledger) < 32
        assert sum(v.get('wall_seconds', 900) for v in ledger.values()) < 7200
        ledger[ident] = {'status': 'reserved', 'arguments': arguments, 'physical_rollouts': 1}
        path.write_text(json.dumps(ledger, indent=2)+'\n')


def finish(ident, fields):
    with (OUT / 'ledger.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = OUT / 'ledger.json'
        ledger = json.loads(path.read_text())
        ledger[ident].update(fields)
        path.write_text(json.dumps(ledger, indent=2)+'\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--id', required=True)
    p.add_argument('--kind', choices=['turn', 'descent', 'postit', 'recovery', 'full'], default='turn')
    p.add_argument('--parameters', default='{}')
    args = p.parse_args()
    reserve(args.id, vars(args))
    start = time.perf_counter()
    parameters = json.loads(args.parameters)
    try:
        from .world import restore
        from .navigation import navigate, NavigationParameters
        from ..balanced.sequence import PhysicalStop
        if args.kind=='full':
            from .sequence import run
            def choose(world,domain,task,default,available):
                action=('W2' if task=='alarm' else parameters.get('walk','W4')) if domain=='walk' else parameters.get('recovery','R0') if domain=='recovery' else {'alarm':'F','drawer':'B','laptop':'P2','globe':'G0'}[task]
                world.decisions.append({'t':float(world.d.time),'domain':domain,'task':task,
                    'action':action,'source':'Fixed engineering reference; no training'})
                return action
            full=run(parameters.get('seed',41001),True,choose=choose)
            row={**full,'scope':'Fresh uninterrupted controller-engineering reference, zero new optimizer updates.',
                'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}}
            (OUT/(args.id+'.json')).write_text(json.dumps(row,separators=(',',':')))
            finish(args.id,{'status':'completed','success':full['complete_sequence_success'],
                'failure':full['failure'],'seconds':full['episode']['duration'],
                'steps':full['episode']['steps']['attempts'],'wall_seconds':time.perf_counter()-start})
            print(json.dumps({'success':full['complete_sequence_success'],'failure':full['failure'],
                'steps':full['episode']['steps']['attempts'],'seconds':full['episode']['duration']}),flush=True)
            return
        source = ROOT / 'artifacts/directional-v14/states/full-directional-1-alarm.pickle'
        if args.kind == 'postit':
            source = source.with_name('full-directional-1-drawer.pickle')
        w = restore(pickle.loads(source.read_bytes()), record=True)
        if args.kind=='recovery':
            saved=pickle.loads((ROOT/'.cache/v16-parent-supported-states.pickle').read_bytes())
            w=restore(saved['recovery:'+parameters.get('task','alarm')],record=True)
        if args.kind=='descent':
            source=OUT/parameters.pop('source','book-contact-turn-4.pickle')
            assert source.resolve().parent==OUT.resolve()
            w=restore(pickle.loads(source.read_bytes()),record=True)
        # These source states predate the V15 detector; install it explicitly.
        from .steps import StepCounter
        w.step_counter = StepCounter()
        w.efficiency_segment = 'engineering'
        w.frames = []
        w.capture()
        w.measurements = []
        w.next_measurement = float(w.d.time)
        begun = float(w.d.time)
        result = None
        failure = None
        try:
            if args.kind == 'turn':
                if parameters.pop('clearance', False):
                    from .terrain import clear_and_turn
                    result = clear_and_turn(w, parameters)
                else:
                    result = navigate(w, (*w.d.qpos[:2], -math.pi/2), timeout=35.,
                        label='book-top-turnaround', speed=.04,
                        parameters=NavigationParameters(parked_arms=True, **parameters))
            elif args.kind=='postit':
                from .terrain import cross_postit
                result=cross_postit(w,parameters)
            elif args.kind=='descent':
                from .terrain import forward_descent
                result=forward_descent(w,parameters)
            elif args.kind=='recovery':
                from .recovery import recover
                result=recover(w,parameters.get('task','alarm'),parameters.get('code','R4'))
                if not result['success']:
                    raise PhysicalStop('arm-recovery-failed')
            else:
                raise NotImplementedError(args.kind)
        except PhysicalStop as exc:
            failure = str(exc)
        row = {'scope': 'Saved-state engineering branch, not a continuous demo or trained gain.',
            'source': str(source.relative_to(ROOT)), 'kind': args.kind, 'parameters': parameters,
            'success': failure is None, 'failure': failure, 'result': result,
            'duration_s': float(w.d.time)-begun, 'episode': w.episode(), 'controller':w.walker.description(),
            'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in Path(__file__).parent.glob('*.py')}}
        if failure is None:
            from .world import state
            (OUT / (args.id+'.pickle')).write_bytes(pickle.dumps(state(w)))
        (OUT / (args.id+'.json')).write_text(json.dumps(row, separators=(',', ':')))
        result = {'status': 'completed', 'success': row['success'], 'failure': failure,
            'seconds': row['duration_s'], 'steps': row['episode']['steps']['attempts'],
            'wall_seconds': time.perf_counter()-start}
        finish(args.id, result)
        print(json.dumps(result), flush=True)
    except Exception as exc:
        finish(args.id, {'status': 'failed', 'error': type(exc).__name__, 'wall_seconds': time.perf_counter()-start})
        raise


if __name__ == '__main__':
    main()
