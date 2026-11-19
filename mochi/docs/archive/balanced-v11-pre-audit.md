> **Reference invalidated by the independent walking-contact audit.** The
> legacy task counter passed, but the robot contacted the clock with its wrist,
> knee and hip. The pending training run was cancelled before gradients. The
> terrain-only check missed task-fixture contacts during walking. See
> `evidence/balance-v11/reference-audit.json`. The prior observations below are
> preserved as history; they do not establish a collision-free reference.

# Balanced desk continuation (V11)

This is a new, bounded engineering and training study. The V8 controller,
checkpoints, evaluation, and default live demo remain preserved. Three continuous local engineering references pass the independent verifier.
A remote reference is required before any V11 optimizer updates. The bounded
training campaign is launched; completed updates remain to be verified. The training, development, and held-out seed partitions
in `configs/balance-v11.json` were unopened during engineering calibration.

## Implementation

The first quasistatic controller repeatedly moved the pelvis toward each
stance foot. Detached IK audits found that a staggered support transfer could
overextend the trailing leg. Inverse-dynamics, preview-control, narrower-stance,
landing-search, and alternative-sole experiments are retained as development
attempts, including failures. Lower sway in an early failure is not a win.

The alternative reference uses a pinned, externally pretrained G1 velocity
policy with actuator-only execution. Its original task is flat-ground walking;
the source model does not establish book-climbing ability. The adapter uses
physical scaling, a bounded command filter, measured velocity feedback, and a
separate captured-stance controller. Three fixed waist joints are explicitly
represented as fixed; no 29-actuator robot is claimed. Original collision pads,
body masses, and scene geometry are used in the selected reference.

