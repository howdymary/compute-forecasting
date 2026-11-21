"""Export complete from-reset controller experiments, never restored branches."""
import gzip
import hashlib
import json
from pathlib import Path

from build_paperfree_v19_demo import metadata
from mochi.smooth_v16.public import rounded

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'artifacts/inkling-v21'
OUT = ROOT / 'web/desk/inkling-v21'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ledger = json.loads((SOURCE / 'physics/ledger.json').read_text())
    files, scenarios, outcomes = {}, [], []
    pairs = [(f'development-{s}', s, f'baseline-prefix-{s}', f'clearance-full-{s}', 'development') for s in [221000, 221001]]
    pairs += [(f'held-out-{s}', s, f'fresh-parent-{s}', f'fresh-clearance-{s}', 'held_out') for s in range(223000, 223004)]
    for ident, seed, before_name, after_name, partition in pairs:
        if not all(ledger['attempts'].get(n, {}).get('status') == 'completed' for n in [before_name, after_name]):
            continue
        versions = []
        for side, name in [('parent', before_name), ('selected', after_name)]:
            meta = ledger['attempts'][name]
            assert meta['arguments']['mode'] in ['prefix', 'full']
            packed = (SOURCE / 'physics' / (name + '.json.gz')).read_bytes()
            assert hashlib.sha256(packed).hexdigest() == meta['artifact_sha256']
            row = json.loads(gzip.decompress(packed))
            e = row['episode']
            assert e['trajectory']['frames'][0]['t'] < .1
            assert not e['paper_geometry_present'] and e['maximum_applied_base_force'] == 0
            row['model_decisions'] = [d for d in e['decisions'] if 'observation' in d]
            clip = {k: v for k, v in e.items() if k not in ['control_telemetry', 'book_motion_samples', 'balance_measurements']}
            clip['balance_measurements'] = [{k: v for k, v in m.items() if k in ['t', 'phase', 'gait_phase', 'roll_rad', 'loads_n', 'step_category']} for m in e['balance_measurements']]
            clip['model_decisions'] = row['model_decisions']
            raw = json.dumps(rounded(clip), separators=(',', ':')).encode()
            compressed = gzip.compress(raw, compresslevel=6, mtime=0)
            file = name + '.json.gz'
            (OUT / file).write_bytes(compressed)
            laptop = meta['arguments'].get('laptop_action', 'P5')
            fingerprint = hashlib.sha256(json.dumps({'laptop': laptop, 'candidates': meta['candidates']}, sort_keys=True).encode()).hexdigest()
            label = f'FROZEN {laptop} CONTROL REFERENCE' if side == 'parent' else f'INKLING CLEARANCE PROPOSAL · {laptop}'
            files[file] = metadata(row, e, {'checkpoint_id': fingerprint, 'checkpoint_update': 0, 'cumulative_updates': 0},
                {'sha256': hashlib.sha256(compressed).hexdigest(), 'uncompressed_sha256': hashlib.sha256(raw).hexdigest()}, label)
            files[file].update(controller_scope=meta['scope'], adapter_sha256=meta['adapter_sha256'],
                source_artifact_sha256=meta['artifact_sha256'], new_optimizer_updates=0,
                engineering_candidates=meta['candidates'])
            versions.append({'update': 0, 'file': file})
            outcomes.append({'scenario': ident, 'partition': partition, 'side': side, 'complete': row['complete_sequence_success'],
                'qualified': row['qualified_complete'], 'steps': e['steps']['attempts'], 'seconds': e['duration'], 'failure': row['failure']})
        scenarios.append({'id': ident, 'label': ('Fresh test' if partition == 'held_out' else 'Development') + f' scenario {seed}',
            'partition': partition, 'parent_file': versions[0]['file'], 'versions': versions})
    assert scenarios
    freeze = json.loads((SOURCE / 'selection-freeze.json').read_text())
    model_records = []
    for path in sorted(SOURCE.glob('*.json')):
        d = json.loads(path.read_text())
        if d.get('model') != 'thinkingmachines/Inkling-2-Mini' or not d.get('request_id'):
            continue
        public = {k: v for k, v in d.items() if k != 'memory'}
        if d.get('memory'):
            m = d['memory']
            public['memory_provenance'] = {'actors': m['actors'], 'audiences': m['audiences'], 'reads': m['reads'],
                'records': [{k: v for k, v in x.items() if k != 'payload'} for x in m['records']],
                'source_urls': sorted({s['url'] for batch in m['sources'] for s in batch['sources']})}
        model_records.append(public)
    budget_path = SOURCE / 'budget.json'
    budgets = [x['budget'] for x in model_records if x.get('budget')]
    if budget_path.exists():
        budgets.append(json.loads(budget_path.read_text()))
    budget = max(budgets, key=lambda x: x['model_calls']) if budgets else None
    report = {'study': 'mochi-inkling-v21', 'model': 'thinkingmachines/Inkling-2-Mini',
        'scope': 'Inference-driven controller engineering. No new optimizer updates or native gait training.',
        'model_receipts': model_records, 'model_budget_latest_snapshot': budget, 'outcomes': outcomes,
        'physical_attempts': len(ledger['attempts']), 'physical_seconds_actual_or_reserved': sum(v.get('wall_seconds', v['reserved_seconds']) for v in ledger['attempts'].values())}
    default = next((s['id'] for s in scenarios if s['partition'] == 'held_out' and files[s['versions'][-1]['file']]['qualified_complete']), scenarios[0]['id'])
    assessment_path = SOURCE / 'assessment.json'
    assessment = json.loads(assessment_path.read_text()) if assessment_path.exists() else None
    if assessment:
        report['assessment'] = assessment
    manifest = {'study': report['study'], 'evaluation_status': 'engineering', 'optimizer_updates_completed': 0,
        'selected_update': 0, 'selection_finalized': True, 'checkpoints': [], 'held_out': None,
        'source_sha': None, 'controller_source_sha256': hashlib.sha256(json.dumps(freeze['frozen_sha256'], sort_keys=True).encode()).hexdigest(),
        'improvement_goal_met': False,
        'engineering_note': f'Inkling 2 Mini proposed a farther post-laptop clearance point after reviewing measured failures. {len(model_records)} retained model-call receipts. These are controller-engineering comparisons with zero new weight updates. Development results and fresh tests are kept separate.',
        'services': {}, 'display_note': 'Uninterrupted MuJoCo simulation replay. Fixed native gait and physical validity checks. This compares control configurations, not newly trained neural checkpoints.',
        'scene': json.loads((ROOT / 'configs/richdesk-v19-paperfree.json').read_text()), 'recordings': files,
        'scenarios': scenarios, 'default_scenario': default}
    if assessment:
        manifest['held_out'] = assessment['held_out']
        manifest['improvement_goal_met'] = assessment['step_goal_met']
        manifest['engineering_note'] += f" Final fresh qualification: reference {assessment['held_out']['parent']['qualified_complete_successes']}/4, clearance {assessment['held_out']['selected']['qualified_complete_successes']}/4. The declared step target was {'met' if assessment['step_goal_met'] else 'not met'}."
    for name, data in [('manifest', manifest), ('report', report)]:
        text = json.dumps(data, indent=2) + '\n'
        assert 'tinker://' not in text
        (OUT / (name + '.json')).write_text(text)
    print(json.dumps({'recordings': len(files), 'scenarios': len(scenarios), 'default': default}))


if __name__ == '__main__':
    main()
