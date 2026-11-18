"""Join final service receipts without changing archived performance records."""
import hashlib
import json
from pathlib import Path


def completed_report(source):
    source = Path(source)
    raw = (source / 'report.json').read_bytes()
    report = json.loads(raw)
    progress = source / 'progress.json'
    if progress.exists():
        final_raw = progress.read_bytes()
        final = json.loads(final_raw)
        if final.get('status') == 'completed':
            for key in ['study', 'workflow_run', 'source_sha', 'held_out',
                        'selected_checkpoint', 'optimizer_updates_completed']:
                assert final[key] == report[key], key
            original = {x['id'] for x in report['services']['records']}
            finalized = {x['id'] for x in final['services']['records']}
            assert original <= finalized
            assert len(final['services']['calls']) >= len(report['services']['calls'])
            report['services'] = final['services']
            report['receipt_provenance'] = {
                'performance': 'Unmodified completed report.json measurements',
                'services': 'Completed progress.json, published after the final memory handoffs',
                'report_sha256': hashlib.sha256(raw).hexdigest(),
                'progress_sha256': hashlib.sha256(final_raw).hexdigest(),
                'archive_mutated': False,
            }
    return report
