# GMR and mink controller-reference pilot

V22 has two independent comparisons. Appearance mode renders the same retained C21 recording with two material and lighting configurations. Motion mode renders different, physically simulated attempts with the same revised appearance. Changing the rendering does not count as improved control.

## Preserved executor

The physical executor remains on MuJoCo 3.3.7. C21's accepted laptop-clearance waypoint, H0/C/P5/G0 task profiles, W10 walking, R4 parent recovery, native ONNX gait and success checks are unchanged. The pre-work freeze covers 276 source, configuration, rendering and asset files. New controllers are process-local adapters in `src/mochi/visual_motion_v22/`; they restore the original functions on exit. No existing deployment is replaced.

GMR and mink run in a separate Python environment using MuJoCo 3.10.0. Neither can step the authoritative simulation or assign its floating-base pose. A JSON-lines worker returns arm reference configurations to the old executor. The original position actuators track those references through simulated forces and contacts. Native gait weights are fixed. This pilot performs no Tinker optimizer updates.

## What GMR did

[GMR](https://github.com/YanjieZe/GMR) is pinned to commit `25f56db79ac411258b377b6d4ccba0c8ff3372ac`. The unchanged `GeneralMotionRetargeting` core retargeted 158 frames from CMU Graphics Lab walking recording 07_01 to its G1 model. It called mink's IK solver 628 times in the calibrated run. Only the core was loaded; optional Torch, viewer and streaming imports were not installed.

The input is the [Bruce Hahne BVH conversion](https://github.com/una-dinosauria/cmu-mocap/blob/master/data/007/07_01.bvh) of CMU data. Its Git blob is checked against `0e50b7db19c7ea0bf2cd3df942f82642b9b22ebc`. [CMU's FAQ](https://mocap.cs.cmu.edu/faqs.php) describes its reuse terms. The conversion credits CMU, Bruce Hahne and contributors. The input is a walking clip, not task demonstrations or a stair-climbing controller.

The default LaFAN mapping produced unsuitable CMU poses. That attempt is retained. The calibrated run explicitly aligns CMU neutral bone bases and per-landmark scale to a G1 T-pose before calling the unchanged retargeter. This is a small, custom calibration, not a validated general retargeting pipeline. Root orientation, scene scale, foot contact and dynamic balance do not become correct merely because IK converges.

Physical tests use a very small, bounded joint-angle residual derived from the retargeted leg motion, added through the existing gait's actuator commands. Root trajectories from GMR are never applied. Arm medians were also tested as a weak posture prior. This does not train a locomotion policy, transplant a human gait, or demonstrate hardware transfer.

The prototype indexes the retargeted clip with the native controller's cycle phase. It does not extract and validate a contact-aligned human stride cycle. Its calibration and timing are therefore additional limitations of these tests, not evidence against GMR as a general method. Natural locomotion would require validated contact and phase correspondence, dynamic tracking and a broader evaluation.

## What mink did

[mink 1.4.0](https://github.com/kevinzakka/mink) generates joint-space reference trajectories against the exported, unchanged Mochi model. A posture task follows a quintic target over time. A hard DOF-freezing constraint holds the base, legs and inactive arm. Configuration and velocity limits apply to the controlled arm; noncontrolled joints are frozen at their input configuration. The solver is daqp with a 20 ms reference interval.

References use Hermite interpolation and are tracked by physical arm actuators. R4's final rest pose, clock clearance waypoint, contact checks, joint-error tolerance, speed tolerance and dwell criterion are preserved. The gentler candidate scales the requested duration by 1.12. Duration and solver changes were not isolated in an ablation, so a smoother return cannot be attributed to mink alone. This is a controller-engineering change using mink; mink does not supply the task state machine or balance policy. These tests use no collision-avoidance IK task, so references still require contact validation in physics.

## Diagnostics and measurements

Component comparisons restore the exact same saved C21 state. They preserve control-critical recent measurements, discard only the rendering history, then execute the new component through actuators. Their playback clocks are shifted to zero. They are explicitly labelled as restored-state components and are never assembled into a purported continuous success.

Full comparisons start at reset and run the complete clock, drawer, laptop and globe sequence without restoring state. The parent and candidate use the same seed, model, initial state, route and task profiles. The candidate changes recovery alone. Development seeds are 225000 and 225001. Final seeds 226000 through 226003 are reserved until a selection record is written.

Arm travel and finite-difference velocity, acceleration and jerk come from measured joint positions at recorded telemetry times, not desired commands. Jerk is sensitive to sample cadence and transitions; it is an engineering diagnostic rather than a validated perceptual-naturalness score. Native-gait acceleration and loaded-foot sliding use the existing sensors and definitions. A brief failed attempt cannot win an efficiency comparison.

An initial adapter incorrectly clipped native position-actuator commands, which also encode torque and gravity compensation. Those attempts are retained as confounded diagnostics. The corrected zero-blend control reproduces the parent's entire recorded component trajectory, step events and metrics exactly. Only corrected walking attempts support comparisons of GMR or mink references.

## Visual assets

Blender 5.1.2 adds UVs and authored PBR finishes to a copy of the original G1 model. Joint pivots and geometry are preserved. Original procedural normal and roughness maps are CC0. The separate viewer adds softer lighting, SMAA antialiasing and a cosmetic laptop display. Task motion still comes from recorded MuJoCo body transforms.

glTF Transform 4.5.1 and meshoptimizer 1.3.0 compress the authored model without joining body nodes or simplifying geometry. The decoded asset retains all 44 MuJoCo body bindings and has zero measured body-transform difference. Maximum measured world-bound difference is less than 0.001 mm. The authored model is 12.65 MB and its compressed version is 8.53 MB. The untouched original is 8.19 MB, so this is not a size reduction relative to the original finish. No frame-rate improvement is claimed.

## Reproduction

Run from the repository root with the existing physical environment and robot assets installed. Use Python 3.11. The isolated reference environment does not replace `mochi/.venv`.

```sh
python3 -m venv mochi/.cache/visual-motion-v22/motion-env
mochi/.cache/visual-motion-v22/motion-env/bin/python -m pip install -r mochi/configs/visual-motion-v22/reference-requirements.txt
git clone https://github.com/YanjieZe/GMR.git mochi/.cache/visual-motion-v22/GMR
git -C mochi/.cache/visual-motion-v22/GMR checkout 25f56db79ac411258b377b6d4ccba0c8ff3372ac
mkdir -p mochi/artifacts/visual-motion-v22/source
curl -fL https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/data/007/07_01.bvh -o mochi/artifacts/visual-motion-v22/source/07_01.bvh
PYTHONPATH=mochi/src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 mochi/.cache/visual-motion-v22/motion-env/bin/python -m mochi.visual_motion_v22.references
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/export_visual_v22_model.py
```

The model export preserves an existing file. It exports from an unstepped world on a new checkout; the local XML contains the mesh directory for that checkout. Motion tests use immutable experiment IDs and a shared, locked budget ledger. Do not reuse an existing ID.

```sh
PYTHONPATH=mochi/src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 mochi/.venv/bin/python -m mochi.visual_motion_v22.experiment --id reproduction-parent-226000 --mode full --seed 226000
PYTHONPATH=mochi/src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 mochi/.venv/bin/python -m mochi.visual_motion_v22.experiment --id reproduction-mink-226000 --mode full --seed 226000 --candidate mochi/configs/visual-motion-v22/mink-recovery-only.json
```

These are examples for a separate reproduction campaign with its own copied ledger, within the declared budget. Archived development snapshots are not required to reproduce the from-reset tests. Their hashes identify the local component diagnostics; they are not included in Git because they contain large histories.

To rebuild visuals, install the pinned Node packages into the isolated asset-tools directory, then run the following. The scripts generate new files only.

```sh
mkdir -p mochi/.cache/visual-motion-v22/asset-tools
cp mochi/configs/visual-motion-v22/asset-package.json mochi/.cache/visual-motion-v22/asset-tools/package.json
cp mochi/configs/visual-motion-v22/asset-package-lock.json mochi/.cache/visual-motion-v22/asset-tools/package-lock.json
npm ci --prefix mochi/.cache/visual-motion-v22/asset-tools --ignore-scripts --no-audit --no-fund
mochi/.venv/bin/python mochi/scripts/build_visual_v22_materials.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python mochi/scripts/build_visual_v22_robot.py
node mochi/scripts/optimize_visual_v22.mjs
python3 mochi/scripts/build_visual_v22_stage.py
python3 mochi/scripts/build_visual_v22_preview.py
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/build_visual_v22_motion.py
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/write_visual_v22_findings.py
python3 -m http.server 4122 --directory mochi/web/desk
```

Open `http://localhost:4122/visual-motion-v22.html`. `?mode=motion` selects physical comparisons. The public replay needs no credentials. Deploying its new Modal app uses the existing authenticated Modal profile and `mochi/scripts/deploy_visual_motion_v22.py`. Exa, past.dev and Tinker are not called in this isolated library pilot; their previous studies remain available in the preserved demo and evidence.
