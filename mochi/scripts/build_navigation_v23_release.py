"""Audit all paired results and package measured replays without private paths."""
import argparse
from collections import Counter, defaultdict
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import gzip

import numpy as np
from mochi.navigation_v23.layouts import fingerprint
from mochi.smooth_v16.public import rounded

ROOT = Path(__file__).resolve().parents[1]
(ROOT / '.cache/navigation-v23').mkdir(parents=True, exist_ok=True)
release_lock = (ROOT / '.cache/navigation-v23/release.lock').open('a')
fcntl.flock(release_lock, fcntl.LOCK_EX)
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
args = parser.parse_args()
source = args.source
report = json.loads((source / 'progress.json').read_text())
assert report['status'] == 'completed' and report['held_out_opened']
assert report['optimizer_updates_completed'] > 0
assert all(r['forward_backward_completed'] and r['optimizer_completed'] for r in report['training_log'])
assert report['maximum_probe_probability_change'] > 1e-7
assert len(report['training_log']) == report['optimizer_updates_completed']
assert report['native_gait_weights_trained'] is False
selection = json.loads((source / 'selection-freeze.json').read_text())
assert selection['selected_checkpoint'] == report['selected_checkpoint']
splits = selection['split_manifest']
for partition, rows in [('development', report['development']['0']['rows']), ('final_navigation', report['final']['parent'])]:
    layouts = list({r['layout_sha256']: r['layout'] for r in rows}.values())
    assert len(layouts) == splits[partition]['count']
    assert fingerprint(layouts) == splits[partition]['sha256']
report['selection_freeze'] = selection
report['split_manifest'] = splits
for key, filename in [('weight_tensor_audit', 'weight-tensor-audit.json'),
    ('trajectory_equivalence_audit', 'trajectory-equivalence-audit.json')]:
    path = ROOT / 'evidence/navigation-v23' / filename
    if path.exists():
        report[key] = json.loads(path.read_text())
OUT = ROOT / 'web/desk/navigation-v23'
EVIDENCE = ROOT / 'evidence/navigation-v23'
OUT.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def paired(left, right):
    a = {(r['layout_sha256'], r['seed']): r for r in left}
    b = {(r['layout_sha256'], r['seed']): r for r in right}
    assert a.keys() == b.keys()
    groups = defaultdict(list)
    for k in sorted(a):
        x, y = a[k], b[k]
        assert x['mechanics_sha256'] == y['mechanics_sha256']
        assert x['initial_physical_state_sha256'] == y['initial_physical_state_sha256']
        assert x['layout'] == y['layout']
        groups[k[0]].append((x, y))
    success_delta = [np.mean([float(y['qualified']) - float(x['qualified']) for x, y in pairs]) for pairs in groups.values()]
    both = [(x, y) for pairs in groups.values() for x, y in pairs if x['qualified'] and y['qualified']]
    per_layout_steps = [np.mean([y['steps']['attempts'] - x['steps']['attempts'] for x, y in pairs if x['qualified'] and y['qualified']]) for pairs in groups.values() if any(x['qualified'] and y['qualified'] for x, y in pairs)]
    rng = np.random.default_rng(235501)
    def interval(values):
        if not values:
            return None
        samples = rng.choice(values, (20000, len(values)), replace=True).mean(axis=1)
        return np.quantile(samples, [.025, .975]).tolist()
    return {'layouts': len(groups), 'paired_attempts': len(a), 'success_fraction_delta': float(np.mean(success_delta)),
        'success_delta_layout_bootstrap_95_interval': interval(success_delta),
        'jointly_qualified_attempts': len(both), 'jointly_qualified_layouts': len(per_layout_steps),
        'mean_layout_step_delta_on_jointly_qualified_pairs': float(np.mean(per_layout_steps)) if per_layout_steps else None,
        'step_delta_layout_bootstrap_95_interval': interval(per_layout_steps),
        'mean_physical_seconds_delta_on_jointly_qualified_pairs': float(np.mean([y['physical_seconds'] - x['physical_seconds'] for x, y in both])) if both else None,
        'scope': 'Candidate minus reference. Layouts are the bootstrap unit. Eight layouts provide limited uncertainty resolution; a degenerate zero bootstrap interval does not establish population equivalence. Efficiency is conditional on paired qualified completion.'}


