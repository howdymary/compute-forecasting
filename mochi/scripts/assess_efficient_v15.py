"""Audit completed V15 evidence and write a publication-sized assessment.

Reads existing results only. Never runs a rollout, trains, or edits raw evidence.
Run after build_efficient_v15_preview.py has downloaded the public recordings.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
TASKS = ('alarm', 'drawer', 'laptop', 'globe')
DOMAINS = {'walk', *TASKS, 'recovery'}


def read(path):
    return json.loads(path.read_text())


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10), (a, b)


def number(value, suffix=''):
    return 'Unavailable' if value is None else f'{value:.2f}{suffix}'


def check_completed_physics(episode):
    """Read physical endpoint and contact evidence, independently of a score."""
    assert not episode['fall'] and not episode['invalid_contact']
    assert episode['maximum_applied_base_force'] == 0
    assert set(episode['results']) == set(TASKS)
    for result in episode['results'].values():
        assert result['success'] and result['contacts'] > 0
        assert result['non_hand_contact_steps'] == 0 and result['max_force_n'] < .8
    values, speeds = episode['final_object_states'], episode['final_object_speeds']
    assert values['drawer'] < .002 and values['laptop'] < math.radians(5)
    assert abs(values['globe']) < math.radians(3)
    assert all(abs(speeds[task]) < limit for task, limit in [('drawer', .01), ('laptop', .15), ('globe', .07)])
    assert [r['task'] for r in episode['recoveries']] == list(TASKS)
    assert all(r['success'] for r in episode['recoveries'])
    task_events = [e for e in episode['events'] if e.get('task') in TASKS
        and e.get('phase') != 'recover' and isinstance(e.get('success'), bool)]
    assert [e['task'] for e in task_events] == list(TASKS)
    assert all(e['success'] for e in task_events)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--public', default=str(ROOT / 'web/desk/efficient-v15'))
    parser.add_argument('--out', default=str(ROOT / 'docs/efficient-v15-assessment.md'))
    args = parser.parse_args()
    source, public = Path(args.source), Path(args.public)
    report = read(source / 'report.json')
    cfg = report['protocol']
    assert report['study'] == 'mochi-efficient-v15'
    assert report['status'] == 'completed' and report['held_out_opened']
    assert report['source_sha'] == '87ba8d482efd13c789bb200ae9424924e0f77ad1'
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha
        for path, sha in cfg['frozen_sha256'].items()), 'Frozen experiment source changed'
    logs = report['training_log']
    assert report['optimizer_updates_completed'] == 16
    assert [r['update'] for r in logs] == list(range(1, 17))
    assert all(r['optimizer_completed'] and r['forward_backward_completed'] for r in logs)
    assert all(set(r['domain_loss_metrics']) == DOMAINS for r in logs)
    assert all(set(r['domain_counts']) == DOMAINS and min(r['domain_counts'].values()) > 0 for r in logs)
    assert all(v > 1e-7 for v in report['first_optimizer_behavioral_probe'].values())
    cps = {c['update']: c for c in report['checkpoints']}
    assert set(cps) == {0, 1, 4, 8, 16}
    assert len({c['checkpoint_id'] for c in cps.values()}) == len(cps)
    for c in cps.values():
        assert len(c['checkpoint_id']) == 64 and int(c['checkpoint_id'], 16) >= 0
        assert c['cumulative_updates'] == cfg['parent_optimizer_updates'] + c['update']
    selected = report['selected_checkpoint']['update']
    selection = read(source / 'selection-freeze.json')
    assert not selection['held_out_opened'] and selection['selected_checkpoint']['update'] == selected
    assert not selection.get('held_out'), 'Selection must precede final test results'
    assert selection['selected_checkpoint']['checkpoint_id'] == cps[selected]['checkpoint_id']
    partitions = [set(cfg[k]) for k in ('training_seeds', 'development_seeds', 'held_out_seeds')]
    assert not any(a & b for i, a in enumerate(partitions) for b in partitions[i + 1:])

    held = {label: read(source / f'held-out-{label}.json') for label in ('parent', 'selected', 'fixed', 'static')}
    pairs = []
    evidence = {}
    for label, rows in held.items():
        assert {r['seed'] for r in rows} == partitions[2] and len(rows) == len(partitions[2])
        valid = [r for r in rows if r['qualified_complete']]
        stats = report['held_out'][label]
        assert stats['n'] == len(rows) and stats['qualified_complete_successes'] == len(valid)
        assert stats['complete_successes'] == sum(r['complete_sequence_success'] for r in rows)
        for row in rows:
            if row['complete_sequence_success']:
                check_completed_physics(row['episode'])
        if valid:
            close(stats['successful_mean_steps'], mean(r['episode']['steps']['attempts'] for r in valid))
            close(stats['successful_mean_seconds'], mean(r['episode']['duration'] for r in valid))
        evidence[label] = {'statistics': stats, 'failures': dict(Counter(r['failure'] for r in rows if r['failure'])),
            'actions': dict(Counter(f"{d['observation']['domain']}:{d['action']}" for r in rows for d in r['model_decisions']))}
    before = {r['seed']: r for r in held['parent']}
    for b in held['selected']:
        a = before[b['seed']]
        assert a['episode']['scenario'] == b['episode']['scenario'] and a['episode']['scene'] == b['episode']['scene']
        if a['qualified_complete'] and b['qualified_complete']:
            pairs.append({'seed': b['seed'], 'parent_steps': a['episode']['steps']['attempts'],
                'selected_steps': b['episode']['steps']['attempts'],
                'step_reduction_fraction': 1 - b['episode']['steps']['attempts'] / a['episode']['steps']['attempts'],
                'time_reduction_fraction': 1 - b['episode']['duration'] / a['episode']['duration']})
    paired = report['paired_held_out']
    assert paired['n'] == len(pairs)
    if pairs:
        close(paired['mean_step_reduction_fraction'], mean(r['step_reduction_fraction'] for r in pairs))
        close(paired['mean_time_reduction_fraction'], mean(r['time_reduction_fraction'] for r in pairs))
    met = bool(len([r for r in held['selected'] if r['qualified_complete']]) == len(partitions[2])
        and len(pairs) >= 2 and paired['mean_step_reduction_fraction'] >= .2
        and paired['mean_time_reduction_fraction'] >= 0
        and report['held_out']['selected']['falls'] <= report['held_out']['parent']['falls']
        and report['held_out']['selected']['invalid_contacts'] <= report['held_out']['parent']['invalid_contacts'])
    assert report['improvement_goal_met'] == met

    components = defaultdict(list)
    for batch in report['component_results']:
        for row in batch['results']:
            components[row['domain'] + ':' + row['task']].append(row)
    assert len(components) == 12
    for rows in components.values():
        reached = [r for r in rows if r.get('status') != 'reference_not_reached']
        if reached:
            assert {r['model'] for r in reached} == {'parent', 'selected'} and len(reached) == 2
            assert len({r['initial_state_sha256'] for r in reached}) == 1

    manifest = read(public / 'manifest.json')
    assert manifest['source_sha'] == report['source_sha'] and manifest['selected_update'] == selected
    assert manifest['optimizer_updates_completed'] == 16 and manifest['test_pairs_available'] == len(partitions[2])
    first_frames = {}
    for filename, meta in manifest['recordings'].items():
        payload = (public / filename).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == meta['sha256']
        raw = gzip.decompress(payload)
        assert hashlib.sha256(raw).hexdigest() == meta['uncompressed_sha256']
        clip = json.loads(raw)
        assert clip['scenario']['seed'] == meta['seed'] and clip['maximum_applied_base_force'] == 0
        assert clip['steps']['attempts'] == len(clip['step_events']) == meta['steps']['attempts']
        frames = clip['trajectory']['frames']
        assert frames and frames[0]['t'] == 0
        assert all(0 < b['t'] - a['t'] <= .05 for a, b in zip(frames, frames[1:])), 'Missing or reversed trajectory samples'
        assert 0 <= clip['duration'] - frames[-1]['t'] <= .05
        assert set(clip['results']) <= set(TASKS)
        first_frames[filename] = clip['trajectory']['frames'][0]
    for scenario in manifest['scenarios']:
        for version in scenario['versions']:
            assert first_frames[scenario['parent_file']] == first_frames[version['file']]

    usage = report['budget_usage_or_reserved']
    for kind, limit in cfg['bounds'].items():
        if kind != 'modal_concurrency':
            assert 0 <= usage[kind] <= limit, (kind, usage[kind], limit)
    assert usage['optimizer_updates'] == 16 and cfg['bounds']['modal_concurrency'] == 4
    receipts = report['physics_receipts']
    assert sum(r['receipt']['physical_rollouts'] for r in receipts) == report['campaign_modal_rollouts_completed'] == usage['modal_rollouts']
    close(sum(r['receipt']['duration_seconds'] * r['receipt']['cpu'] / 3600 for r in receipts), usage['modal_cpu_hours'])
    eligibility = report['services']['eligibility']
    assert eligibility['writers'] > 1 and eligibility['readers'] > 1 and eligibility['cross_agent_reads'] > 0
    assert eligibility['isolation_passed'] and not report['services'].get('pending_ingestions')
    assert report['cross_run_memory']['reads'][-1]['source_id_verified']
    assert report['services']['sources'] and all(s['request_id'] and s['sources'] for s in report['services']['sources'])
    for kind in ('ingest', 'recall'):
        assert any(c['provider'] == 'past.dev' and c['kind'] == kind and c['method'] == 'POST'
            and 200 <= c['status'] < 300 for c in report['services']['calls'])
    audit = {'study': report['study'], 'source_sha': report['source_sha'], 'run_id': report['run_id'],
        'optimizer_updates': len(logs), 'domain_backward_calls': sum(len(r['domain_loss_metrics']) for r in logs),
        'selected_update': selected, 'selected_checkpoint_id': cps[selected]['checkpoint_id'],
        'development': {str(k): c['development'] for k, c in cps.items()}, 'held_out': evidence,
        'paired_qualified_completions': pairs, 'paired_summary': paired, 'improvement_goal_met': met,
        'component_results': dict(components), 'usage': usage, 'service_eligibility': eligibility,
        'public_recordings_verified': len(first_frames), 'selection_preceded_held_out': True,
        'limits': ['Small fixed-layout simulation cohort; no hardware or broad reliability claim.',
            'Native gait weights and the physical controller library stayed fixed.',
            'Matched success costs exclude pairs where either policy fails; all failures remain in completion denominators.',
            'Exact-state component branches are diagnostic evidence, not the continuous demo.',
            'Shared-memory and search usage are verified separately from causal benefit; no memory/search ablation.']}
    lines = ['# V15 walking and task-control results', '',
        f"Tinker completed {len(logs)} optimizer updates and {audit['domain_backward_calls']} domain gradient calls. Development selected update {selected}.", '',
        '| Checkpoint | Qualified complete | Steps on qualified completions | Physical seconds |', '|---|---:|---:|---:|']
    for update, cp in sorted(cps.items()):
        s = cp['development']
        lines.append(f"| {update} | {s['qualified_complete_successes']}/{s['n']} | {number(s['successful_mean_steps'])} | {number(s['successful_mean_seconds'])} |")
    lines += ['', '| Final-test policy | All four tasks | Qualified complete | Steps on qualified completions | Physical seconds |', '|---|---:|---:|---:|---:|']
    for label, item in evidence.items():
        s = item['statistics']
        lines.append(f"| {label} | {s['complete_successes']}/{s['n']} | {s['qualified_complete_successes']}/{s['n']} | {number(s['successful_mean_steps'])} | {number(s['successful_mean_seconds'])} |")
    lines += ['', f"The 20% step-reduction goal was {'met' if met else 'not met'} on this cohort.",
        f"Paired efficiency uses {len(pairs)} scenarios where both policies completed within all declared quality limits."]
    if pairs:
        lines += [f"Mean step reduction: {paired['mean_step_reduction_fraction']:.1%}; mean completion-time reduction: {paired['mean_time_reduction_fraction']:.1%}."]
        for field, title in [('mean_step_reduction_bootstrap_95', 'Step reduction'), ('mean_time_reduction_bootstrap_95', 'Time reduction')]:
            interval = paired[field]
            if interval:
                lines.append(f"{title} paired bootstrap interval: {interval[0]:.1%} to {interval[1]:.1%}. This describes the small observed cohort.")
    lines += ['', '| Exact-state test | Parent action / success | Selected action / success |', '|---|---|---|']
    for key, rows in sorted(components.items()):
        by_model = {r['model']: r for r in rows if r.get('status') != 'reference_not_reached'}
        if by_model:
            a, b = by_model['parent'], by_model['selected']
            lines.append(f"| {key} | {a['action']} / {a['success']} | {b['action']} / {b['success']} |")
        else:
            lines.append(f'| {key} | Reference state not reached | Reference state not reached |')
    lines += ['', 'Component success is the recorded branch outcome. Contact, balance and smoothness measurements remain in the numerical assessment; these branches are separate from the full continuous sequences.', '', 'Observed final-test failures:']
    for label, item in evidence.items():
        failures = ', '.join(f'{k} × {n}' for k, n in item['failures'].items()) or 'none in this cohort'
        lines.append(f'- {label}: {failures}.')
    lines += ['', f"Physical rollouts: {usage['modal_rollouts']}/224. Function CPU-hours: {usage['modal_cpu_hours']:.3f}/18. This is measured function execution, not an invoice.", '', *audit['limits'], '',
        f"[Run evidence](https://github.com/howdymary/mochi-demo/actions/runs/{report['run_id'].split('-')[-1]}) · [Checkpoint demo](https://howdymary--mochi-efficient-v15-demo-web.us-east.modal.run/)"]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines) + '\n')
    out.with_suffix('.json').write_text(json.dumps(audit, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'assessment': str(out), 'goal_met': met, 'updates': len(logs), 'paired_n': len(pairs), 'recordings': len(first_frames)}))


if __name__ == '__main__':
    main()
