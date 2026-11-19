# Furnished-desk continuation: rejected reference, no new training

The requested smooth four-task sequence on new scenarios **has not been
achieved**. This continuation reached the 64-attempt local calibration limit.
An independent contact audit invalidated the apparent complete reference;
four subsequent stricter Modal tests all failed. The Tinker campaign was
cancelled before any optimizer update. The V8 model, checkpoints and default
demo remain unchanged.

[Recorded attempts](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/balanced.html)
· [Execution index](../evidence/balance-v11/execution-index.json)
· [Strict test receipts](../evidence/balance-v11/clearance-results.json)

## What the audit changed

Three local recordings and one remote preflight completed the task-state
checks. The original walking check covered terrain, books and desk props but
missed task fixtures. The read-only contact observer found the wrist, knee
and hip hitting the clock during ascent and departure. The knee/clock peak
was 5.20 N. These contacts invalidate the reference even though the four
objects reached their target states.

The original recordings, their numerical flags and the old reference-gate
record are retained. [The new verdict](../evidence/balance-v11/reference-audit.json)
supersedes that gate. The viewer marks the full recording as rejected and
provides a jump to the first clock contact at 3.40 seconds. Nothing is cut
from the attempt or stabilized in render space.

The corrected runtime check permits loaded foot support on the desk/books.
During task approach, contact, hold and release it permits the active hand
on that task's target surface. Other robot/fixture contacts above 0.05 N stop
the sequence. Regression tests use real MuJoCo contacts, including intentional
support, invalid hand/book support, clock support and active-hand permissions.
The archived V8 verifier is untouched.

## Four strict correction tests

All four used the same furnished scene and engineering seed 31000. After two
lower-speed attempts failed before ascent, the next two removed measured
velocity feedback. All stopped before verified book-top arrival.

| Change | Physical end time | Failure |
|---|---:|---|
| Nominal speed 0.045 m/s | 4.194 s | Hip/clock, 6.91 N |
| Nominal speed 0.050 m/s | 3.677 s | Torso/clock, 32.62 N |
| 0.050 m/s, velocity feedback removed | 4.561 s | Fall |
| 0.055 m/s, velocity feedback removed | 3.551 s | Knee/clock, 7.96 N |

The proposed warm-resume variant was conditional on a successful ascent;
that condition did not occur, so warm resume was not physically tested.
Its state-copy behavior is unit checked, which is a different claim.

[Measurement analysis](../evidence/balance-v11/dynamics-diagnosis.json)
shows that the reference's path-forward COM velocity reached 0.592 m/s at
3.168 seconds, before the first clock contact. Its nominal route speed was
0.055 m/s; this differs from the feedback-filtered gait command. Recorded
foot loading also shows samples without loaded support. The lower-speed
trial reached 0.543 m/s before contact. These observations establish loss of
control; they do not isolate every cause of the instability.

The external model's published configuration is for flat-ground velocity
tracking. Its weights are fixed. A controller-selector update cannot create
a safe primitive when the available primitives fail this physical gate.
Lower sway during a failed or stalled run is not reported as improvement.

## Actual training and service use