comparisons = {key: paired(report['final']['parent'], values) for key, values in report['final'].items() if key != 'parent'}
memory_pair = paired(report['final']['selected'], report['final']['selected_memory_enabled'])
report['paired_final_comparisons'] = comparisons
report['paired_memory_comparison'] = memory_pair
report['actual_physical_attempts'] = len(report['physics_receipts']) + report['protocol'].get('carried_actual_physical_rollouts', 5)
report['layout_counts'] = {k: v['count'] for k, v in json.loads((ROOT / 'configs/navigation-v23/split-manifest.json').read_text()).items()}
def layout_reliability(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['layout_sha256']].append(row['qualified'])
    n, k = len(groups), sum(all(values) for values in groups.values())
    z, p = 1.95996398454, k / n
    denominator = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denominator
    half = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    return {'layouts_passing_all_seeds': k, 'layouts': n,
        'descriptive_wilson_95_interval': [max(0., centre-half), min(1., centre+half)],
        'scope': 'Layouts, not repeated physics seeds, are the units. Descriptive binomial approximation for this small, generated cohort; not a guarantee for arbitrary desks.'}
report['layout_reliability'] = {name: layout_reliability(rows) for name, rows in report['final'].items()}
report['action_audit'] = {name: dict(Counter(r['action'] for r in values)) for name, values in report['final'].items()}
fixed_by_case = {(r['layout_sha256'], r['seed']): r for r in report['final']['fixed']}
same_choice, same_outcome = 0, 0
for row in report['final']['selected']:
    fixed = fixed_by_case[(row['layout_sha256'], row['seed'])]
    same_choice += row['action'] == fixed['action']
    same_outcome += (row['qualified'] == fixed['qualified'] and row['steps']['attempts'] == fixed['steps']['attempts'])
report['mechanism_audit'] = {'selected_distinct_actions': len(report['action_audit']['selected']),
    'matched_fixed_strategy_choices': same_choice, 'matched_fixed_qualification_and_steps': same_outcome,
    'attempts': len(report['final']['selected']),
    'qualification': 'A fixed profile can still produce layout-dependent A* routes. Matching choices or outcome summaries does not prove identical unrounded trajectories or a learned clearance rule.'}
report['mechanism_audit']['changed_parent_choices'] = sum(a['action'] != b['action']
    for a, b in zip(report['final']['parent'], report['final']['selected']))
report['training_targets'] = dict(Counter(t['target'] for t in report['training_trials']))
report['adaptation_summary'] = {}
for name in ['parent', 'selected']:
    for enabled in [False, True]:
        rows = [r for r in report['adaptation'] if r['model'] == name and r['memory_enabled'] == enabled]
        report['adaptation_summary'][name + ('_memory' if enabled else '_no_memory')] = {
            'layouts': len(rows), 'first_attempt_successes': sum(r['attempts'][0]['qualified'] for r in rows),
            'success_within_three': sum(r['success_within_budget'] for r in rows),
            'attempts': sum(len(r['attempts']) for r in rows),
            'total_physical_seconds': sum(a['physical_seconds'] for r in rows for a in r['attempts']),
            'total_function_wall_seconds': sum(a['receipt']['duration_seconds'] for r in rows for a in r['attempts']),
            'total_inference_seconds': sum(a['selection'].get('inference_seconds', 0.) for r in rows for a in r['attempts']),
            'resets_after_failed_attempts': sum(len(r['attempts']) - 1 for r in rows),
            'total_steps': sum(a['steps']['attempts'] for r in rows for a in r['attempts'])}
