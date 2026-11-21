"""Automatic static feasibility only. Final coordinates are never printed."""
import json
from pathlib import Path

from mochi.navigation_v23.engine import inspect
from mochi.navigation_v23.layouts import generate, fingerprint

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'configs/navigation-v23'
PRIVATE = ROOT / 'artifacts/navigation-v23/sealed'
PRIVATE.mkdir(parents=True, exist_ok=True)
existing_manifest = json.loads((PUBLIC / 'split-manifest.json').read_text()) if (PUBLIC / 'split-manifest.json').exists() else None
manifest = {}
for partition, amount, base in [('training', 16, 231000), ('development', 8, 232000),
    ('final_navigation', 8, 233000), ('final_sequence', 8, 234000)]:
    accepted, rejected, counts = [], [], [0] * 4
    target = PRIVATE / (partition + '.json') if partition.startswith('final') else PUBLIC / (partition + '.json')
    if target.exists():
        values = json.loads(target.read_text())
        manifest[partition] = {'count': len(values), 'sha256': fingerprint(values), 'path': str(target.relative_to(ROOT))}
        continue
    for index in range(200):
        family = index % 4
        if counts[family] >= amount // 4:
            continue
        layout = generate(base + index * 101, partition, index)
        _, envelope, obstacles, plans = inspect(layout, 231000)
        valid = all(plans[p]['feasible'] for p in ['direct', 'buffered', 'planner'])
        if not valid:
            rejected.append({'generation_seed': layout['generation_seed'], 'layout_sha256': layout['layout_sha256'],
                'reasons': {p: v.get('reason') for p, v in plans.items() if not v['feasible']}})
            continue
        layout['geometric_validation'] = {'envelope': envelope, 'feasible_actions': [p for p, v in plans.items() if v['feasible']],
            'physics_executed': False, 'scope': 'Frozen geometric filter only; no learned policy or execution outcome used.'}
        accepted.append(layout)
        counts[family] += 1
        if len(accepted) == amount:
            break
    (ROOT / 'artifacts/navigation-v23' / (partition + '-generation-rejections.json')).write_text(json.dumps(rejected, indent=2) + '\n')
    assert len(accepted) == amount, (partition, counts)
    target.write_text(json.dumps(accepted, indent=2) + '\n')
    manifest[partition] = {'count': len(accepted), 'sha256': fingerprint(accepted),
        'path': str(target.relative_to(ROOT)), 'static_rejections': len(rejected), 'family_counts': counts,
        'physical_evaluation_opened': False}
    print(partition, len(accepted), 'layouts; static rejections', len(rejected), flush=True)
if existing_manifest is not None:
    assert manifest.keys() == existing_manifest.keys()
    for partition in manifest:
        for key in ['count', 'sha256']:
            assert manifest[partition][key] == existing_manifest[partition][key], (partition, key)
    print('Verified existing split hashes; preserved the immutable manifest. The navigation test cohort cannot be reused for tuning; the separate sequence cohort remains reserved.', flush=True)
else:
    (PUBLIC / 'split-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