[Run 44447254287](https://github.com/howdymary/mochi-demo/actions/runs/44447254287)
was cancelled while collecting physical counterfactual labels. No completed
teacher batch, training log or checkpoint list was produced. The code creates
the Tinker training client only after that batch and its memory checks.
[Cancellation evidence](../evidence/balance-v11/cancellation.json) records
zero new optimizer updates and no new checkpoints. Existing V8 training is
reported separately.

| Service | Evidence in this continuation |
|---|---|
| Modal | Seven completed receipt-backed rollouts: two research probes, the invalidated remote preflight, four strict correction trials |
| Tinker | Two research inference decisions; zero new optimizer updates and zero promoted checkpoints |
| Exa | Two actual searches in the research/training preparation loop |
| past.dev | Initial handoffs plus a completed correction that supersedes the rejected reference; exact records below |
| Blender | Measured supported-reach development frames rendered with full-body framing; these do not certify a valid complete run |

## past.dev challenge

- **Agents:** researcher, designer, experimenter and critic have distinct
  identities. The correction reused the actual run's existing audiences.
- **Layers:** working prompts, shared sourced memory, versioned procedures,
  exact numerical artifacts and trajectories remain separate.
- **Results:** the corrected run has four writing identities, four reading
  identities and five source-verified cross-role handoffs. The experimenter
  wrote the contact audit; the critic recalled it and rejected the earlier
  conclusion; the researcher recalled that rejection to gate the strict
  tests. A synthetic private critic canary was denied to the designer.
- **Caveats:** this is demonstrated provenance and access isolation, not a
  measured memory benefit. The initial separate two-probe run's five handoffs
  are not added to the corrected run's five. Logical calls, ingestion polls
  and billed credits are distinct.

[Audit-memory receipts](../evidence/balance-v11/audit-memory.json)
· [Correction execution](https://github.com/howdymary/mochi-demo/actions/runs/44451766703)
· [Strict test execution](https://github.com/howdymary/mochi-demo/actions/runs/44451979972)

## Budget and remaining work

Local calibration: **64/64 attempts reserved**. Remote ledger: **155/256
rollout slots used or reserved**, not 155 completed rollouts. Seven completed
receipts are available; the cancelled teacher batch's 148-slot upper
reservation is conservatively retained. Actual partial work in that batch
has not been reconstructed. The CPU ledger holds 1.4566/8 CPU-hours including
that reservation. This is not a billing statement.

The ledger also retains 8,000 inference tokens reserved, two Exa searches,
11 logical past.dev writes and 11 recalls. New optimizer updates and training
token presentations are both zero. All 32 permitted updates remain unspent.
The overall remote ceiling is not exhausted; the four-test corrective stage
is complete and the physical training prerequisite remains unmet. Additional
blind sweeps and selector training have not been launched against this gate.

Training seeds 37000–37003 were opened by the cancelled batch. Development
38000–38002 and held-out 39000–39005 remain unopened. There is no V11
checkpoint comparison or held-out result to report. The original frozen
protocol is preserved as an invalidated historical protocol; a new controller
needs new hashes and recalibrated smoothness thresholds before comparison.

The next experiment should test a terrain-aware controller on the fixed
book geometry, with clock clearance, sole/riser contact, COM speed and foot
loading recorded. Require repeated ascent and descent without fixture
support before reopening the full sequence. A candidate must expose its
observation, action, joint-order and timing contract and demonstrate compatibility
with the miniature G1. A rough-terrain task definition is not proof that
compatible trained weights are available.

One investigated source is [Isaac Lab's pinned G1 terrain configuration](https://github.com/isaac-sim/IsaacLab/blob/841286fddcff61ddf06c99c46750e766a8c133a6/source/isaaclab_tasks/isaaclab_tasks/contrib/g1_terrain/terrain_env_cfg.py).
It uses depth/history and a different 43-joint contract. Its referenced model
has not been downloaded, licensed for reuse or validated in Mochi. It is
an integration candidate, not a working replacement. The current fixed
[flat policy](https://huggingface.co/kramp/unitree-g1-29dof-velocity-mjlab/tree/5f79b5520040d193b3e8471188cc8e54ccd64942)
has pinned hashes and attribution in `assets/robot/g1-v11-policy/`.

## Verification and preservation

Fifteen targeted physics regression tests pass. Node checks exercise replay
controls, identical initial frames, complete failed endings and the separate
V8 replay. They do not test WebGL pixels in a browser. The chart is calculated
from retained measurements without executing another rollout:

```sh
mochi/.venv/bin/python mochi/scripts/diagnose_balanced_motion.py
```

The unfinished trainer and checkpoint-export tooling are source code only.
They are not exposed as a completed trained demo. All new project files stay
inside `mochi/` except additive Mochi workflows. Publication uses an alternate
Git index and the separate `mochi-desk-v3` branch, preserving the active
checkout and forecasting default branch. No checkpoints were deleted and no
billing settings were changed.
