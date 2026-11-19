# Turning toward the next waypoint

The previous flat-desk navigator held a task-facing yaw while asking the G1 gait to translate in both body axes. This made long sideways travel possible even when the next corridor required a different heading.

The new navigator chooses a travel bearing from the measured root position to the next waypoint. It commands yaw through the existing gait actuators, pauses translation for heading errors above 35°, then walks mainly forward. Within 35 mm of a task pose it aligns to the required task heading and permits small positioning corrections. The final stop requires actual loaded contacts and a supported dwell.

Robot and object transforms come from MuJoCo. No physical root is moved onto a spline, no rendered robot is rotated independently, and no base support force is added. The native ONNX gait, book contact controller, manipulation profiles and recovery primitives are unchanged. This is navigation engineering, with **zero new Tinker optimizer updates**. The running V13 model comparison keeps its original 134-file physics/control snapshot frozen.

## Physical comparisons

The replay manifest contains source hashes, durations, task results and directional measurements for each accepted comparison. Both sides begin in the same physical state and play at the same speed. Each clip is one uninterrupted episode.

The corner comparison uses `corner-baseline-1` and `corner-directional-4`, seed 81000. Using the same trajectory-based measurement on both sides:

| Corner probe | Previous navigation | Directional navigation |
|---|---:|---:|
| Travel within 25° of body heading | 71.3% | 92.9% |
| Distance-weighted heading error | 30.2° | 13.8° |
| Lateral travel | 8.31 cm | 4.48 cm |
| Physical time | 17.0 s | 20.2 s |
| Falls / forbidden contacts | 0 / 0 | 0 / 0 |

Turning takes time; this change does not establish a faster route. Travel measurements average velocity over approximately one gait cycle and exclude stationary turns, low-speed balance and book traversal. The rendered motion is unfiltered. These are development examples in one fixed layout, not a robustness benchmark.

The fresh uninterrupted `full-directional-1` run also passed all four tasks, both book traversals and four arm recoveries, with no falls, forbidden contacts or applied base force. Against the retained `continuous-four-task-reference-2`, both start from the exact same seed-41001 physical state:

| Continuous route | Previous navigation | Directional navigation |
|---|---:|---:|
| Travel within 25° of body heading | 24.3% | 95.2% |
| Distance-weighted heading error | 80.6° | 14.5° |
| Physical time | 251.5 s | 265.7 s |
| Verified tasks | 4/4 | 4/4 |
| Falls / forbidden contacts | 0 / 0 | 0 / 0 |

[Execution evidence and attempt ledger](../evidence/directional-v14/results.json) · [Replay manifest and source hashes](../web/desk/directional-v14/manifest.json).

Book descent retains the validated backward contact controller. After closing the laptop, a short physical retreat/clearance step avoids sweeping a foot through its edge before turning. These local movements are deliberate; long flat-desk transit now follows the travel heading.

## Attempts and provenance

Local artifacts live in `mochi/artifacts/directional-v14/`. The append-only attempt IDs and bounded ledger retain failed probes, including an over-constrained near-waypoint approach, a rejected parked-arm variant, and the first complete-route attempt that contacted the laptop with its hip. The laptop station target was moved 5 mm right and 5 mm back, then checked from a saved supported state before a fresh complete rollout. Diagnostic continuations are labelled and cannot qualify as uninterrupted full-sequence demos.

Each full attempt saves a source snapshot and hashes. Recorded checkpoints from earlier training campaigns and forecasting artifacts remain separate. The local engineering cap is 20 rollouts and 5,400 accumulated wall seconds; this refinement does not launch a new training campaign.

## Run from the repository root

```sh
PYTHONPATH=mochi/src mochi/.venv/bin/python -m pytest -q mochi/tests/test_directional_v14.py

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONPATH=mochi/src mochi/.venv/bin/python \
  -m mochi.directional_v14.probe --id my-turn-probe --mode turn

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONPATH=mochi/src mochi/.venv/bin/python \
  -m mochi.directional_v14.sequence --id my-full-directional-run

PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/build_directional_preview.py \
  --full my-full-directional-run
node mochi/scripts/check_directional_ui.mjs
python3 -m http.server 8994 --directory mochi/web/desk
```

Open `/directional.html`. Exporting a full comparison requires both episodes to pass and their initial poses and scene to match. The public viewer has no provider credentials. Its independent Modal app is `mochi-directional-v14-demo`; the additive workflow injects the existing Modal secret references without replacing the training viewer.
