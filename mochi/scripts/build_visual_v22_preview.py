"""Prepare appearance comparisons from identical retained physical recordings."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web/desk'
OUT = WEB / 'visual-motion-v22'
OUT.mkdir(parents=True, exist_ok=True)
old = json.loads((WEB / 'inkling-v21/manifest.json').read_text())
assets = json.loads((ROOT / 'evidence/visual-motion-v22/asset-audit.json').read_text())
scenarios = []
for scenario in old['scenarios']:
    file = scenario['versions'][-1]['file']
    meta = old['recordings'][file]
    clean = {'sha256': meta['sha256'], 'steps': meta['steps']['attempts'], 'success': meta['qualified_complete'], 'complete': meta['complete'],
        'failure': meta['failure'], 'duration': meta['duration'], 'component': False}
    scenarios.append({'id': scenario['id'], 'label': scenario['label'],
        'before': '../inkling-v21/' + file, 'after': '../inkling-v21/' + file,
        'before_meta': clean, 'after_meta': clean,
        'before_label': 'ORIGINAL MATERIALS & LIGHTING', 'after_label': 'V22 MATERIALS & LIGHTING',
        'scope': 'APPEARANCE COMPARISON · Identical recorded MuJoCo movement, task outcomes, camera settings and playback speed. No new motion is claimed in this mode.',
        'finding_title': 'Identical physical movement.',
        'finding_detail': 'Both panes share recording ' + meta['sha256'][:12] + '. The robot finish and lighting change. Original geometry, joint pivots and body bindings are preserved; the compressed model differs by less than 0.001 mm in measured body bounds.'})
manifest = {'study': 'mochi-visual-motion-v22', 'scene': old['scene'], 'scenarios': scenarios,
    'default_scenario': 'held-out-223002', 'summary': 'Compare the original finish with authored metal and polymer surfaces, procedural detail and revised studio lighting. Every appearance comparison uses one physical recording on both sides.'}
(OUT / 'appearance-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
motion = OUT / 'motion-manifest.json'
if not motion.exists():
    motion.write_text(json.dumps({'study': manifest['study'], 'scene': old['scene'], 'scenarios': [],
        'summary': 'GMR and mink are isolated from the frozen physical executor. Motion candidates will appear here only after measured physical attempts.'}, indent=2) + '\n')
report_path = OUT / 'report.json'
report = json.loads(report_path.read_text()) if report_path.exists() else {}
report.update(study=manifest['study'], asset_audit=assets,
    asset_summary=f"All {assets['preserved_body_bindings']} body bindings are preserved. Maximum bounds difference: {assets['max_world_bounds_error_m'] * 1000:.6f} mm. Authored asset: {assets['authored_bytes']/1e6:.2f} MB; compressed: {assets['optimized_bytes']/1e6:.2f} MB. Original asset: {assets['source_bytes']/1e6:.2f} MB.",
    motion_summary=report.get('motion_summary', 'GMR retargeting and mink reference generation have run. Physical candidate evaluation is in progress. No new model weights have been trained.'))
(OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'appearance_cases': len(scenarios), 'identical_physics': True}))
