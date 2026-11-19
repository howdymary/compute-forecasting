"""Export measured navigation comparisons; never rotate a rendered root."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from assess_terrain_training import initial_frame_delta
from build_terrain_training_preview import rounded
from mochi.directional_v14.navigation import travel_metrics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'web/desk/directional-v14'


def measured_direction(episode):
    frames = episode['trajectory']['frames']
    balance = episode['balance_measurements']
    index = previous = 0
    samples = []
    for frame in frames:
        while previous + 1 < len(frames) and frames[previous+1]['t'] <= frame['t'] - .24:
            previous += 1
        while index + 1 < len(balance) and balance[index+1]['t'] <= frame['t']:
            index += 1
        dt = frame['t'] - frames[previous]['t']
        if dt < .2:
            continue
        q = frame['quaternions'][1]
        yaw = math.atan2(2*(q[0]*q[3]+q[1]*q[2]), 1-2*(q[2]*q[2]+q[3]*q[3]))
        samples.append({'t': frame['t'], 'yaw_rad': yaw,
            'phase': 'turn-to-path' if frame['phase'] == 'turn' else 'walk-forward',
            'native_walk': balance[index]['gait_phase'] == 'native-walk' and frame['phase'] in ['walk', 'turn'],
            'cycle_averaged_velocity_xy': [(frame['positions'][1][i]-frames[previous]['positions'][1][i])/dt for i in [0,1]]})
    return travel_metrics(samples)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--corner-before', default='corner-baseline-1')
    p.add_argument('--corner-after', default='corner-directional-4')
    p.add_argument('--full')
    args = p.parse_args()
    directory = ROOT / 'artifacts/directional-v14'
    pairs = [('desk-corner', 'A turn at the desk corner', 'Isolated navigation probe, starting on the flat desk.',
        directory/(args.corner_before+'.json'), directory/(args.corner_after+'.json'))]
    if args.full:
        pairs.append(('four-tasks', 'One continuous four-task route',
            'Clock → drawer → laptop → globe. Validated backward book descent and short fixture-clearance steps are retained.',
            ROOT/'artifacts/terrain-v12/continuous-four-task-reference-2.json', directory/(args.full+'.json')))
    validated = []
    for ident, label, scope, before_path, after_path in pairs:
        before, after = [json.loads(p.read_text()) for p in [before_path, after_path]]
        assert all(r.get('success', r.get('complete_sequence_success', False)) for r in [before, after])
        if ident == 'four-tasks':
            assert after['complete_sequence_success'] and after['resume_source'] is None
        a, b = before['episode'], after['episode']
        assert a['scenario']['seed'] == b['scenario']['seed'] and a['scene'] == b['scene']
        assert initial_frame_delta(a['trajectory']['frames'][0], b['trajectory']['frames'][0]) <= 1e-12
        assert a['maximum_applied_base_force'] == b['maximum_applied_base_force'] == 0
        validated.append((ident, label, scope, before, after, before_path, after_path))
    OUT.mkdir(parents=True, exist_ok=True)
    cases = []
    for ident, label, scope, before, after, before_path, after_path in validated:
        records = []
        for side, row, path in [('before', before, before_path), ('after', after, after_path)]:
            e = row['episode']
            keys = ['scenario','scene','events','results','fall','invalid_contact','duration','maximum_applied_base_force',
                    'balance_metrics','foot_slip_estimate_m','final_object_states','final_object_speeds','trajectory','recoveries']
            clip = {k:e[k] for k in keys if k in e}
            clip['balance_measurements'] = [{k:v for k,v in m.items() if k in ['t','phase','gait_phase','roll_rad','loads_n']} for m in e['balance_measurements']]
            name = ident+'-'+side+'.json.gz'
            payload = gzip.compress(json.dumps(rounded(clip), separators=(',', ':')).encode(), compresslevel=9, mtime=0)
            (OUT/name).write_bytes(payload)
            records.append({'file': name, 'sha256': hashlib.sha256(payload).hexdigest(),
                'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'complete': True, 'duration_s': e['duration'], 'direction_metrics': measured_direction(e),
                'task_results': {t:r['success'] for t,r in e['results'].items()},
                'fall': e['fall'], 'forbidden_contact': e['invalid_contact']})
        cases.append({'id': ident, 'label': label, 'scope': scope, 'scene': before['episode']['scene'],
                      'seed': before['seed'], 'before': records[0], 'after': records[1]})
    report = {'study': 'mochi-directional-v14', 'scope': 'Navigation controller engineering; zero new Tinker optimizer updates. Fixed pretrained native gait. Actual MuJoCo body trajectories.',
        'cases': cases, 'default_case': 'desk-corner',
        'note': 'Both panes use the same physical initial state and playback speed. Every pane is an uninterrupted rollout. Display coordinates are rounded to six decimals; raw simulation archives and failed attempts are retained.',
        'training': {'run': 'https://github.com/howdymary/mochi-demo/actions/runs/44600829444',
            'note': 'The active V13 training comparison keeps its previous navigation frozen. This turning refinement is evaluated separately.'}}
    (OUT/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'cases':len(cases),'recordings':len(cases)*2,'has_full_route':bool(args.full)}))


if __name__ == '__main__':
    main()
