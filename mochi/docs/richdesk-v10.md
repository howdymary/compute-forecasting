# Furnished-desk route and training study

The new scene is separate from the validated V8 study. V8 trained command,
contact-profile and recovery selection. Its native gait weights remain fixed.
No V10 optimizer update has been run.

## First deliverable

The authoritative scene is `configs/richdesk-v9.json`. MuJoCo, Blender and the
interactive viewer use its object placements, including the printer, its tray,
the three 8 mm books and the relocated globe. The books are fixed nonsliding
terrain. Prop collisions use conservative envelopes rather than detailed GLB
triangles. All lengths use metres.

`artifacts/richdesk-v10/route-plan.png` is the annotated overhead study.
`route-plan.json` retains all candidates, rejected collision samples, station
headings, terrain foot placements and geometry-check scope.

The direct route crosses the open drawer and laptop. The revised front
corridor avoids the sticky notes, uses the front of the laptop, and backs away
before turning so that the robot does not sweep into the printer. A wider
corridor is retained as a comparison. The selection minimizes the stated
nominal motion estimate among these candidates; no global optimum is claimed.

Geometry uses detached MuJoCo copies with robot shells enabled and 2 mm
clearance. Rest-pose sweeps do not validate balance or a complete swing
envelope. Stair transitions require separate foot and physical execution
checks. The proposed sole rectangles must fit entirely on their landing
surface. The drawn route is never assigned to the physical robot root.

## Physical feasibility gate

`richdesk.stepping` is an experimental contact-gated reference controller.
`richdesk.wholebody` adds floating-base inverse dynamics with unilateral
ground forces, friction and centre-of-pressure bounds, joint-acceleration
guards and actual actuator torque limits. MuJoCo determines contact and motion.

Early attempts used the archived 105 mm absolute pelvis cutoff. The later
terrain-v2 verifier allows intentional crouching down to 80 mm of pelvis
clearance, while retaining the 30 degree tilt limit, desk bounds and invalid
non-foot loaded terrain contact checks. Results under these verifier versions
must not be pooled. No trained-checkpoint comparison has been run under either
version of the new terrain study.

Touchdown detection and loaded-foot measurement are distinct: a lightly
touching foot may establish a contact before it carries 0.05 N. Final book-top
success requires both feet to carry the declared load, remain inside the
upper book and satisfy orientation and dwell checks. A planned foot position
or a raised pelvis cannot pass that verifier.

Engineering attempts, including falls and stalled landings, remain in
`artifacts/richdesk-v10/`. They are not checkpoints, training outcomes or
held-out evidence. Training must wait for reliable ascent, descent and a
complete reference task sequence.

## Proposed learning and budget

The intended Tinker model learns step-level walking decisions, task-contact
choices and arm recovery. Inference runs outside the physics loop. The native
Unitree network is not being described as newly trained. Changes to the
classical controller are frozen before comparing model weights.

`configs/richdesk-campaign.json` declares unopened train/development/test
partitions and ceilings: 32 optimizer updates, checkpoints 0/4/8/16/32, 256
Modal rollouts, four workers, eight CPU-hours, two million training-token
presentations, 200,000 inference tokens, eight Exa searches and 20/40 past.dev
writes/recalls. These are workload bounds, not billing estimates. No billing
setting or checkpoint deletion is authorized by this campaign.

Local provider credentials are absent. Existing GitHub Actions secret names
were verified without reading values: `TINKER_API_KEY`, `MODAL_TOKEN_ID`,
`MODAL_TOKEN_SECRET`, `EXA_API_KEY`, `PAST_API_KEY`. Use explicit backend
injection and separate Mochi identities/audiences. No frontend credentials.

Before training, collect actual branch outcomes and reject flat rewards or
conflicting state encodings. Select checkpoints on development only. Open
held-out scenarios once after selection. Compare the parent, fixed heuristic
and all saved checkpoints on identical physical conditions. Isolate walking,
task contact and recovery as well as reporting uninterrupted full sequences.

## Commands from repository root

```sh
uv pip install --python mochi/.venv/bin/python 'osqp==1.1.1'
PYTHONPATH=mochi/src mochi/.venv/bin/python -m mochi.richdesk.plan
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/probe_richdesk.py --id development-native --controller native
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/probe_richdesk.py --id development-qp --stride .022 --crouch .012
```

Official API references checked November 18, 2026:
[Tinker API](https://tinker-docs.thinkingmachines.ai/),
[training calls](https://tinker-docs.thinkingmachines.ai/tinker/sdk-cheatsheet/),
[OSQP Python interface](https://osqp.org/docs/interfaces/python.html).

These references support API use, not a measured robotics improvement.

## Completed sponsor-connected feasibility probe

[Run 44432056165](https://github.com/howdymary/mochi-demo/actions/runs/44432056165)
completed using the original published V10 engineering revision. It executed
one failure-driven Exa search, five verified cross-role past.dev recalls,
one Tinker decision-inference call and two physical Modal rollouts. Four
identities wrote and read memory. Private critic access was configured; a new
isolation canary was not run in this small probe.

The designer recalled a sourced hypothesis and selected `slow_swing`. The
experimenter used that recalled proposal as actual Modal parameters. Both the
native baseline and the candidate fell. Neither reached the upper book.
The critic recalled the measured results and qualified the original hypothesis.
This run completed **zero optimizer updates** and opened no held-out scenario.
It does not show learned improvement, a completed climb or a service ablation.

[Exact service and outcome receipts](../evidence/richdesk-v10/feasibility-services.json).
The public [route drawing](../web/desk/richdesk/route-plan.png) and development
viewer supplement, rather than replace, the numerical records.
