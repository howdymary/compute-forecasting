"""Completion-only audit with paired costs and exact-state domain evidence."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from assess_terrain_training import paired_complete, evidence


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True)
    a = p.parse_args()
    source = Path(a.source)
    report = json.loads((source / 'report.json').read_text())
    assert report['status'] == 'completed' and report['held_out_opened']
    logs = report['training_log']
    assert len(logs) == report['optimizer_updates_completed']
    assert all(r['optimizer_completed'] and r['forward_backward_completed'] for r in logs)
    held = {label: json.loads((source / ('held-out-' + label + '.json')).read_text()) for label in report['held_out']}
    paired = paired_complete(held['parent'], held['selected'])
    components = defaultdict(list)
    for batch in report['component_results']:
        for row in batch['results']:
            components[row['domain'] + ':' + row['task']].append(row)
    for rows in components.values():
        reached = [r for r in rows if r.get('status') != 'reference_not_reached']
        if reached:
            assert {r['model'] for r in reached} == {'parent', 'selected'}
            assert len({r['initial_state_sha256'] for r in reached}) == 1
    audit = {'study': report['study'], 'run_id': report['run_id'],
        'scope': report['scope'], 'optimizer_updates_completed': len(logs),
        'completed_domain_backward_calls': sum(len(r['domain_loss_metrics']) for r in logs),
        'selected_checkpoint': report['selected_checkpoint'],
        'held_out': {label: {**report['held_out'][label], **evidence(rows)} for label, rows in held.items()},
        'paired_successful_completions': paired, 'exact_state_components': dict(components),
        'component_reference_seed': report['component_reference_seed'],
        'limits': ['Small simulated evaluation; no hardware reliability claim.',
                   'Native gait and physical controllers stayed fixed.',
                   'Changed weights or preferences alone do not establish better physical control.',
                   'No causal search or memory ablation.']}
    (source / 'assessment.json').write_text(json.dumps(audit, indent=2) + '\n')
    lines = ['# Fresh-state continuation results', '',
        f"Tinker completed {len(logs)} optimizer updates. Development selected update {report['selected_checkpoint']['update']}.", '',
        '| Policy | All four tasks | Within smoothness limits |', '|---|---:|---:|']
    for name, row in report['held_out'].items():
        lines.append(f"| {name} | {row['complete_successes']}/{row['n']} | {row['smooth_complete_successes']}/{row['n']} |")
    lines += ['', f'{len(paired)} final scenarios completed under both parent and selected weights.']
    if paired:
        lines.append(f"On those matched successes, completion time changed by {mean(r['time_change_s'] for r in paired):+.2f} s and recovery joint travel by {mean(r['recovery_joint_travel_change_rad'] for r in paired):+.3f} rad.")
    lines += ['', 'The static comparison uses station preferences chosen only from training labels. Component diagnostics use identical physical starting states; they are separate branches, not a stitched demonstration.', '', *audit['limits']]
    (source / 'assessment.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'updates': len(logs), 'selected_update': report['selected_checkpoint']['update'],
                      'paired_successes': len(paired), 'component_pairs': len(components)}))


if __name__ == '__main__':
    main()
