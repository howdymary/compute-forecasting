# MOCHI — Navigation and Manipulation Policy Learning

A 22.1 cm Unitree G1 walks across one desk to silence an alarm, close a drawer,
close a laptop and align a globe. MuJoCo produces the motion and outcomes.
The web demo replays measured trajectories; Blender renders the same recordings.

[Trained checkpoints](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/)
· [Route study](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/planning.html)
· [V7 results](docs/refinement-v7-results.md)
· [Planning methods](docs/path-planning-study.md)

## What has actually run

**Completed V7 training:** Tinker post-trained Qwen3.5-4B with rank-16 LoRA for
96 optimizer updates. Every update included walking-command selection and all
four task-profile domains. The native Unitree gait network, standing balance
and arm IK were fixed. This was supervised controller selection from simulation
state, not motor-level gait training.

The selected model completed one of four held-out full routes and reached all
20 waypoints without falling. It reached eight of eight isolated navigation
goals, versus zero for the starting weights. The fixed controller also reached
eight and completed one of four full routes. Superiority over fixed control
was not established. Alarm performance regressed in isolated tests; laptop
reliability remains limited. The viewer retains six checkpoints and all four
test pairs, including failures.

**Current route study:** structured reference planning, local targets, latched
final alignment and measured stopping drift are being tested with fixed control.
This phase has performed **zero additional Tinker optimizer updates**.
[Its calibration results](evidence/planning/results.json) are an engineering
comparison, not a gain from new model weights.

The storage audit found 100 checkpoints at the free checkpoint-count limit,
including six Mochi full states. They were preserved; billing was not changed.
Further training is gated on physical feasibility and durable storage.

## Inspect the demo

The original viewer shows actual V7 checkpoints, paired tests, model-decision
traces and verified memory handoffs. The successful test example was selected
after evaluation and is labeled as one of four; the default remains the
predeclared development case.

The planning viewer adds a top-down desk plan, planned/executed paths, local
targets, approach directions and tracking error. Old and new fixed-control
episodes play at the same simulation time. Top-down, follow, side and foot
views inspect the same physical sequence. The path overlay can be hidden.

Each four-task attempt preserves physical state throughout. No task resets,
teleports, external base forces or animated root motion determine the result.
The planning study's primary calibration seed, 19000, was declared before its
paired results. Proposed new held-out scenarios remain unopened.

## Sponsor integrations

| Service | Actual use | Source |
|---|---|---|
| Tinker | V7 LoRA training, saved-state recovery and inference. Planning roles use inference only. | [Training](src/mochi/curriculum/refine.py), [recovery](src/mochi/curriculum/finalize_refinement.py), [receipts](evidence/refinement-v7/results.json) |
| Modal | Pinned CPU MuJoCo trials, parallel contact calibration and paired closed-loop evaluation. | [Planning workers](src/mochi/planning/remote.py), [V7 workers](src/mochi/curriculum/remote_policy.py) |
| Exa | Failure-derived searches in the main research loop, with request IDs and source links. | [HTTP adapter](src/mochi/integrations.py), [planning loop](src/mochi/planning/baseline.py) |
| past.dev | Real ingestion, audience controls and source-verified cross-identity recalls. | [Memory client](src/mochi/desk/services.py), [planning evidence](evidence/planning/results.json) |

Search and memory have no causal ablation. Service receipts establish use,
not that either service caused a control improvement.

## past.dev challenge

### Agents

Four application roles use distinct instructions and identities: research,
policy design, experiment execution and criticism. Research writes a sourced
proposal; design recalls it; execution recalls the plan and writes results;
criticism recalls evidence and writes a verdict; research recalls the verdict.
In the planning loop, the recalled plan selects a real additional physical probe.

### Layers

Prompts hold working context. past.dev holds findings and conclusions.
Versioned code holds procedures. Exact measurements and trajectories live in
Mochi artifacts. Fixed shared and critic-only audiences enforce access;
a synthetic private canary checks isolation.

### Results

The V7 training/recovery campaign recorded 11 writes, 11 recalls and nine
verified cross-identity recalls. The new planning receipts are reported
separately in [its evidence](evidence/planning/results.json).
Dependent reads require completed ingestion and the expected source ID.

### Caveats

Canonical numerical records are resolved only after verifying recalled source
IDs. There is no silent memory fallback. Memory's performance benefit is
unestablished. Corrections retain provenance; native semantic supersession
is not assumed.

## Run from the repository root

Reuse the existing Mochi environment when present. For a new environment:

```sh
uv venv --python 3.11 mochi/.venv
uv pip install --python mochi/.venv/bin/python torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python mochi/.venv/bin/python -e './mochi[remote,dev,plots]' pyyaml==6.0.2
mochi/.venv/bin/python mochi/scripts/fetch_visual_models.py
```

Backend integrations use existing `TINKER_API_KEY`, `EXA_API_KEY`,
`PAST_API_KEY`, `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`.
See [integration setup](docs/integrations.md). Mochi workflows explicitly
inject existing GitHub secret references. No credential belongs in the viewer.

Local planning and fixed control need no service credentials:

```sh
PYTHONPATH=mochi/src mochi/.venv/bin/python -m mochi.planning.route
PYTHONPATH=mochi/src mochi/.venv/bin/python -m mochi.planning.follower --seed 19000
mochi/.venv/bin/python mochi/scripts/draw_route.py
PYTHONPATH=mochi/src mochi/.venv/bin/python -m pytest -q mochi/tests/test_planning.py
python3 -m http.server 8047 --directory mochi/web/desk
```

Open `http://localhost:8047/planning.html` or `curriculum.html`.
The additive `mochi-planning*.yml` workflows run remote calibration and actual
service handoffs. The [next training plan](configs/path-training-plan.json)
has not run. Rerunning the old V7 entrypoint is not a continuation of the new
tracking interface.

Render an episode exported from the workflow artifact:

```sh
blender -b -t 4 -P mochi/scripts/render_curriculum.py -- \
  --input mochi/artifacts/planning/episode.json \
  --out mochi/artifacts/planning/render --time 30 --samples 32 \
  --camera topdown --route mochi/configs/desk-route-v1.json
```

Use `--camera side` or `--camera feet` for inspection.
`--animate` writes the recorded animation into a Blender scene. Large outputs
and caches stay out of Git.

## Limits and provenance

This is a small fixed-layout simulation study. Waist and fingers are fixed.
There is no camera input or hardware validation. Seven sampled planning
configurations and a 25 Hz replay audit do not certify continuous collision
freedom. Tracking/braking margins remain assumptions to test. Longer paths,
failed tasks and checkpoint regressions are retained.

The original supported puck hackathon slice is preserved in
[the archived README](docs/archive/initial-puck-slice.md). Free walking,
the four-task curriculum and subsequent training are later iterations;
they are not all claimed as work built during the original hackathon.

Dependencies include MuJoCo, NumPy, SciPy, PyTorch, Three.js, Blender, FastAPI
and the service SDKs. Robot revisions, hashes and licenses are recorded in
[G1 provenance](assets/robot/g1/source.json) and
[locomotion provenance](assets/robot/locomotion/source.json).
[Scene attribution](web/desk/assets/sand3d-attribution.json) records visual assets.
The forecasting application and its archived results remain separate.
