"""Export measured V22 comparisons, including failed motion candidates."""
import copy
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from mochi.smooth_v16.public import rounded
from mochi.visual_motion_v22.metrics import arm_smoothness

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'artifacts/visual-motion-v22'
OUT = ROOT / 'web/desk/visual-motion-v22'
EVIDENCE = ROOT / 'evidence/visual-motion-v22'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percent(value):
    return 'unmeasured' if value is None else f'{value * 100:.3f}%'


def repository_paths(value):
    if isinstance(value, dict):
        return {key: repository_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [repository_paths(item) for item in value]
    return value.replace(str(ROOT.parent) + '/', '') if isinstance(value, str) else value


def full_quality(row):
    if 'component_domain' in row:
        return []
    e = row['episode']
    limits = json.loads((ROOT / 'configs/paperfree-v19-training.json').read_text())['smoothness']
    checks = []
    for name, value, limit in [('roll_rms', e['balance_metrics']['roll_rms_deg'], limits['roll_rms_degrees_max']),
        ('roll_peak', e['balance_metrics']['roll_peak_deg'], limits['roll_peak_degrees_max']),
        ('lateral_rms', e['balance_metrics']['lateral_rms_m'], limits['path_lateral_rms_m_max']),
        ('lateral_range', e['balance_metrics']['lateral_peak_to_peak_m'], limits['path_lateral_peak_to_peak_m_max']),
        ('sequence_time', e['duration'], limits['sequence_time_seconds_max']),
        ('loaded_foot_travel', sum(e['foot_slip_estimate_m'].values()), limits['loaded_contact_travel_estimate_m_max']),
        ('native_acceleration', e['native_smoothness']['sampled_acceleration_rms_rad_s2'], limits['native_acceleration_rms_max']),
        ('native_torque_change', e['native_smoothness']['sampled_torque_change_rms_nm'], limits['native_torque_change_rms_max'])]:
        checks.append({'name': name, 'value': value, 'maximum': limit, 'passed': value is not None and value <= limit})
    fraction = row['direction_metrics']['forward_facing_fraction']
    checks.append({'name': 'forward_facing_fraction', 'value': fraction, 'minimum': .9,
        'passed': fraction is not None and fraction >= .9})
    checks.append({'name': 'three_clearance_qualified_flat_legs', 'passed': len(e['flat_legs']) == 3 and all(
        v['success'] and v['moving_swings'] >= 2 and v['moving_minimum_sole_clearance_m'] >= .0045 for v in e['flat_legs'])})
    return checks


def summarize(row):
    episode = row['episode']
    component = 'component_domain' in row
    recovery = []
    for event in episode['events']:
        if event.get('phase') != 'recover' or event.get('t', 0) < row.get('start_time', 0):
            continue
        end, duration = event['t'], event.get('duration_s', 0)
        recovery.append({'task': event.get('task'), 'success': event['success'], 'seconds': duration,
            'smoothness': arm_smoothness(episode, end - duration, end)})
    return {'seed': row['seed'], 'component': component, 'domain': row.get('component_domain'),
        'complete': row.get('complete_sequence_success'),
        'success': bool(row.get('component_valid') if component else row.get('qualified_complete')),
        'failure': row['failure'], 'duration': row.get('component_seconds', episode['duration']),
        'steps': row.get('component_steps', episode['steps'])['attempts'],
        'arm_travel_rad': row.get('component_arm_travel_rad', episode.get('intertask_arm_joint_travel_rad')),
        'component_metrics': row.get('component_metrics'), 'component_slip_m': row.get('component_slip_m'),
        'arm_smoothness': arm_smoothness(episode, row.get('start_time', 0)),
        'recovery_segments': recovery, 'native_smoothness': episode.get('native_smoothness'),
        'balance_metrics': episode.get('balance_metrics'), 'maximum_applied_base_force': episode['maximum_applied_base_force'],
        'paper_geometry_present': episode['paper_geometry_present'],
        'task_success': {k: v['success'] for k, v in episode['results'].items()},
        'invalid_contact': episode.get('invalid_contact'), 'reference_receipts': row.get('reference_receipts')}


def clip(row):
    episode = row['episode']
    out = {k: copy.deepcopy(v) for k, v in episode.items()
        if k not in ['control_telemetry', 'book_motion_samples', 'balance_measurements']}
    start = row.get('start_time', 0)
    out['balance_measurements'] = [{k: v for k, v in sample.items()
        if k in ['t', 'phase', 'gait_phase', 'roll_rad', 'loads_n', 'step_category']}
        for sample in episode['balance_measurements'] if sample['t'] >= start]
    out['model_decisions'] = [copy.deepcopy(d) for d in episode['decisions'] if d['t'] >= start and 'observation' in d]
    if 'component_domain' in row:
        out['duration'] = row['component_seconds']
        out['scope'] = row['scope']
        out['results'] = {}
        out['events'] = [v for v in out['events'] if v.get('t', -1) >= start]
        out['decisions'] = [v for v in out['decisions'] if v['t'] >= start]
        out['step_events'] = [v for v in out['step_events'] if v['detected_t'] >= start]
        out['steps'] = row['component_steps']
        out['recoveries'] = [v for v in out['recoveries'] if v.get('task') == 'laptop'] if row['component_domain'] == 'recovery' else []
        for items, keys in [(out['trajectory']['frames'], ['t']), (out['events'], ['t']),
                            (out['decisions'], ['t']), (out['model_decisions'], ['t']),
                            (out['balance_measurements'], ['t']),
                            (out['step_events'], ['start_t', 'detected_t', 'touchdown_t', 'verified_t'])]:
            for item in items:
                for key in keys:
                    if key in item:
                        item[key] -= start
        assert -.001 <= out['trajectory']['frames'][0]['t'] <= .1
    else:
        assert out['trajectory']['frames'][0]['t'] < .1
    assert out['maximum_applied_base_force'] == 0 and not out['paper_geometry_present']
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-running', action='store_true', help='Local preview only; final export requires all attempts to finish')
    options = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    ledger = json.loads((SOURCE / 'physics/ledger.json').read_text())
    assert options.allow_running or not any(v['status'] == 'running' for v in ledger['attempts'].values()), 'Wait for physical attempts'
    records, metadata, numerical = {}, {}, {}
    for ident, meta in ledger['attempts'].items():
        if meta['status'] != 'completed':
            continue
        path = SOURCE / 'physics' / (ident + '.json.gz')
        assert digest(path) == meta['artifact_sha256']
        row = json.loads(gzip.decompress(path.read_bytes()))
        records[ident] = summarize(row)
        records[ident]['quality_checks'] = full_quality(row)
        records[ident]['quality_failures'] = [v['name'] for v in records[ident]['quality_checks'] if not v['passed']]
        windows = ([{'since': row['start_time'], 'until': row['episode']['duration'], 'scope': row['component_domain']}]
            if 'component_domain' in row else
            [{'since': v['t'] - v['duration_s'], 'until': v['t'], 'scope': 'recovery:' + v['task']}
             for v in row['episode']['events'] if v.get('phase') == 'recover'])
        numerical[ident] = []
        for window in windows:
            samples = [{'t': v['t'], 'q': v['q']} for v in row['episode']['control_telemetry']
                if window['since'] <= v['t'] <= window['until']]
            numerical[ident].append({**window, 'control_telemetry': samples,
                'measurements': arm_smoothness({'control_telemetry': samples})})
        payload = gzip.compress(json.dumps(rounded(clip(row)), separators=(',', ':')).encode(), compresslevel=6, mtime=0)
        file = ident + '.json.gz'
        (OUT / file).write_bytes(payload)
        metadata[ident] = {**{k: records[ident][k] for k in ['success', 'complete', 'failure', 'duration', 'steps', 'component']},
            'arm_jerk_rms': records[ident]['arm_smoothness']['jerk_rms_rad_s3'],
            'arm_travel_rad': records[ident]['arm_smoothness'].get('travel_rad'),
            'quality_failures': records[ident]['quality_failures'],
            'forward_facing_fraction': row.get('direction_metrics', {}).get('forward_facing_fraction'),
            'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload),
            'source_artifact_sha256': meta['artifact_sha256']}
    cases = []

    def pair(ident, label, left, right, left_label, right_label, title, detail, component=True):
        if left not in metadata or right not in metadata:
            return
        a, b = ledger['attempts'][left], ledger['attempts'][right]
        if component:
            assert a['snapshot_sha256'] == b['snapshot_sha256']
        else:
            assert a['arguments']['seed'] == b['arguments']['seed']
        cases.append({'id': ident, 'label': label, 'before': left + '.json.gz', 'after': right + '.json.gz',
            'before_meta': metadata[left], 'after_meta': metadata[right],
            'before_label': left_label, 'after_label': right_label,
            'scope': ('RESTORED-STATE COMPONENT · Same saved physical state, same rendering and physical-time playback. This is not a full four-task rollout.' if component else
                'CONTINUOUS FOUR-TASK ATTEMPTS · Matched seed, scene, initial state and playback speed. No cuts or state restoration within either attempt. Failures stop where they occur.'),
            'finding_title': title, 'finding_detail': detail})

    recovery_a, recovery_b = records['recovery-parent-221000'], records['recovery-smooth-221000']
    jerk_reduction = 100 * (1 - recovery_b['arm_smoothness']['jerk_rms_rad_s3'] / recovery_a['arm_smoothness']['jerk_rms_rad_s3'])
    time_increase = 100 * (recovery_b['duration'] / recovery_a['duration'] - 1)
    pair('recovery-component', 'Arm recovery: matched development state', 'recovery-parent-221000', 'recovery-smooth-221000',
        'FROZEN R4 RECOVERY', 'MINK SMOOTH RECOVERY', 'Smoother recovery, longer return.',
        f'Both recoveries passed. Measured arm jerk is {jerk_reduction:.1f}% lower; recovery takes {time_increase:.1f}% longer ({recovery_a["duration"]:.2f} → {recovery_b["duration"]:.2f} s). Arm travel is essentially unchanged. One development component, not a generalization claim.')
    pair('gmr-walk', 'GMR walking: mixed development result', 'walk-parent-221000', 'walk-gmr-legs-221000',
        'FROZEN NATIVE WALKING', 'BOUNDED GMR LEG REFERENCE', 'Straight walking did not improve.',
        'Both components passed. The GMR residual used 112 versus 110 steps and slightly more time, sliding and sway. Native gait weights were fixed. This candidate was not promoted.')
    pair('gmr-turn', 'GMR turning: mixed development result', 'turn-parent-221000', 'turn-gmr-legs-221000',
        'FROZEN NATIVE TURNING', 'BOUNDED GMR LEG REFERENCE', 'Fewer steps and less sliding, with more sway.',
        'This one development component used 130 versus 132 steps, about 29% less loaded-foot sliding and about 3% lower measured arm jerk. Torso sway and native joint acceleration increased. This does not establish a general walking improvement.')
    pair('rejected-walking', 'Rejected: arm reference during walking', 'walk-parent-221000', 'walk-mink-r1-221000',
        'FROZEN NATIVE WALKING', 'REJECTED MINK ARM BLEND', 'A quieter arm reference caused contact.',
        'The baseline reached the laptop. The candidate contacted the drawer and was rejected. A shorter failed attempt does not count as a reduction in steps or time.')
    for partition, seeds in [('dev', [225000, 225001]), ('fresh', list(range(226000, 226004)))]:
        for seed in seeds:
            left, right = f'full-parent-{partition}-{seed}', f'full-mink-{partition}-{seed}'
            if left not in records or right not in records:
                continue
            a, b = records[left], records[right]
            title = ('Both completed all four tasks.' if a['success'] and b['success'] else
                'Candidate completed; reference did not qualify.' if b['success'] else
                'Reference completed; candidate did not qualify.' if a['success'] else
                'Neither attempt passed every quality check.')
            pair(f'{partition}-{seed}', ('Fresh test' if partition == 'fresh' else 'Development') + f' continuous scenario {seed}',
                left, right, 'FROZEN C21 REFERENCE', 'MINK RECOVERY CANDIDATE',
                title,
                f'Reference: {a["steps"]} steps, {a["duration"]:.2f} s. Candidate: {b["steps"]} steps, {b["duration"]:.2f} s. '
                'Only arm recovery changed. Walking, route targets, manipulation profiles and native gait weights stayed fixed. '
                + (f'Forward-facing fraction: reference {percent(metadata[left]["forward_facing_fraction"])}, candidate {percent(metadata[right]["forward_facing_fraction"])}; 90% required. ' if 'forward_facing_fraction' in a['quality_failures'] + b['quality_failures'] else '')
                + ('Quality failures: reference ' + (', '.join(a['quality_failures']) or 'none') + '; candidate ' + (', '.join(b['quality_failures']) or 'none') + '. ' if a['quality_failures'] or b['quality_failures'] else '')
                + 'Numerical results are in the evidence report.', False)
    scene = json.loads((OUT / 'appearance-manifest.json').read_text())['scene']
    manifest = {'study': 'mochi-visual-motion-v22', 'scene': scene, 'scenarios': cases,
        'default_scenario': 'recovery-component',
        'summary': 'Compare real physical motion tests. The gentler mink arm return improved one matched component. GMR walking and turning tests were mixed; failed candidates and full-sequence comparisons remain visible.'}
    (OUT / 'motion-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    report = json.loads((OUT / 'report.json').read_text())
    report.update(recordings={k + '.json.gz': v for k, v in metadata.items()}, outcomes=records,
        experiments=repository_paths(ledger['attempts']), physical_attempts=len(ledger['attempts']),
        evaluation_complete=not any(v['status'] == 'running' for v in ledger['attempts'].values()),
        physical_wall_seconds=sum(v.get('wall_seconds', v['reserved_seconds']) for v in ledger['attempts'].values()),
        optimizer_updates=0, native_gait_updates=0,
        motion_summary=f'{len(ledger["attempts"])} physical attempts; zero optimizer updates. GMR supplied a real retargeted human-motion reference. mink solved bounded joint references. The gentler arm-return component lowered measured jerk by {jerk_reduction:.1f}% with {time_increase:.1f}% more time. Walking tests were mixed; no new native gait was trained.')
    report['confounded_diagnostics'] = ['walk-gmr-221000', 'walk-mink-221000', 'walk-mink-gated-221000',
        'walk-gmr-gated-221000', 'turn-gmr-gated-221000']
    report['confound'] = 'Initial adapter clipped native actuator commands even with no reference blend. These attempts are retained, excluded from efficacy claims and followed by corrected runs and an exact zero-blend control.'
    report['causal_limits'] = ['Duration and mink IK were changed together; no solver-only benefit is identified.',
        'GMR calibration and native-cycle indexing are unvalidated prototypes; these results do not evaluate a trained imitation controller.',
        'Four fresh cases in one simulated layout cannot establish broad robustness or hardware transfer.']
    report['reference_environment'] = json.loads((EVIDENCE / 'reference-environment.json').read_text())
    numbers = gzip.compress(json.dumps(numerical, separators=(',', ':')).encode(), compresslevel=6, mtime=0)
    for target in [OUT / 'arm-telemetry.json.gz', EVIDENCE / 'arm-telemetry.json.gz']:
        target.write_bytes(numbers)
    report['arm_measurement_data'] = {'file': 'arm-telemetry.json.gz', 'sha256': hashlib.sha256(numbers).hexdigest(),
        'scope': 'Unrounded measured arm joint positions and timestamps for every component and each full-route recovery phase. Recompute finite differences with visual_motion_v22/metrics.py. These are measured joint states, not desired controls.'}
    assessment_path = EVIDENCE / 'assessment.json'
    if assessment_path.exists():
        report['assessment'] = json.loads(assessment_path.read_text())
        a = report['assessment']
        if a['fresh_pairs']:
            report['motion_summary'] += f' On {a["fresh_pairs"]} fresh pairs, qualified completion was {a["fresh_parent_qualified"]}/{a["fresh_pairs"]} for the reference and {a["fresh_candidate_qualified"]}/{a["fresh_pairs"]} for the recovery candidate.'
            qualified = [p for p in a['pairs'] if p['partition'] == 'fresh' and p['parent_qualified'] and p['candidate_qualified']]
            if len(qualified) == 1:
                p = qualified[0]
                report['motion_summary'] += f' The only mutually qualified fresh pair used {p["candidate_steps"]} versus {p["parent_steps"]} steps and took {p["candidate_seconds"] - p["parent_seconds"]:.2f} seconds longer. No complete-route efficiency gain was demonstrated.'
            manifest['summary'] = f'Fresh complete-route qualification: reference {a["fresh_parent_qualified"]}/{a["fresh_pairs"]}, recovery candidate {a["fresh_candidate_qualified"]}/{a["fresh_pairs"]}. The matched development recovery component had {jerk_reduction:.1f}% lower measured jerk with {time_increase:.1f}% more time. GMR walking and turning results were mixed.'
            (OUT / 'motion-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for path in [OUT / 'report.json', EVIDENCE / 'results.json']:
        path.write_text(json.dumps(report, indent=2) + '\n')
    (EVIDENCE / 'recording-manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({'recordings': len(metadata), 'motion_comparisons': len(cases), 'jerk_reduction_percent': jerk_reduction}))


if __name__ == '__main__':
    main()
