"""Write the final result summary from the checked numerical artifacts."""
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence/visual-motion-v22'
audit = json.loads((EVIDENCE / 'assessment.json').read_text())
report = json.loads((ROOT / 'web/desk/visual-motion-v22/report.json').read_text())
assert report['evaluation_complete'] and audit['fresh_pairs'] == 4
LIVE = 'https://howdymary--mochi-visual-motion-v22-demo-web.us-east.modal.run/'
counts = f"reference {audit['fresh_parent_qualified']}/4, recovery candidate {audit['fresh_candidate_qualified']}/4"
qualified = [v for v in audit['pairs'] if v['partition'] == 'fresh' and v['parent_qualified'] and v['candidate_qualified']]
efficiency = (f"In the only mutually qualified fresh pair, the candidate used {qualified[0]['candidate_steps'] - qualified[0]['parent_steps']} additional steps and took {qualified[0]['candidate_seconds'] - qualified[0]['parent_seconds']:.2f} seconds longer. No complete-route efficiency gain was demonstrated." if len(qualified) == 1 else
    'Complete-route efficiency must be assessed only on pairs where both versions qualify.')
rows = []
for p in audit['pairs']:
    def result(side):
        return 'qualified' if p[side + '_qualified'] else 'completed, unqualified' if p[side + '_complete'] else p[side + '_failure'] or 'incomplete'
    rows.append(f"| {p['partition']} {p['seed']} | {result('parent')} | {result('candidate')} | {p['parent_steps']} / {p['candidate_steps']} | {p['parent_seconds']:.2f} / {p['candidate_seconds']:.2f} |")
phases = [p for p in audit['recovery_phase_pairs'] if p['partition'] == 'fresh' and p['both_successful']]
ratios = [100 * (1 - p['candidate_jerk_rms'] / p['parent_jerk_rms']) for p in phases if p['parent_jerk_rms'] > 0]
phase_summary = (f"Across {len(ratios)} available paired successful recovery phases in the fresh continuous attempts, the median observed arm-jerk reduction was {median(ratios):.1f}%. "
    "These phases occur in trajectories that can reach different physical states, and later failures remain in the cohort. This is a descriptive phase measurement, not an independent set of matched-state trials or proof of improved complete-route reliability.") if ratios else 'No paired fresh recovery phases were available.'
report['motion_summary'] = (f"Fresh complete-route qualification: {counts}. The matched recovery component had {audit['recovery_component_jerk_reduction_pct']:.1f}% lower measured arm jerk with {audit['recovery_component_time_increase_pct']:.1f}% more time. "
    + efficiency + ' GMR walking and turning results were mixed. Native gait weights stayed fixed; zero new optimizer updates.')
for p in [ROOT / 'web/desk/visual-motion-v22/report.json', EVIDENCE / 'results.json']:
    p.write_text(json.dumps(report, indent=2) + '\n')