Source: [kramp/unitree-g1-29dof-velocity-mjlab](https://huggingface.co/kramp/unitree-g1-29dof-velocity-mjlab),
revision `5f79b5520040d193b3e8471188cc8e54ccd64942`, declared Apache-2.0.
File hashes and attribution are in `assets/robot/g1-v11-policy/source.json`.
The YAML source files are retained as data; Python-tagged YAML is never loaded.
The ONNX file checksum is verified before inference.

**These gait weights are fixed.** The new Tinker campaign resumes the V8-selected
Qwen decision model at cumulative update 104, then trains walking-strategy,
manipulation-profile and recovery selections. This changes high-level decision
weights, not the native gait network.

The capture-point check uses actual loaded contact points, COM position, and
COM velocity. It is a linear inverted-pendulum approximation, not a complete
centroidal stability certificate. A supported stop additionally checks foot
load and orientation. The physical root is never assigned after reset.

The alarm uses bounded absolute IK with a relaxed hand-pad orientation
objective. A recovery-verifier fork excludes intended upward-facing foot/book
support, while preserving robot/fixture collisions. Real-contact regression
tests require hand/book contact to remain invalid. The archived V8 verifier is
unchanged. Gait phase, previous actions, and filtering persist through transit
waypoints. Stops, turns, and manipulations remain physical control operations.

## Reproduce an engineering attempt

From the repository root:

```sh
python -m pip install './mochi[robotics,dev]' pyyaml==6.0.2
python mochi/scripts/fetch_visual_models.py
PYTHONPATH=mochi/src python -m mochi.balanced.sequence \
  --id my-new-reference --alarm-x -.365 --alarm-y .045 \
  --capture-margin .001 --forward-descent --descent-speed .03
PYTHONPATH=mochi/src pytest mochi/tests/test_balanced_v11.py \
  mochi/tests/test_control_v8.py mochi/tests/test_richdesk.py
```

Use the existing isolated Python runtime with CPU PyTorch installed, or install
the CPU PyTorch version used by `mochi-balanced-v11.yml`. The command reserves
an immutable attempt ID before starting and refuses to exceed the local
rollout ceiling. Each artifact retains the complete measured episode, failure
reason, code hashes, support measurements, and original outcomes. A complete
sequence is never assembled from separate successful clips.

## Services and budgets

Local credentials are absent. The additive workflow explicitly injects the
existing GitHub Actions secret references into backend execution. It uses a
Mochi-specific Modal app, artifacts, and past.dev identities/audiences. No
forecasting memory or deployment is overwritten.

`balanced/research.py` performs one Exa search from the observed descent
failure, passes sourced evidence through verified past.dev recalls, uses a
Tinker inference decision to choose a bounded capture margin, and runs two
matched physical probes on Modal. It cannot create a training client. The
report distinguishes inference from optimizer operations and retains service
receipts. API retry/poll calls are visible separately from logical writes and
recalls. No claim that search or memory improved performance is made without
an ablation.

The continuation budget is 64 local rollouts, 256 Modal rollouts, 8 CPU-hours,
32 optimizer updates, 2 million training-token presentations, 200,000 inference
tokens, 8 Exa searches, and 20/40 past.dev writes/recalls. The first remote probe
is bounded to two rollouts, one search, five writes/recalls and one inference
decision. Unused training budget is not consumed while feasibility is closed.

## past.dev challenge

- **Agents:** experimenter, researcher, designer, critic have separate identities.
- **Layers:** shared sourced findings in past.dev; code in Git; exact physics and
  trajectories in artifact storage; individual working prompts in memory.
- **Results:** see the new remote execution report for source-ID-verified reads
  and actual author/reader handoffs; previous V10 receipts remain separate.
- **Caveats:** runtime evidence is required. A configured integration is not
  proof of a completed call, training update, or measured causal benefit.

## Current limits

Three complete runs on engineering seed 31000 pass ascent, alarm, descent,
drawer, laptop, globe and four recoveries. Two use different drawer profiles;
the third reproduces the frozen selector interface. This is not a generalization
result. The complete reference takes 136–139 simulated seconds. Final object
positions, speeds, zero base force and supported finish are independently
verified in `evidence/balance-v11/reference-gate.json`.

The frozen training protocol is `configs/balanced-v11-training.json`. It records
19 controller/model hashes and calibration-based smoothness thresholds before
training. The new workflow first repeats the complete reference on Modal.
Only then does it open training scenarios, run physical counterfactuals, resume
LoRA optimizer state, and save updates 0/4/8/16/32. Checkpoint selection uses only
development results; final held-out scenarios stay closed until selection.

Original failed experiments remain available. A stricter joint-speed capture
gate timed out. Holding the native policy at a measured support phase allowed
settling, but leaving it active during manipulation caused drift. The selected
engineering method settles with phase-frozen feedback, then captures a static
stance. Dynamic task outcomes, not render-space adjustments, verify the result.


## Decision and memory interfaces

The trained model chooses one walking strategy per task leg, one contact
profile per task and one active-arm recovery per task. Walking strategies
change climb, descent and flat-ground command speeds. A fixed route planner
and the frozen feedback controllers execute those choices. This is categorical
controller selection, not neural torque-policy learning or vision-based control.
A complete sequence requires twelve model decisions; inference pauses physics.

The numerical data retains all failed counterfactual branches. Branches are
independent copies of a real state, including MuJoCo warm starts and the fixed
gait's action/filter/phase state. A regression test requires the next physical
steps to agree exactly. Those branches generate labels; they are never spliced
into the continuous displayed episode.

past.dev recall must return the expected source ID before an agent can use the
associated canonical numerical payload. Failed provenance checks stop the run.
The canonical payload is retained locally to avoid treating a memory summary as
an exact numerical record. This design is not a demonstrated memory advantage.

Early local development hashes were captured at completion, and some failed
probes overlapped source edits. They are retained as development evidence, not
immutable checkpoint comparisons. The successful reference was reproduced after
refactoring, and cloud training/evaluation pins a Git commit and nineteen file
hashes. The aggregate progress field covers the final segment; use verified
station arrivals to assess the complete route.
