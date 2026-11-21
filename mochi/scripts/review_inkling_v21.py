"""Ask the deployed model to review a completed, independently measured study."""
import hashlib
import json
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'artifacts/inkling-v21'
REQUEST = 'compact-final-review-r6'


def main():
    destination = SOURCE / (REQUEST + '.json')
    if destination.exists():
        print(json.dumps({'retained_receipt': str(destination)}))
        return
    assessment = json.loads((SOURCE / 'assessment.json').read_text())
    ledger = json.loads((SOURCE / 'physics/ledger.json').read_text())
    assert all(row['status'] == 'completed' for row in ledger['attempts'].values())
    packet = {
        'summary': 'Final review of the closed Inkling controller-engineering pilot. '
            'The selected change is only globe_clearance_y_m = 0.055. '
            'This study performed zero optimizer updates. Interpret paired complete, '
            'qualified attempts separately from partial failed trajectories. '
            'Do not propose or execute additional changes after the held-out results.',
        'recall_record_ids': ['mochi-ink21-20261120-r6', 'mochi-ink21-20261120-r8'],
        'assessment_sha256': hashlib.sha256((SOURCE / 'assessment.json').read_bytes()).hexdigest(),
        'assessment': {
            'frozen_files_verified': assessment['frozen_files_verified'],
            'physical_attempts_accounted': assessment['physical_attempts_accounted'],
            'simulation_seconds_accounted': assessment['simulation_seconds_accounted'],
            'step_goal_met': assessment['step_goal_met'],
            'paired_held_out': assessment['paired_held_out'],
            **{partition: {label: {key: values[key] for key in [
                'n', 'complete_successes', 'qualified_complete_successes',
                'successful_mean_steps', 'successful_mean_seconds', 'wilson_95_qualified_rate']}
                for label, values in assessment[partition].items()}
                for partition in ['development', 'held_out']},
        },
        'service_caveats': [
            'Two Exa searches and verified past.dev handoffs are real activity, not evidence of a measured ablation benefit.',
            'No new critic-private canary test was run in this pilot.',
            'Physics in this pilot ran locally; Modal hosted the authenticated research backend.',
            'A failed initial structured-output call retains a conservative token reservation, not an invented exact output count.',
            'All four tasks must qualify before step or arm-travel savings can be compared.',
        ],
        'physical_attempts': [
            {k: row.get(k) for k in ['id', 'complete', 'qualified', 'branch_success',
                'branch_valid', 'failure', 'steps', 'branch_steps', 'seconds', 'branch_seconds']}
            for row in ledger['attempts'].values()
        ],
        'output_contract': {
            'analysis': 'A short list of measured findings, with sample counts.',
            'candidates': [],
            'limitations': 'A short list of unestablished claims and next research questions. '
                'No new proposal may be accepted in this frozen study.',
        },
    }
    assert len(json.dumps(packet)) <= 16000, 'Keep final evidence compact before rendering'
    (SOURCE / (REQUEST + '-packet.json')).write_text(json.dumps(packet, indent=2) + '\n')
    volume = modal.Volume.from_name('mochi-inkling-v21-research')
    try:
        result = modal.Function.from_name('mochi-inkling-v21-research', 'research').remote(
            REQUEST, packet, [], 'review')
        destination.write_text(json.dumps(result, indent=2) + '\n')
    finally:
        for name in [REQUEST + '.json', 'budget.json']:
            try:
                data = b''.join(volume.read_file('mochi-ink21-20261120/' + name))
                (SOURCE / name).write_bytes(data)
            except Exception as error:
                print(json.dumps({'unavailable_remote_artifact': name, 'error_type': type(error).__name__}))
    print(json.dumps({k: result[k] for k in ['request_id', 'status', 'input_tokens', 'output_tokens', 'budget']}))


if __name__ == '__main__':
    main()