def adaptation_pair(reference_model, reference_memory, candidate_model, candidate_memory):
    a = {r['layout_sha256']: r for r in report['adaptation'] if r['model'] == reference_model and r['memory_enabled'] == reference_memory}
    b = {r['layout_sha256']: r for r in report['adaptation'] if r['model'] == candidate_model and r['memory_enabled'] == candidate_memory}
    assert a.keys() == b.keys() and len(a) == 8
    values = defaultdict(list)
    for key in sorted(a):
        x, y = a[key], b[key]
        assert x['attempts'][0]['initial_physical_state_sha256'] == y['attempts'][0]['initial_physical_state_sha256']
        values['first_attempt_success_delta'].append(float(y['attempts'][0]['qualified']) - float(x['attempts'][0]['qualified']))
        values['success_within_three_delta'].append(float(y['success_within_budget']) - float(x['success_within_budget']))
        values['attempt_count_delta'].append(len(y['attempts']) - len(x['attempts']))
        values['all_attempt_physical_seconds_delta'].append(sum(r['physical_seconds'] for r in y['attempts']) - sum(r['physical_seconds'] for r in x['attempts']))
        values['all_attempt_steps_delta'].append(sum(r['steps']['attempts'] for r in y['attempts']) - sum(r['steps']['attempts'] for r in x['attempts']))
    rng = np.random.default_rng(235503)
    indices = rng.integers(8, size=(20000, 8))
    return {'layouts': 8, 'maximum_attempts_per_layout': 3, 'candidate_minus_reference': {
        name: {'mean': float(np.mean(v)), 'layout_bootstrap_95_interval': np.quantile(np.asarray(v)[indices].mean(axis=1), [.025, .975]).tolist()}
        for name, v in values.items()},
        'scope': 'Paired layouts with one physics seed each. Every failure and reset is included in costs. First trajectories reused from the corresponding frozen first-attempt cohort are not billed twice. A degenerate interval is not population equivalence.'}
report['paired_adaptation'] = {
    'parent_memory_effect': adaptation_pair('parent', False, 'parent', True),
    'selected_memory_effect': adaptation_pair('selected', False, 'selected', True),
    'training_effect_without_memory': adaptation_pair('parent', False, 'selected', False),
    'training_effect_with_memory': adaptation_pair('parent', True, 'selected', True)}
parent, selected = report['final_summaries']['parent'], report['final_summaries']['selected']
fixed_count = report['final_summaries']['fixed']['qualified']
report['public_summary'] = f"{report['optimizer_updates_completed']} real Tinker optimizer updates. On eight unseen layouts with two physics seeds each, parent and selected qualification were {parent['qualified']}/16 and {selected['qualified']}/16; the strongest fixed strategy qualified {fixed_count}/16. Training changed {report['mechanism_audit']['changed_parent_choices']} final route choice. Geometry is privileged and the native gait is fixed."
mem = report['final_summaries']['selected_memory_enabled']
report['memory_summary'] = f"The selected weights qualified {selected['qualified']}/16 without retrieval and {mem['qualified']}/16 with frozen training-memory retrieval. Three-attempt adaptation is reported separately in the full evidence. This does not by itself establish a memory benefit."
off, on = report['adaptation_summary']['selected_no_memory'], report['adaptation_summary']['selected_memory']
report['memory_summary'] += f" In the separate eight-layout, one-seed adaptation comparison, success within three attempts was {off['success_within_three']}/8 without retrieval and {on['success_within_three']}/8 with retrieval, using {off['attempts']} and {on['attempts']} total attempts. Both conditions retained their local failure history."
extension = ROOT / 'evidence/navigation-tasks-v24/preflight.json'
if extension.exists():
    report['task_extension_preflight'] = json.loads(extension.read_text())
    report['phase_b_status'] = 'The separate task preflight completed clock, drawer and laptop, but did not validate the globe transition. Additional departure probes remained unsuccessful. No task-training update or four-task generalization gain is claimed. Sequence final layouts remain unopened.'
