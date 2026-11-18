# Gait modulation calibration

This is a controller engineering experiment, not a trained-model result. It does not change the frozen V7 training run or its simulator. No selected V7 policy imports this prototype.

The native Unitree network accepts a phase clock and desired velocity. `gait_control.py` adds explicit, bounded phase-rate and velocity-slew profiles while keeping the native network weights fixed. The model would need an additional declared action interface and actual post-training before any profile selection could be called learned gait modulation.

The final local calibration grid tested five profiles on three training-only goals (seeds 18000–18002), with identical initial conditions and success rules. All 15 trials reached their goals without falling. A prior nine-trial pilot is retained locally and is not an independent confirmation. These are local ARM64 trials; no cross-runtime generalization is claimed.

| Profile | Phase rate | Linear acceleration cap | Angular acceleration cap | Observation |
|---|---:|---:|---:|---|
| native | 1.00 | Original controller | Original controller | Exact original-controller ablation |
| smooth | 0.90 | 0.14 m/s² | 1.8 rad/s² | More slip and slower arrival on these goals |
| steady | 1.00 | 0.24 m/s² | 3.0 rad/s² | Small, mixed changes; worse turning slip |
| brisk | 1.05 | 0.20 m/s² | 2.4 rad/s² | Lower torso tilt, more slip and slower arrival |
| measured | 1.00 | 0.30 m/s² | 1.8 rad/s² | Small, mixed changes; worse turning slip |

Cadence changes are not promoted. Neither slower nor faster phase produced a consistent physical gain. The slew-limited candidates require matched Modal experiments and a frozen motion objective before a future training study. The current demonstration retains the native gait and reports learned walking-command improvement separately.

`tests/test_gait_control.py` confirms the native profile produces exactly equal joint positions to the original controller across 600 actual physics steps. A separate check bounds vector command acceleration. No root forces, foot locking or animation are added.

Reproduce the calibration:

```sh
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/calibrate_gait.py --out mochi/artifacts/gait-calibration/reproduction.json
```

The numerical receipt, source hash and retained trajectory hash are in `mochi/evidence/gait-calibration/results.json`. Loaded-foot slip here spans each complete walking-only episode; it is an estimate from sampled loaded contact-point velocities. None of these three-goal comparisons establishes a perceptual naturalness improvement.
