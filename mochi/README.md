# MOCHI: Walking, Contact and Recovery Policy Learning

## Current work: feasible contact actions and post-training

[Execution prompt](docs/smooth-v17-prompt.md) · [Controller evidence](evidence/smooth-v17/engineering.json) · [Resource reconciliation](evidence/smooth-v17/carried-budget.json) · [Existing route preview](https://howdymary--mochi-smooth-v16-engineering-web.us-east.modal.run/)

The revised fixed reference completed the uninterrupted clock, book turnaround, forward descent, drawer, loaded Post-it crossing, laptop and globe sequence in 339.60 physical seconds and 470 steps. It passed the unchanged quality checks with no fall or forbidden contact. This is a controller-engineering result. New Tinker results remain pending.

Two actions address measured limitations. H0 adds a joint-rest prior to clock inverse kinematics; a matched development case reduced R4 recovery travel from 9.06 to 3.62 rad. P4 uses steady 0.60 N laptop control with a 16-second action horizon; it closed the hard development case in 12.72 seconds with 0.619 N peak contact force. The global force limit stays 0.8 N. Every model checkpoint and baseline receives the same extended library. Native gait weights remain fixed.

Execution [44669222147](https://github.com/howdymary/mochi-demo/actions/runs/44669222147) timed out in collection. Execution [44686221838](https://github.com/howdymary/mochi-demo/actions/runs/44686221838) preserved its physical states but stopped when none of the original laptop actions succeeded on one training approach. Both completed zero optimizer updates. Their failures and checkpoints remain archived.

The repair continues against the budget opened by the second execution, with an audited starting debit of 73 attempts and 3.835 accounted CPU-hours. This includes conservative bounds for two interrupted calls and old supervisors. It does not reset previous usage. The limits remain 224 attempts, 18 accounted CPU-hours, 16 optimizer updates and four physics workers. The old route viewers and forecasting application are preserved.

Training will use historical parent-prefix states plus newly measured clock, laptop and recovery alternatives. Final displayed evaluations will be uninterrupted rollouts from reset. The study will distinguish manually engineered capability from improvements caused by trained choices, and compare against fixed and training-derived static controls.

## Completed V15 walking and task-control study

[Uninterrupted checkpoint comparison](https://howdymary--mochi-efficient-v15-demo-web.us-east.modal.run/) · [Fresh test scenario](https://howdymary--mochi-efficient-v15-demo-web.us-east.modal.run/?scenario=held-out-93000) · [Technical blog](https://howdymary.github.io/mochi/) · [Assessment](docs/efficient-v15-assessment.md) · [Numerical assessment](docs/efficient-v15-assessment.json)

Tinker completed **16 new optimizer updates and 96 domain-gradient calculations** for the shared Qwen3.5-4B LoRA decision model. Every update included walking, clock, drawer, laptop, globe and arm-recovery examples. Checkpoints 0, 1, 4, 8 and 16 were evaluated on all three development scenarios. The frozen rule selected update 16 before opening four fresh final-test scenarios.

Update 0 restores a previously trained checkpoint with 105 cumulative updates. The selected checkpoint has 121 cumulative updates. The native ONNX gait, physical controllers, scene, route, step detector and success criteria stayed fixed throughout this comparison. Tinker trained controller selection, including walking commands and task/recovery profiles.

| Final-test policy | Complete within quality limits | Mean step attempts | Physical seconds |
|---|---:|---:|---:|
| Parent | 4/4 | 806.0 | 266.4 |
| Selected update 16 | 4/4 | 476.5 | 219.5 |
| Fixed controller | 4/4 | 809.5 | 264.9 |
| Training-derived static | 4/4 | 482.0 | 219.1 |

The declared 20% step-reduction target was met on this cohort. Across the four matched successful pairs, the selected model used **40.9% fewer steps** and **17.6% less simulated time** than the parent. No policy fell or made a forbidden contact in these final tests. Completion rates were equal at 4/4.

The paired bootstrap intervals are 39.4% to 41.8% for steps and 15.7% to 18.7% for time. They describe four fixed-layout cases. A 4/4 completion result has an approximately 51% to 100% Wilson interval at 95% confidence. This is a small simulation study without hardware validation.

### Static control and motion tradeoffs

The training-derived static policy was close: 482.0 steps and 219.1 seconds, compared with 476.5 steps and 219.5 seconds for the selected model. Their choices matched in 46/48 corresponding decisions. The two differences were laptop profiles on seeds 93000 and 93003. No meaningful adaptive-policy advantage was established. Small cost differences under identical choice vectors remain unexplained.

Average total arm-joint travel per successful recovery increased from 5.54 to 6.93 radians. Mean torso roll RMS increased slightly, from 0.271 to 0.279 degrees. Both remained within the declared limits. Fewer footsteps did not establish lower arm travel or smoother motion in every measure.

### Development checkpoint progression

| New updates | Qualified development completions | Mean steps | Physical seconds |
|---|---:|---:|---:|
| 0 | 3/3 | 805.3 | 265.5 |
| 1 | 3/3 | 583.3 | 237.9 |
| 4 | 3/3 | 494.7 | 219.0 |
| 8 | 3/3 | 488.0 | 218.2 |
| 16 | 3/3 | 485.3 | 218.1 |

The viewer retains all five versions on all three development scenarios, plus every parent/selected final-test pair. Each pane is one uninterrupted clock, drawer, laptop and globe episode with identical initial conditions and playback speed. Body motion and object outcomes come from recorded MuJoCo physics.

### Component checks

The first qualified fixed reference route supplied twelve supported physical states. Both models were tested from each state, producing **24 diagnostic branches**. All branches passed the frozen branch validity checks. These branches are separate from the continuous four-task tests.

Across the four walking branches, measured attempts fell from 808 to 472 and total physical time fell from 229.04 to 184.86 seconds. The laptop approach used 324 versus 172 steps from the same state. Task-plus-fixed-withdrawal time summed to 35.81 versus 32.51 seconds. Recovery time summed to 6.65 versus 5.30 seconds, while summed arm-joint travel increased from 22.15 to 26.77 radians. These totals combine separate branches, not one route.

### Execution and sponsor integrations

- Tinker: 16 completed optimizer updates, 96 gradient calculations, 217,812 training-token presentations and retained parent/intermediate states. Training examples include reuse of 48 measured observation records.
- Modal: 204 physical rollouts and 10.341 function CPU-hours, within the 224-rollout, 18-hour and four-worker limits. This reports function execution at the declared CPU allocation, not an invoice.
- Exa: one search in the research loop, selected from measured turning and alignment failures. Source URLs and provenance remain in the public report.
- past.dev: six writes and seven logical recalls, including one cross-run recall. The completed handoff includes results, critic review, a qualified conclusion and a subsequent research recall.

The 204 physical rollouts comprise one preflight, 148 data-generation branches/continuations, fifteen development episodes, sixteen final episodes and twenty-four component branches. No extra gradients or physical rollouts were needed for publication.

### past.dev challenge

**Agents:** research, design, execution and review use distinct service identities with explicit shared and private audiences.

**Layers:** prompts contain working context; past.dev stores observations, sourced hypotheses and qualified conclusions; code contains procedures; artifact storage contains exact numerical records and trajectories.

**Results:** four writing identities, four verified reading identities and five source-verified cross-role handoffs within V15. A separate cross-run recall retrieved the earlier assessment. The private-canary denial test passed, with no pending ingestions.

**Caveats:** canonical journal payloads are used after verifying returned source IDs. The study did not isolate a causal benefit from memory or search. API activity is distinct from billed credits.

### Replay and audit

Run from the repository root after the environment and visual-asset setup below. Downloading the public artifact reuses archived trajectories:

```sh
gh run download 44625135986 --repo howdymary/mochi-demo --name mochi-efficient-v15-public-44625135986 --dir mochi/web/desk/efficient-v15
python3 -m http.server 4118 --directory mochi/web/desk
```

Open `http://127.0.0.1:4118/efficient-trained.html`. To audit the retained numerical evidence:

```sh
gh run download 44625135986 --repo howdymary/mochi-demo --name mochi-efficient-v15-training-44625135986 --dir mochi/.cache/v15-completed
node mochi/scripts/check_efficient_evidence.mjs
node mochi/scripts/check_efficient_v15_ui.mjs
mochi/.venv/bin/python mochi/scripts/assess_efficient_v15.py --source mochi/.cache/v15-completed
```

[Frozen methods](docs/efficient-v15.md) · [Execution and artifacts](https://github.com/howdymary/mochi-demo/actions/runs/44625135986) · [past.dev and Tinker article draft](docs/past-dev-blog-draft.md)

Policy reruns require access to the retained Tinker states and backend credentials. Replays load the archived trajectories. Forecasting code, deployments, old checkpoints and earlier studies remain preserved.

## Completed terrain study (V12) and navigation refinement (V14)

[Turning and forward-walking comparison](https://howdymary--mochi-directional-v14-demo-web.us-east.modal.run/?case=desk-corner) · [Navigation changes and evidence](docs/directional-v14.md)

The directional navigator turns toward the next corridor, walks forward, then aligns for the task. Its replay uses actual MuJoCo body orientations. This controller refinement is evaluated separately from the frozen Tinker checkpoint study below; it adds no model-training updates.

The furnished-desk controller now completes the continuous **clock → drawer → laptop close → globe** sequence, including book ascent and descent, without hitting the clock. Two local engineering references and the subsequent remote reference passed the strict checks.

[V12 checkpoint comparison](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/terrain-trained.html) · [Recorded repaired route](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/terrain.html) · [V12 methods](docs/terrain-v12.md) · [V12 execution status](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/api/terrain-training)

Those passes establish physical feasibility. V12 completed **32 new optimizer updates and 192 domain-gradient calls** using the recorded physical comparisons, with durable checkpoints at 0, 1, 8 and 32. The first matched development comparison passed 2/3 complete smooth sequences with the parent and 3/3 after one update. The eight- and 32-update checkpoints also passed 3/3. The frozen rule selected update 1 for its lower torso roll among successful checkpoints. On six final-test scenarios, the parent completed 3/6, selected checkpoint 6/6 and fixed controller 5/6. These are small simulated cohorts; component checks did not establish learned manipulation or recovery improvement in V12. [Completed assessment](docs/terrain-v12-assessment.md). The native gait network remains fixed. Earlier V8 training and rejected V11 evidence below are preserved.

<!-- MOCHI_CURRICULUM_START -->
## Archived V8: learning walking, task and arm-recovery decisions

[Interactive before/after demo](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/) · [V8 methods](docs/control-v8-study.md) · [Numerical evidence](evidence/control-v8/results.json) · [Training execution](https://github.com/howdymary/mochi-demo/actions/runs/44382265039) · [Archived V7 viewer](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/?study=v7)

A 22.1 cm Unitree G1 walks around one desk, silences an alarm, closes a drawer and laptop, then aligns a globe. Each displayed checkpoint is a separate uninterrupted MuJoCo episode. The interface replays the recorded robot and object transforms, with synchronized before/after views and actual model decisions. Select development scenario 24001 and “Play all checkpoints” to inspect the full sequence from update 8 onward; scenario 24000 retains the laptop failure, and the development cohort remains 1/2.

Tinker completed **64 additional optimizer updates and 384 domain-gradient calls**, resuming the retained V7 update-96 state. Every update trains walking commands, all four task-profile choices and active-arm recovery. The Qwen3.5-4B LoRA selector reads simulation state. The native gait network, standing balance, arm IK and physical motion primitives remain fixed. This is command/profile learning, not learning motor torques or gait-network weights.

Development selection chose **8 additional updates**. Counts describe the whole training campaign; the selected checkpoint may precede update 64. The latest checkpoint is not automatically the selected one. Checkpoints 0/8/16/32/64, including regressions, are retained and shown.

| Four matched held-out scenarios | Parent weights, V8 setup | Selected V8 weights | Fixed controller |
|---|---:|---:|---:|
| Complete four-task sequences | 0/4 | 4/4 | 4/4 |
| Walking stations reached | 0/16 | 16/16 | 16/16 |
| Falls | 0 | 0 | 0 |
| Valid arm recoveries / attempts | 0/0 | 16/16 | 16/16 |

Four scenarios and one training run are a small simulation pilot. Walking failures can prevent later tasks from being attempted. Task success, recovery success and full-sequence success are distinct checks. Raw paired outcomes and uncertainty are in the evidence. The original V7 stack is evaluated separately; its engineering differences are not attributed to weight training.


Separate task and recovery probes use the same held-out seed block after checkpoint selection. Recovery choices start from shared post-task states, so walking failure cannot hide them. starting model: 12/16 valid recoveries. post trained model: 16/16 valid recoveries. Across 12 shared states where both recoveries passed, mean hand travel was 9.3 cm before and 9.3 cm after. These isolated resets are not part of the continuous demo. [Probe evidence](evidence/control-v8/isolated-controls.json).

### What was fixed before training

The old laptop press could not sustain enough closing torque. The new controller contacts the upper lid edge from a front-right stance, applies bounded actuator force, then withdraws while gravity finishes closing. The hinge, object properties and success criteria remain unchanged.

A universal parking detour caused unnecessary arm travel. The revised options include direct folding where safe and outward shoulder clearance before lowering beside the alarm. These are engineered primitives. Tinker learns which commands and primitives to choose; their implementation is frozen across the weight comparison. Recovery checks include stable joints, low speed, no fall and no fixture-contact steps above 0.01 N.

The recovery primitives were checked on training-only branches before learning. Across 22 shared states where both choices passed, the parking-detour option averaged 19.6 cm of hand travel; the chosen safe labels averaged 9.3 cm. This measures the engineered alternatives, not a held-out gain from trained weights. [Design audit](evidence/control-v8/recovery-design-audit.json).

### Services used

- **Tinker:** real supervised post-training, completed forward/backward and optimizer calls, durable intermediate states, and fixed-checkpoint inference in closed-loop simulation. No extra optimizer updates are credited to evaluation-only probes.
- **Modal:** 335 physical rollouts across the training/evaluation evidence, bounded at four CPU workers per function. The before/selected/fixed comparisons share one worker per scenario. Small MuJoCo experiments run on CPUs.
- **Exa:** 2 searches inside the research/training loop. Retrieved evidence informs bounded proposals; it is not executed as code.
- **past.dev:** 11 writes, 11 recall requests and 10 source-verified cross-role handoffs. Recalled proposals select between predeclared training allocations. Credit charges are not available from these API receipts.

### past.dev challenge

**Agents:** research, policy design, experiment execution and criticism use separate identities and explicit audiences.

**Layers:** prompts hold working context; past.dev stores sourced findings, outcomes and qualified conclusions; versioned code stores procedures; Mochi artifacts store numerical measurements and trajectories.

**Results:** 4 writing identities, 4 verified reading identities and 10 cross-role recalls. Private critic audience isolation passed.

**Caveats:** canonical payloads are resolved only after verifying returned source IDs. No causal memory or search ablation is claimed. Training examples include repetitions, not new market or physical observations at each update.

### Inspect and run

Run from the repository root. Provider credentials stay on the backend, using the repository's existing GitHub Actions secrets.

```sh
PYTHONPATH=mochi/src python -m pytest mochi/tests/test_control_v8.py -q
node mochi/scripts/check_replay_ui.mjs
python3 -m http.server 4028 --directory mochi/web/desk
PYTHONPATH=mochi/src python -m mochi.control_v8.train
```

The training command starts a new research run and requires access to the retained parent checkpoint. Canonical trained states remain in the owner's Tinker account; public receipts identify them by hash. Archived trajectories can be replayed without service credentials. The numerical evidence and execution artifacts support inspection; trained state access is required for an exact policy rerun.

No checkpoint deletion or billing-plan changes are part of this training study. Forecasting code, deployments and archived results remain separate. The older V6/V7 studies and their failures remain in their original evidence directories.

Integration paths: [training](src/mochi/control_v8/train.py), [Modal execution](src/mochi/control_v8/remote.py), [physical controls](src/mochi/control_v8/manipulation.py), [recovery](src/mochi/control_v8/recovery.py), [memory](src/mochi/desk/services.py), [search](src/mochi/integrations.py).
<!-- MOCHI_CURRICULUM_END -->

## Fresh environment and rendering

Reuse `mochi/.venv` when available. For a new environment, run from the repository root:

```sh
uv venv --python 3.11 mochi/.venv
uv pip install --python mochi/.venv/bin/python torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python mochi/.venv/bin/python -e './mochi[remote,dev,plots]' pyyaml==6.0.2
mochi/.venv/bin/python mochi/scripts/fetch_visual_models.py
```

See [the integration inventory](docs/integrations.md) for local versus remote credentials. The additive Mochi workflows inject existing backend secret references. The local replay server requires no provider credentials.

```sh
blender -b -t 4 -P mochi/scripts/render_curriculum.py -- \
  --input mochi/web/desk/curriculum/v8-held-out-25000-after.json \
  --out mochi/artifacts/inspection --time 53.394657 --samples 32 --camera follow
```

The source-study render uses actual selected-checkpoint motion. Use `--camera side` or `feet` to inspect gait, or `--animate` to save the recorded animation in a Blender scene. Large generated outputs and caches stay out of Git.

## Provenance and limits

This is a fixed-layout, state-observation simulation study. Waist and fingers are fixed. There is no camera input or hardware validation. Remote model inference pauses simulation time; displayed completion times exclude those waits. Sampled clearance checks do not certify continuous collision freedom.

The original supported puck slice is in [the initial archive](docs/archive/initial-puck-slice.md). The preceding navigation/planning README is [preserved separately](docs/archive/planning-v1-readme.md). Later walking, task and recovery training is not all claimed as work built during the original hackathon.

Dependencies include MuJoCo, NumPy, SciPy, PyTorch, Three.js, Blender, FastAPI and the provider SDKs. Robot hashes and licenses are recorded in [G1 provenance](assets/robot/g1/source.json) and [locomotion provenance](assets/robot/locomotion/source.json). [Scene attribution](web/desk/assets/sand3d-attribution.json) records visual assets. Forecasting code, deployments and archived results remain separate.

## Furnished-desk continuation (V11)

[Balance experiments](https://howdymary--mochi-curriculum-demo-web.us-east.modal.run/balanced.html)
retain complete attempts, failed endings and contact faults. The legacy task
counter passed three runs, but the robot hit the clock during walking. An
independent audit invalidated that reference and the pending Tinker campaign
was cancelled before gradients. Four subsequent strict Modal tests all failed.

The local 64-attempt calibration cap is reached. The remote ledger holds 155
used-or-reserved rollout slots, including a conservative 148-slot reservation
for the cancelled batch; seven completed receipts are available. No V11
trained checkpoint or fresh held-out improvement is claimed. The current
need is a terrain-capable controller that can climb without fixture support.

[Results and exact receipts](docs/balanced-v11-results.md) ·
[Methods and inspection commands](docs/balanced-v11.md) ·
[Contact audit](evidence/balance-v11/reference-audit.json).