departure = ROOT / 'evidence/navigation-tasks-v24/departure-r2.json'
if departure.exists():
    report['task_departure_probe'] = json.loads(departure.read_text())

trained_updates = [cp['update'] for cp in report['checkpoints'] if cp['update'] > 0]
cases, comparison_options = [], [
    {'id': 'selected', 'label': 'Selected checkpoint'},
    *[{'id': 'u' + str(u), 'label': 'Checkpoint · ' + str(u) + ' updates'} for u in trained_updates],
    {'id': 'planner', 'label': 'Collision-aware planner'},
    {'id': 'conventional', 'label': 'Conventional tuning'},
    {'id': 'fixed', 'label': 'Strongest fixed strategy'},
    {'id': 'selected_memory_enabled', 'label': 'Selected + training memory'},
]
used = {}
def recording(row):
    public = row['public_recording']
    name = Path(public['path']).name
    p = source / 'public' / name
    assert hashlib.sha256(p.read_bytes()).hexdigest() == public['sha256'], name
    if name not in used:
        clip = json.loads(gzip.decompress(p.read_bytes()))
        assert clip['maximum_applied_base_force'] == 0
        for key in ['props', 'station_offsets', 'clock_offset', 'globe_offset']:
            assert clip['scene'].get(key) == rounded(row['layout']['scene'].get(key)), (name, key)
        shutil.copyfile(p, OUT / name)
        used[name] = {'sha256': public['sha256'], 'bytes': p.stat().st_size,
            'source_trajectory': row['artifact'], 'scope': row['scope']}
    return {'file': name, 'row': row}

for partition, values in [('final', report['final']['parent']), ('development', report['development']['0']['rows'])]:
    for i, parent in enumerate(values):
        key = (parent['layout_sha256'], parent['seed'])
        runs = {'parent': recording(parent)}
        pools = (report['final'] if partition == 'final' else {
            'selected': report['development'][str(report['selected_checkpoint']['update'])]['rows'],
            **{'u' + str(u): report['development'][str(u)]['rows'] for u in trained_updates}})
        for name, cohort in pools.items():
            if name == 'parent':
                continue
            row = next(r for r in cohort if (r['layout_sha256'], r['seed']) == key)
            assert row['initial_physical_state_sha256'] == parent['initial_physical_state_sha256']
            runs[name] = recording(row)
        cases.append({'id': partition + '-' + str(i), 'label': f"{'Unseen final' if partition == 'final' else 'Development'} layout {i // 2 + 1} · seed {parent['seed']}", 'partition': partition, 'runs': runs})
# Preserve complete failed/retried and training recordings alongside the main
# paired viewer, without treating them as additional independent test layouts.
extras = [r for entry in report['adaptation'] for r in entry['attempts']]
extras.extend(r for entry in report['training_trials'] for r in entry['outcomes'].values())
diagnostic_path = EVIDENCE / 'counterfactual-results.json'
if diagnostic_path.exists():
    diagnostic = json.loads(diagnostic_path.read_text())
    assert diagnostic['status'] == 'completed'
    report['counterfactual_diagnostic'] = diagnostic
    report['primary_actual_physical_attempts'] = report['actual_physical_attempts']
    report['actual_physical_attempts'] += len(diagnostic['receipts'])
    report['usage_actual_or_reserved'] = copy.deepcopy(diagnostic['cumulative_usage_actual_or_reserved'])
    extras.extend(r for entry in diagnostic['cases'] for r in entry['runs'].values())
for row in extras:
    recording(row)
report['navigation_actual_physical_attempts'] = report['actual_physical_attempts']
task_recordings = ROOT / 'evidence/navigation-tasks-v24/recordings.json'
if task_recordings.exists():
    used.update(json.loads(task_recordings.read_text())['recordings'])
