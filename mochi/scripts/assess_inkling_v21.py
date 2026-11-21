"""Recompute the frozen controller pilot from measurements and model receipts."""
import gzip
import hashlib
import json
from pathlib import Path

from mochi.paperfree_v19.objective import paired, summary

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'artifacts/inkling-v21'


def load(name):
    return json.loads(gzip.decompress((SOURCE / 'physics' / (name + '.json.gz')).read_bytes()))


def main():
    freeze = json.loads((SOURCE / 'selection-freeze.json').read_text())
    assert freeze['held_out_opened'] is False
    for name, expected in freeze['frozen_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    start = json.loads((SOURCE / 'final-execution-started.json').read_text())
    assert start['held_out_opened'] and start['selection_sha256'] == hashlib.sha256((SOURCE / 'selection-freeze.json').read_bytes()).hexdigest()
    assert freeze['created_at'] < start['created_at']
    ledger = json.loads((SOURCE / 'physics/ledger.json').read_text())
    attempts = ledger['attempts']
    assert len(attempts) == 24 and all(v['status'] == 'completed' for v in attempts.values())
    seconds = sum(v['wall_seconds'] for v in attempts.values())
    assert seconds <= 10800
    for name, meta in attempts.items():
        data = (SOURCE / 'physics' / (name + '.json.gz')).read_bytes()
        assert hashlib.sha256(data).hexdigest() == meta['artifact_sha256']
        row = json.loads(gzip.decompress(data))
        e = row['episode']
        assert e['maximum_applied_base_force'] == 0 and not e['paper_geometry_present']
        assert len(e['step_events']) == e['steps']['attempts'] == meta['steps']
        assert sum(e['steps']['by_category'].values()) == e['steps']['attempts']
        if meta['arguments']['mode'] != 'branch':
            assert e['trajectory']['frames'][0]['t'] < .1
            assert all(b['t'] > a['t'] for a, b in zip(e['trajectory']['frames'], e['trajectory']['frames'][1:]))
    cfg = json.loads((ROOT / 'configs/paperfree-v19-training.json').read_text())
    cohorts = {
        'parent': [load('fresh-parent-' + str(s)) for s in freeze['held_out_seeds']],
        'selected': [load('fresh-clearance-' + str(s)) for s in freeze['held_out_seeds']],
        'p6_control': [load('fresh-p6-control-' + str(s)) for s in freeze['extra_p6_control_seeds']],
    }
    summaries = {label: summary(rows, cfg) for label, rows in cohorts.items()}
    matched = paired(cohorts['parent'], cohorts['selected'])
    development = {label: summary([load(prefix + str(s)) for s in [221000, 221001]], cfg)
        for label, prefix in [('parent', 'baseline-prefix-'), ('selected', 'clearance-full-')]}
    budget = json.loads((SOURCE / 'budget.json').read_text())
    assert budget['model_calls'] <= 8 and budget['tokens_actual_or_reserved'] <= 200000 and budget['exa_searches'] <= 2
    assert json.loads((ROOT / 'evidence/inkling-v21/access.json').read_text())['available']
    receipts = []
    for p in SOURCE.glob('*.json'):
        d = json.loads(p.read_text())
        if d.get('model') != 'thinkingmachines/Inkling-2-Mini' or not d.get('request_id'):
            continue
        assert d['optimizer_updates'] == d['native_gait_updates'] == 0
        if d['status'] == 'completed':
            assert d['renderer'] == 'tml_v0' and d['input_tokens'] > 0 and d['output_tokens'] > 0
            assert d['output_tokens_sha256']
        receipts.append({'request_id': d['request_id'], 'status': d['status'], 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    assert len(receipts) == budget['model_calls']
    r3 = json.loads((SOURCE / 'measured-review-r3.json').read_text())
    assert any(r['reader_role'] == 'critic' and r['source_id_verified'] and r['cross_agent_use']
        and r['record_id'] == 'mochi-ink21-20261120-r4' for r in r3['memory']['reads'])
    result = {'study': 'mochi-inkling-v21', 'model': 'thinkingmachines/Inkling-2-Mini',
        'new_optimizer_updates': 0, 'native_gait_updates': 0, 'frozen_files_verified': len(freeze['frozen_sha256']),
        'physical_attempts_accounted': len(attempts), 'simulation_seconds_accounted': seconds,
        'model_budget': budget, 'model_receipts': receipts, 'development': development,
        'held_out': summaries, 'paired_held_out': matched,
        'step_goal_met': bool(summaries['selected']['qualified_complete_successes'] == 4 and matched['n'] >= 2
            and matched['mean_step_reduction_fraction'] >= .1 and matched['mean_time_reduction_fraction'] >= 0),
        'scope': 'Inference-driven controller engineering, not a neural-training benchmark. Primary reference P5; P6 reported as an additional control. Four fixed-layout simulation cases, no hardware validation.'}
    (SOURCE / 'assessment.json').write_text(json.dumps(result, indent=2) + '\n')
    (ROOT / 'evidence/inkling-v21/assessment.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
