"""Publish only completed development comparisons while final layouts stay sealed."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'artifacts/navigation-v23/development-preview'
report = json.loads((source / 'progress.json').read_text())
assert report['status'] == 'running' and not report['held_out_opened']
updates = sorted(int(u) for u in report['development'] if int(u) > 0)
assert updates
latest = updates[-1]
OUT = ROOT / 'web/desk/navigation-v23'
OUT.mkdir(parents=True, exist_ok=True)
report.update(preview=True, preview_checkpoint=latest,
    actual_physical_attempts=len(report['physics_receipts']) + report['protocol']['carried_actual_physical_rollouts'],
    layout_counts={'development': 8, 'final_navigation': 8},
    public_summary=f"Development preview: checkpoint {latest} and the parent on the same eight layouts and two physics seeds. Training is still running. Final layouts remain unopened.",
    memory_summary='The separate memory performance comparison has not run yet.',
    phase_b_status='Object-relative task primitives are under separate validation. No four-task training gain is claimed.')
options = [{'id': 'u' + str(u), 'label': 'Checkpoint · ' + str(u) + ' updates'} for u in updates]
cases = []
for i, parent in enumerate(report['development']['0']['rows']):
    runs = {}
    for name, cohort in [('parent', report['development']['0']['rows']), *[('u' + str(u), report['development'][str(u)]['rows']) for u in updates]]:
        row = cohort[i]
        assert row['initial_physical_state_sha256'] == parent['initial_physical_state_sha256']
        assert row['layout'] == parent['layout']
        name_on_disk = Path(row['public_recording']['path']).name
        p = source / 'public' / name_on_disk
        assert hashlib.sha256(p.read_bytes()).hexdigest() == row['public_recording']['sha256']
        shutil.copyfile(p, OUT / name_on_disk)
        runs[name] = {'file': name_on_disk, 'row': row}
    cases.append({'id': 'development-' + str(i), 'partition': 'development',
        'label': f'Development layout {i // 2 + 1} · seed {parent["seed"]}', 'runs': runs})
for name, value in [('manifest', {'study': report['study'], 'default_case': 'development-0',
    'default_comparison': 'u' + str(latest), 'comparisons': options, 'cases': cases}), ('report', report)]:
    (OUT / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')
print(json.dumps({'preview': True, 'evaluated_checkpoint': latest, 'cases': len(cases), 'final_layouts_opened': False}))