if report.get('task_extension_preflight'):
    extension = report['task_extension_preflight']
    report['actual_physical_attempts'] += extension['counted_physical_attempts']
    report['usage_actual_or_reserved']['physical_rollouts'] += extension['counted_physical_attempts']
    report['usage_actual_or_reserved']['simulation_cpu_hours'] += extension['conservative_wall_hours']
if report.get('task_departure_probe'):
    extension = report['task_departure_probe']
    report['actual_physical_attempts'] += extension['counted_physical_attempts']
    report['usage_actual_or_reserved']['physical_rollouts'] += extension['counted_physical_attempts']
    report['usage_actual_or_reserved']['simulation_cpu_hours'] += extension['conservative_wall_hours']
report['retained_undispatched_rollout_reservations'] = 9
report['physical_count_scope'] = 'Actual attempts include interrupted engineering, the primary study, post-selection counterfactuals and the separately bounded task preflight. Nine never-dispatched reservations remain charged only in the conservative budget ledger.'
assert report['usage_actual_or_reserved']['physical_rollouts'] <= report['protocol']['bounds']['physical_rollouts']
assert report['usage_actual_or_reserved']['simulation_cpu_hours'] <= report['protocol']['bounds']['simulation_cpu_hours']
report['recording_manifest'] = used
# Preserve complete owner-side receipts, but do not publish identifiers from
# unrelated, publicly retrievable memories in this shared provider project.
for read in report['services']['reads']:
    for attempt in read.get('attempts', []):
        ids = attempt.get('returned_source_ids', [])
        unrelated = [value for value in ids if not value.startswith(report['run_id'])]
        if unrelated:
            attempt['unrelated_source_count'] = len(unrelated)
            attempt['unrelated_source_ids_sha256'] = hashlib.sha256(json.dumps(unrelated, sort_keys=True).encode()).hexdigest()
            attempt['returned_source_ids'] = [value for value in ids if value.startswith(report['run_id'])]
report['public_memory_receipt_scope'] = 'Unrelated public source identifiers are withheld and hash-linked. Exact requested-source verification and private-audience checks are preserved. Unrelated returned text never enters model context.'
changed_cases = [c for c in cases if c['partition'] == 'final'
    and c['runs']['parent']['row']['action'] != c['runs']['selected']['row']['action']]
default_case = changed_cases[0]['id'] if changed_cases else 'final-0'
highlight = f"Illustrative case selected after evaluation because the model changed its choice. Only {len(changed_cases)} of 16 final choices changed; all final attempts and stronger baselines are retained below." if changed_cases else None
save(OUT / 'manifest.json', {'study': report['study'], 'default_case': default_case,
    'highlight_reason': highlight, 'default_comparison': 'selected', 'cases': cases, 'comparisons': comparison_options})
save(OUT / 'report.json', report)
save(EVIDENCE / 'results.json', report)
save(EVIDENCE / 'recording-manifest.json', used)
save(EVIDENCE / 'paired-audit.json', {'comparisons': comparisons, 'memory': memory_pair,
    'adaptation': report['adaptation_summary'], 'paired_adaptation': report['paired_adaptation'],
    'all_layout_and_initial_state_matches': True})
save(EVIDENCE / 'checkpoint-receipts.json', {'checkpoints': report['checkpoints'],
    'training_log': report['training_log'], 'probe_change': report['maximum_probe_probability_change'],
    'native_gait_trained': False})
save(OUT / 'selection-freeze.json', selection)
save(OUT / 'split-manifest.json', splits)
save(OUT / 'recording-manifest.json', used)
print(json.dumps({'cases': len(cases), 'replays': len(used), 'public_bytes': sum(v['bytes'] for v in used.values()),
    'summaries': report['final_summaries'], 'action_audit': report['action_audit'],
    'phase_b_gate_met': report['phase_b_gate_met']}, indent=2))
