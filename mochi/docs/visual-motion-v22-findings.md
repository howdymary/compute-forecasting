# Visual and motion integration V22

[Appearance comparison](https://howdymary--mochi-visual-motion-v22-demo-web.us-east.modal.run/) · [Physical comparisons](https://howdymary--mochi-visual-motion-v22-demo-web.us-east.modal.run/?mode=motion) · [Preserved C21 demo](https://howdymary--mochi-inkling-v21-demo-web.us-east.modal.run/) · [Methods](visual-motion-v22-methods.md) · [Protocol](visual-motion-v22-protocol.md)

V22 adds a new G1 finish and an isolated GMR/mink controller-reference experiment. It preserves the existing physical executor, archived results and deployed demo. Appearance mode uses identical recorded movement on both sides. Motion mode uses real physical attempts rendered with the same appearance.

## Measured results

The matched development recovery component passed on both controllers. Measured arm jerk fell from 2.175 to 1.542 rad/s³, a 29.1% reduction. Jerk measures how quickly joint acceleration changes. Recovery took 2.113 seconds for the reference and 2.361 seconds for the candidate, so the gentler candidate was 11.7% slower. Arm travel was essentially unchanged. The candidate changes both timing and IK reference generation; the experiment does not isolate a benefit from mink alone.

Both development pairs completed all four tasks within the existing quality limits. Fresh complete-route qualification was reference 1/4, recovery candidate 2/4. Both versions qualified on 1 of the four fresh pairs. The small cohort does not establish broad robustness. A completed attempt can remain unqualified because of the frozen heading, support or smoothness requirements. Limits were not relaxed after seeing results.

In the only mutually qualified fresh pair, the candidate used 9 additional steps and took 5.87 seconds longer. No complete-route efficiency gain was demonstrated.

| Scenario | Reference | Recovery candidate | Steps, reference / candidate | Physical seconds, reference / candidate |
| --- | --- | --- | ---: | ---: |
| dev 225000 | qualified | qualified | 418 / 418 | 276.83 / 277.29 |
| dev 225001 | qualified | qualified | 430 / 418 | 278.99 / 278.04 |
| fresh 226000 | completed, unqualified | completed, unqualified | 432 / 426 | 278.09 / 278.93 |
| fresh 226001 | laptop-failed:laptop | laptop-failed:laptop | 286 / 286 | 271.02 / 271.28 |
| fresh 226002 | completed, unqualified | qualified | 416 / 414 | 283.89 / 281.92 |
| fresh 226003 | qualified | qualified | 399 / 408 | 277.59 / 283.46 |

Across 14 available paired successful recovery phases in the fresh continuous attempts, the median observed arm-jerk reduction was 17.8%. These phases occur in trajectories that can reach different physical states, and later failures remain in the cohort. This is a descriptive phase measurement, not an independent set of matched-state trials or proof of improved complete-route reliability.

The GMR leg residual passed its matched walking and turning diagnostics. Straight walking used 112 rather than 110 steps, with slightly more time, sliding and sway. Turning used 130 rather than 132 steps and about 29% less loaded-foot sliding, with increased torso sway and native joint acceleration. These are two components from one development trajectory. GMR changes were not promoted into the selected full-route candidate.

An arm-posture blend during walking caused a drawer contact and was rejected. Five earlier walking diagnostics were confounded by an adapter bug that clipped native actuator commands. Those attempts are retained. After correction, a zero-blend control reproduced the reference trajectory, step events and component metrics exactly. The recovery-only candidate leaves native walking untouched.

The faster mink recovery candidate also passed its component but increased measured jerk from 2.175 to 3.477 rad/s³. It was rejected. The gentler candidate's improvement includes a timing tradeoff.

## Actual library use

GMR's unchanged retargeting core processed 158 CMU walking frames in the calibrated run and made 628 mink solves. An earlier unsuitable mapping processed another 158 frames and made 565 solves. Both outputs and their hashes are retained. The calibrated mapping still has limited contact and phase validation; these tests do not evaluate a trained imitation policy.

The physical controller experiments made 2436 further mink solves in a separate reference process. Its QP holds the reference model's base, legs and inactive arm unchanged while producing bounded arm references. The physical robot's base remains free in the original MuJoCo 3.3.7 executor, which tracks arm references through actuators. GMR root trajectories are never assigned to the physical robot. Native gait weights remain fixed, and this pilot performs zero Tinker optimizer updates. Exa and past.dev were not called in this library pilot. Their earlier studies remain in the preserved project.

The pinned reference environment uses mink 1.4.0 and MuJoCo 3.10.0. GMR is pinned to `25f56db79ac411258b377b6d4ccba0c8ff3372ac`. Motion data comes from CMU Graphics Lab recording 07_01 through Bruce Hahne's BVH conversion. Sources, permissions, input hashes, calibration and dependency versions are in [reference-environment.json](../evidence/visual-motion-v22/reference-environment.json).

## Rendering

The new viewer adds a satin shell, brushed metal and polymer detail, softer lighting, SMAA antialiasing, textured wood cabinetry and a cosmetic code-editor display. Blender adds UVs and PBR finishes to a separate model. All 44 body bindings and body transforms are preserved. Maximum measured decoded body-bound difference is 0.000447 mm. Task-relevant dimensions and recorded movement are unchanged.

The authored model is 12.65 MB and its compressed version is 8.53 MB. The untouched original is 8.19 MB. Compression reduces the newly authored asset's size; it does not make it smaller than the original model. No frame-rate gain was measured.

The replay includes synchronized physical-time playback, task jump buttons, foot and arm views, restored-state component labels, complete from-reset attempts and explicit failed quality checks. Component clips are never spliced into a purported continuous success.

## Verification and cost

The audit verified all 276 frozen files, raw recording hashes, identical paired initial states, unchanged full-route qualification and the zero-blend control. It also checks that the selection freeze predates fresh attempts. Physical accounting is 28 attempts and 2.234 summed single-thread attempt wall-hours, within the 32-attempt and four-hour limits. Reference generation and asset authoring were separate local work; their wall time was not fully instrumented. These figures are not a service invoice.

Physics and reference generation ran locally. Modal hosts a separate static comparison app. The original app remains on its previous release. The new delivery branch and alternate Git index preserve the active checkout and its index.

Public [arm telemetry](../evidence/visual-motion-v22/arm-telemetry.json.gz) retains unrounded measured joint positions and timestamps for each recovery phase and component. Run `PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/check_visual_v22_arm_data.py` to recompute the published arm measurements. Public video poses are rounded for size; raw physical artifacts remain separate and are identified by SHA-256.

[Numerical assessment](../evidence/visual-motion-v22/assessment.json) · [All experiments and outcomes](../evidence/visual-motion-v22/results.json) · [Asset audit](../evidence/visual-motion-v22/asset-audit.json) · [Recording hashes](../evidence/visual-motion-v22/recording-manifest.json)

Live verification checked 37 recording, asset and numerical-data hashes, all six appearance comparisons and all ten motion comparisons. Rendered body positions matched the recorded poses within the test tolerance. The original C21 app remained on its previous release. [Live files](../evidence/visual-motion-v22/live-verification.json) · [Appearance checks](../evidence/visual-motion-v22/live-appearance-browser-qa.json) · [Motion checks](../evidence/visual-motion-v22/live-motion-browser-qa.json) · [Continuous playback](../evidence/visual-motion-v22/live-playback-qa.json).