qps = sum(v.get('reference_receipts', {}).get('mink_solve_ik_calls', 0) if v.get('reference_receipts') else 0 for v in report['experiments'].values())
text = f"""# Visual and motion integration V22

[Appearance comparison]({LIVE}) · [Physical comparisons]({LIVE}?mode=motion) · [Preserved C21 demo](https://howdymary--mochi-inkling-v21-demo-web.us-east.modal.run/) · [Methods](visual-motion-v22-methods.md) · [Protocol](visual-motion-v22-protocol.md)

V22 adds a new G1 finish and an isolated GMR/mink controller-reference experiment. It preserves the existing physical executor, archived results and deployed demo. Appearance mode uses identical recorded movement on both sides. Motion mode uses real physical attempts rendered with the same appearance.

## Measured results

The matched development recovery component passed on both controllers. Measured arm jerk fell from 2.175 to 1.542 rad/s³, a {audit['recovery_component_jerk_reduction_pct']:.1f}% reduction. Jerk measures how quickly joint acceleration changes. Recovery took 2.113 rather than 2.361 seconds in the reference and candidate respectively, so the gentler candidate was {audit['recovery_component_time_increase_pct']:.1f}% slower. Arm travel was essentially unchanged. The candidate changes both timing and IK reference generation; the experiment does not isolate a benefit from mink alone.

Both development pairs completed all four tasks within the existing quality limits. Fresh complete-route qualification was {counts}. Both versions qualified on {audit['paired_qualified_fresh']} of the four fresh pairs. The small cohort does not establish broad robustness. A completed attempt can remain unqualified because of the frozen heading, support or smoothness requirements. Limits were not relaxed after seeing results.

{efficiency}

| Scenario | Reference | Recovery candidate | Steps, reference / candidate | Physical seconds, reference / candidate |
| --- | --- | --- | ---: | ---: |
{chr(10).join(rows)}

{phase_summary}

The GMR leg residual passed its matched walking and turning diagnostics. Straight walking used 112 rather than 110 steps, with slightly more time, sliding and sway. Turning used 130 rather than 132 steps and about 29% less loaded-foot sliding, with increased torso sway and native joint acceleration. These are two components from one development trajectory. GMR changes were not promoted into the selected full-route candidate.

An arm-posture blend during walking caused a drawer contact and was rejected. Five earlier walking diagnostics were confounded by an adapter bug that clipped native actuator commands. Those attempts are retained. After correction, a zero-blend control reproduced the reference trajectory, step events and component metrics exactly. The recovery-only candidate leaves native walking untouched.

The faster mink recovery candidate also passed its component but increased measured jerk from 2.175 to 3.477 rad/s³. It was rejected. The gentler candidate's improvement includes a timing tradeoff.

## Actual library use

GMR's unchanged retargeting core processed 158 CMU walking frames in the calibrated run and made 628 mink solves. An earlier unsuitable mapping processed another 158 frames and made 565 solves. Both outputs and their hashes are retained. The calibrated mapping still has limited contact and phase validation; these tests do not evaluate a trained imitation policy.

The physical controller experiments made {qps} further mink solves in a separate reference process. Its QP holds the reference model's base, legs and inactive arm unchanged while producing bounded arm references. The physical robot's base remains free in the original MuJoCo 3.3.7 executor, which tracks arm references through actuators. GMR root trajectories are never assigned to the physical robot. Native gait weights remain fixed, and this pilot performs zero Tinker optimizer updates. Exa and past.dev were not called in this library pilot. Their earlier studies remain in the preserved project.

The pinned reference environment uses mink 1.4.0 and MuJoCo 3.10.0. GMR is pinned to `25f56db79ac411258b377b6d4ccba0c8ff3372ac`. Motion data comes from CMU Graphics Lab recording 07_01 through Bruce Hahne's BVH conversion. Sources, permissions, input hashes, calibration and dependency versions are in [reference-environment.json](../evidence/visual-motion-v22/reference-environment.json).

## Rendering

The new viewer adds a satin shell, brushed metal and polymer detail, softer lighting, SMAA antialiasing, textured wood cabinetry and a cosmetic code-editor display. Blender adds UVs and PBR finishes to a separate model. All 44 body bindings and body transforms are preserved. Maximum measured decoded body-bound difference is 0.000447 mm. Task-relevant dimensions and recorded movement are unchanged.

The authored model is 12.65 MB and its compressed version is 8.53 MB. The untouched original is 8.19 MB. Compression reduces the newly authored asset's size; it does not make it smaller than the original model. No frame-rate gain was measured.

The replay includes synchronized physical-time playback, task jump buttons, foot and arm views, restored-state component labels, complete from-reset attempts and explicit failed quality checks. Component clips are never spliced into a purported continuous success.

## Verification and cost

The audit verified all {audit['preserved_files']} frozen files, raw recording hashes, identical paired initial states, unchanged full-route qualification and the zero-blend control. It also checks that the selection freeze predates fresh attempts. Physical accounting is {audit['physical_attempts']} attempts and {audit['wall_seconds'] / 3600:.3f} summed single-thread attempt wall-hours, within the 32-attempt and four-hour limits. Reference generation and asset authoring were separate local work; their wall time was not fully instrumented. These figures are not a service invoice.

Physics and reference generation ran locally. Modal hosts a separate static comparison app. The original app remains on its previous release. The new delivery branch and alternate Git index preserve the active checkout and its index.

Public [arm telemetry](../evidence/visual-motion-v22/arm-telemetry.json.gz) retains unrounded measured joint positions and timestamps for each recovery phase and component. Run `PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/check_visual_v22_arm_data.py` to recompute the published arm measurements. Public video poses are rounded for size; raw physical artifacts remain separate and are identified by SHA-256.

[Numerical assessment](../evidence/visual-motion-v22/assessment.json) · [All experiments and outcomes](../evidence/visual-motion-v22/results.json) · [Asset audit](../evidence/visual-motion-v22/asset-audit.json) · [Recording hashes](../evidence/visual-motion-v22/recording-manifest.json)
"""
# Keep the causal timing comparison readable and explicit.
text = text.replace('Recovery took 2.113 rather than 2.361 seconds in the reference and candidate respectively',
    'Recovery took 2.113 seconds for the reference and 2.361 seconds for the candidate')
(ROOT / 'docs/visual-motion-v22-findings.md').write_text(text)
readme = ROOT / 'README.md'
existing = readme.read_text()
begin = '## V22: visual materials and isolated GMR/mink tests\n'
if begin in existing:
    start = existing.index(begin)
    end = existing.index('\n## ', start + len(begin))
    existing = existing[:start] + existing[end + 1:]
section = f"""{begin}
[Visual before/after]({LIVE}) · [Physical motion tests]({LIVE}?mode=motion) · [Findings](docs/visual-motion-v22-findings.md) · [Reproduce](docs/visual-motion-v22-methods.md)

The separate V22 viewer adds authored G1 materials, softer lighting, antialiasing and a detailed laptop display. Appearance comparisons use identical physical recordings. The original demo and all {audit['preserved_files']} frozen files remain unchanged.

Actual GMR retargeting and mink IK ran in an isolated environment. A gentler recovery controller reduced measured arm jerk by {audit['recovery_component_jerk_reduction_pct']:.1f}% in one matched component, with {audit['recovery_component_time_increase_pct']:.1f}% more recovery time. Both development pairs qualified. Fresh complete-route qualification was {counts}. Walking and turning results were mixed; GMR gait changes were not promoted. The viewer retains full attempts and failures. This is controller engineering with zero new Tinker optimizer updates.

{efficiency}

"""
head, rest = existing.split('\n', 1)
readme.write_text(head + '\n\n' + section + rest.lstrip('\n'))
print(json.dumps({'findings_written': True, 'fresh_qualification': counts, 'paired_recovery_phases': len(ratios)}))
