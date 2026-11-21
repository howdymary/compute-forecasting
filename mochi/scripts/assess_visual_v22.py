"""Independently verify preservation, paired comparisons and numerical claims."""
import gzip
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

from mochi.visual_motion_v22.metrics import arm_smoothness
from mochi.paperfree_v19.objective import qualify

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'artifacts/visual-motion-v22'
EVIDENCE = ROOT / 'evidence/visual-motion-v22'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(ident):
    return json.loads(gzip.decompress((SOURCE / 'physics' / (ident + '.json.gz')).read_bytes()))


def wilson(successes, count):
    if not count:
        return None
    z = 1.959963984540054
    p, denominator = successes / count, 1 + z * z / count
    centre = (p + z * z / (2 * count)) / denominator
    radius = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / denominator
    return [centre - radius, centre + radius]


def main():
    freeze = json.loads((SOURCE / 'baseline-freeze.json').read_text())
    changed = [name for name, h in freeze['frozen_sha256'].items() if digest(ROOT / name) != h]
    assert not changed, changed
    ledger = json.loads((SOURCE / 'physics/ledger.json').read_text())
    assert len(ledger['attempts']) <= 32
    assert all(v['status'] != 'running' for v in ledger['attempts'].values())
    wall = sum(v.get('wall_seconds', v['reserved_seconds']) for v in ledger['attempts'].values())
    assert wall <= 14400
    for ident, entry in ledger['attempts'].items():
        if entry['status'] == 'completed':
            assert digest(SOURCE / 'physics' / (ident + '.json.gz')) == entry['artifact_sha256']
        assert entry['physical_mujoco_version'] == '3.3.7' and entry['optimizer_updates'] == 0
        h = entry['controller_sha256']
        assert digest(SOURCE / 'source' / ('controller-' + h + '.py')) == h
    a, b = load('walk-parent-221000'), load('walk-zero-r1-221000')
    for key in ['trajectory', 'step_events']:
        assert a['episode'][key] == b['episode'][key], key
    for key in ['component_seconds', 'component_steps', 'component_metrics', 'component_arm_travel_rad']:
        assert a[key] == b[key], key
    rec_a, rec_b = load('recovery-parent-221000'), load('recovery-smooth-221000')
    smooth_a = arm_smoothness(rec_a['episode'], rec_a['start_time'])
    smooth_b = arm_smoothness(rec_b['episode'], rec_b['start_time'])
    assert rec_a['component_valid'] and rec_b['component_valid']
    assert smooth_b['jerk_rms_rad_s3'] < smooth_a['jerk_rms_rad_s3']
    pairs = []
    recovery_pairs = []
    for partition, seeds in [('dev', [225000, 225001]), ('fresh', list(range(226000, 226004)))]:
        for seed in seeds:
            ids = [f'full-{v}-{partition}-{seed}' for v in ['parent', 'mink']]
            if not all(ledger['attempts'].get(i, {}).get('status') == 'completed' for i in ids):
                continue
            aa, bb = [load(i) for i in ids]
            cfg = json.loads((ROOT / 'configs/paperfree-v19-training.json').read_text())
            for row in [aa, bb]:
                before = row['qualified_complete']
                qualify(row, cfg)
                assert row['qualified_complete'] == before
                assert row['episode']['maximum_applied_base_force'] == 0
                assert not row['episode']['paper_geometry_present']
            for key in ['positions', 'quaternions', 'objects']:
                assert aa['episode']['trajectory']['frames'][0][key] == bb['episode']['trajectory']['frames'][0][key]
            assert aa['episode']['trajectory']['frames'][0]['t'] < .1
            assert bb['episode']['trajectory']['frames'][0]['t'] < .1
            pairs.append({'partition': partition, 'seed': seed,
                'parent_qualified': aa['qualified_complete'], 'candidate_qualified': bb['qualified_complete'],
                'parent_complete': aa['complete_sequence_success'], 'candidate_complete': bb['complete_sequence_success'],
                'parent_failure': aa['failure'], 'candidate_failure': bb['failure'],
                'parent_steps': aa['episode']['steps']['attempts'], 'candidate_steps': bb['episode']['steps']['attempts'],
                'parent_seconds': aa['episode']['duration'], 'candidate_seconds': bb['episode']['duration']})
            ra = {v['task']: v for v in aa['episode']['events'] if v.get('phase') == 'recover'}
            rb = {v['task']: v for v in bb['episode']['events'] if v.get('phase') == 'recover'}
            for task in sorted(ra.keys() & rb.keys()):
                a, b = ra[task], rb[task]
                ma = arm_smoothness(aa['episode'], a['t'] - a['duration_s'], a['t'])
                mb = arm_smoothness(bb['episode'], b['t'] - b['duration_s'], b['t'])
                recovery_pairs.append({'partition': partition, 'seed': seed, 'task': task,
                    'both_successful': a['success'] and b['success'],
                    'parent_seconds': a['duration_s'], 'candidate_seconds': b['duration_s'],
                    'parent_jerk_rms': ma['jerk_rms_rad_s3'], 'candidate_jerk_rms': mb['jerk_rms_rad_s3'],
                    'parent_travel_rad': ma.get('travel_rad'), 'candidate_travel_rad': mb.get('travel_rad')})
    fresh = [p for p in pairs if p['partition'] == 'fresh']
    selected = json.loads((SOURCE / 'selection-freeze.json').read_text()) if (SOURCE / 'selection-freeze.json').exists() else None
    if fresh:
        assert selected is not None and len(fresh) == 4
        for file, h in selected['source_sha256'].items():
            assert digest(ROOT / file) == h, file
        selection_time = datetime.fromisoformat(selected['created_at']).timestamp()
        assert all((SOURCE / 'physics' / (f'full-{side}-fresh-{seed}.started.json')).stat().st_mtime >= selection_time
            for side in ['parent', 'mink'] for seed in range(226000, 226004))
    audit = {'study': 'mochi-visual-motion-v22', 'preserved_files': len(freeze['frozen_sha256']),
        'changed_frozen_files': changed, 'zero_blend_exact_trajectory_match': True,
        'physical_attempts': len(ledger['attempts']), 'wall_seconds': wall,
        'optimizer_updates': 0, 'native_gait_updates': 0,
        'recovery_component_jerk_reduction_pct': 100 * (1 - smooth_b['jerk_rms_rad_s3'] / smooth_a['jerk_rms_rad_s3']),
        'recovery_component_time_increase_pct': 100 * (rec_b['component_seconds'] / rec_a['component_seconds'] - 1),
        'pairs': pairs, 'recovery_phase_pairs': recovery_pairs, 'fresh_pairs': len(fresh),
        'fresh_parent_qualified': sum(p['parent_qualified'] for p in fresh),
        'fresh_candidate_qualified': sum(p['candidate_qualified'] for p in fresh),
        'paired_qualified_fresh': sum(p['parent_qualified'] and p['candidate_qualified'] for p in fresh)}
    audit['descriptive_95pct_wilson'] = {side: wilson(sum(p[side + '_qualified'] for p in fresh), len(fresh))
        for side in ['parent', 'candidate']}
    audit['uncertainty_scope'] = 'Four cases from one simulated desk layout. These descriptive binomial intervals do not establish broad environment or hardware generalization.'
    (EVIDENCE / 'assessment.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit))


if __name__ == '__main__':
    main()
