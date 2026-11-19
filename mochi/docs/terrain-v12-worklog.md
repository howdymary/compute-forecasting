# Terrain V12 continuation (in progress)

The active user request is to repair unassisted book ascent/descent, then resume
actual Tinker post-training and show fresh-checkpoint improvement in one
alarm/drawer/laptop/globe episode. Do not treat the unfinished controller as a
trained improvement. The V8 demo and the rejected V11 evidence are preserved.

## Bounds

New continuation: 96 local diagnostic rollout slots, 512 Modal rollout slots,
8 Modal CPU-hours, 64 Tinker optimizer updates, 2M training-token presentations,
200K inference tokens, 8 Exa searches and 20/40 logical past.dev writes/recalls.
Hard local reservations live in `artifacts/terrain-v12/ledger.json`. V11's old
counters are separate and have not been reset. V12 has zero completed optimizer
updates. The first remote research run completed an Exa search, a Tinker inference decision and initial source-verified memory handoffs, then failed on a missing cloud osqp dependency before returning a physics receipt. Its budget reservations are retained. A second attempt failed in its zero-rollout runtime check because it resolved the source mount against the wrong root. The dependency and mount checks are now corrected; both failures retain their reservations.

## Controller development

Pure clearance residuals around the fixed flat-ground policy hit the first
riser or stalled. Explicit Cartesian replacements destabilized flat walking.
Those failures are retained. Supported-stance PD stepping also fell in the
first transfer. The current direction uses reachable support-pose optimization,
MuJoCo contact inverse dynamics and a new constrained whole-body QP.

The old joint-acceleration inverse solver completed flat steps, but lost balance
when transferring onto a higher book. Reducing stance width from 40 to 28/24 mm
improved detached support-pose feasibility and progressed farther physically.
This is a tested geometric/control change, not cosmetic narrowing or training.
Several subsequent runs completed verified ascent and standing dwell without clock contact on the same engineering seed. A staged backward swing now keeps the foot high until it clears the riser. Two isolated descent branches from an actual supported ascent completed on the engineering seed (24 mm and 20 mm stance widths). Neither branch is a full four-task reference or a trained improvement.

Other tested changes: wait for actual loaded support before liftoff; distinguish
light touchdown from full-sole support; seat reference soles on the terrain
plane; raise the pelvis only after the lower foot unloads; use a forward swing
arc; compensate changing leg COM; include actual arm servo effort via a Schur
complement instead of prescribing old arm accelerations; centre both supports
before final stance capture. All motion remains actuator-driven.

## Current QP

`src/mochi/terrain_v12/qp.py` eliminates the arm dynamics, constrains floating-base
force balance, contact-point forces, friction and actuator torque, and tracks
COM, torso orientation, swing feet and posture. Redundant contact Jacobian rows
are removed with pivoted QR. Contact forces are predictions, never externally
applied forces. The most recent change keeps loaded material points stationary
while leaving flat-foot alignment to a separate objective; hard desired flat-foot
point transforms were preventing toe-edge rotation. That diagnostic remained stalled and is not the selected controller.

Earlier QP variants stayed upright with torso roll below one degree but stalled
while seating the next sole. Stalled low-motion runs are not successful walking.
Ankle feedback gains 0.5 and 1.0 completed ascent and standing dwell. A bounded
backward IK solver prevented an observed hip-reference flip and passed the first
downward transition, but the following drop initially failed. The later staged-swing and short-placement branches passed descent. These are repeated
engineering trials on one geometry seed, not a fresh-scenario result. No new held-out scenario is
open and no checkpoint comparison has begun.

## Files and execution

Main modules: `world.py`, `contact.py`, `probe.py`, `sequence.py`, `tasks.py`, `development.py`, `budget.py`. `qp.py` retains the unpromoted whole-body experiment.
`walker.py` and `quasi.py` retain rejected development alternatives.
`probe.py` records complete attempts and automatically tries backward descent
only after measured book-top support and dwell. It never resets between ascent
and descent. Immutable source snapshots are retained for newer probes; older
local source hashes without snapshots are development evidence only.

Two contact-area regression tests pass: a loaded four-corner patch has area;
a loaded two-point toe edge does not. Combined with targeted V11 tests, seven
checks pass. Broader archived physics tests were passed before V12; they need
appropriate rerunning after selecting the implementation, not on every edit.

`research.py`, `remote.py` and additive `mochi-terrain-v12.yml` prepare actual Exa,
past.dev and Modal diagnostics with one explicitly labelled Tinker inference
decision. They do not contain optimizer updates. Training remains gated off.
Do not infer sponsor usage from prepared source code. Use a separate fixed
protocol once a repeated, valid full four-task reference exists.

No sub-agents, checkpoint deletions, billing changes, forecasting mutations or
branch checkout/reset are authorized by this continuation. Publish only scoped
Mochi changes with the alternate-index publisher; preserve the active unborn
`metagame` checkout and remote default `compute-observatory`.

The clock approach is being repaired separately: the original hand path contacted the case; the collision-aware two-stage path avoided that contact but did not yet depress the switch. A closer station is being tested through actual footsteps. Training remains gated.

## Physical reference gate passed

Two uninterrupted local engineering episodes passed all four tasks and recoveries without a fall, forbidden contact or applied base force: seed 41000 in 249.81 s; seed 41001 in 251.46 s. The second uses the final learning interface and bounded contact seek. Initial-state and terrain-friction variations are defined for the training/development/held-out partitions; those held-out scenarios remain unopened.

The V12 controller is now frozen for a bounded 64-update Tinker campaign. A remote complete reference must pass again before gradients. Actual post-training has not started at this edit. The first optimizer step will be checked using fresh checkpoint decision distributions before continuing. All six domains receive real forward/backward calls. The native ONNX gait weights and deterministic contact controller remain fixed.

Eighteen targeted physics, detached-state, contact and archive checks pass. The new TerrainWorld branch test verifies exact next-step positions/velocities and identical friction against the source, rather than merely comparing two re-created clones.

## Remote reference and visual verification

The active run 44472186998 passed its complete remote feasibility reference and entered physical teacher-branch collection. Its initial three past.dev cross-role handoffs completed and its Exa-informed allocation was recalled before data collection. At this milestone, zero new optimizer updates had completed; numerical live status remains authoritative. A separate training-partition probe verified the W2 narrow walking action on seed 42000.

The preceding cloud diagnostic completed both matched traversals. Both the longer and shorter placement plans passed with the repaired swing; no meaningful advantage from shorter placements is established. Its result-ingestion handoff exceeded five minutes and remained incomplete. The new memory adapter journals pending ingestion IDs, preserves source provenance and forbids dependent reads before readiness.

Cancelled training launch attempts retained their uncompleted resource reservations. They contributed no optimizer updates. Later physical receipts are persisted individually and separated from those reservations. New evaluation models run independently on identical frozen images and paired initial scenarios, rather than serializing three full episodes under one function deadline.

The complete engineering replay is published at `/terrain.html`; its files were verified against deployed bytes. Headless Chrome rendered the actual WebGL scene and the resulting screenshot was inspected. The default V8 page and rejected V11 page remain available.

## Preserved-data post-training continuation

Run 44472186998 completed its remote reference and all four teacher sequences: 149 completed physical rollouts including counterfactual branches. It produced 48 decision labels. Sixteen walking labels include W0 and W2; the sixteen recovery labels select safe direct withdrawal. No new optimizer updates were completed or reserved when that run was stopped. Its artifacts and conservative resource reservations remain preserved.

Run 44482272455 reuses those exact data and restores the canonical parent with optimizer state. Its frozen budget allows 32 new updates, with checkpoints at 0, 1, 8 and 32. It trains all six domains before performing physical development evaluation. Each model receives the same 1500-second function deadline and token allowance; the scene, controller, scenario partition and success verifier are unchanged. This ordering avoids blocking gradients behind slow replay evaluations. The larger inference allowance is precautionary, not evidence of a confirmed earlier token-limit failure.

The public status endpoint now shows the active continuation's budget separately from original campaign reservations. Training progress and measured checkpoint evaluations, rather than this launch description, establish what has completed.

## Real training completed; evaluator import repaired

Run 44482272455 completed 32 optimizer updates with six forward/backward domains per update and 383,343 training-token presentations. Durable states exist at updates 0, 1, 8 and 32. The first-step distribution probe changed every domain. Held-out scenarios remained unopened.

The first remote development evaluation stopped before producing an outcome because `evaluation_remote.py` omitted its `json` import. The import is now repaired and checked with undefined-name linting. The evaluation-only continuation allows precisely that source-hash change, verifies every other frozen file, and contains no optimizer, state-save or deletion calls. It also corrects bookkeeping for checkpoints that existed before their development measurements. Prior uncompleted compute reservations remain archived.

## First measured checkpoint gain

The parent completed 2/3 development sequences with 2/3 within frozen smoothness limits. The one-update checkpoint completed 3/3 with 3/3 within limits. All six traversals passed the clock, book ascent/descent and drawer. The parent failure on seed 43002 was a left-hip contact with the laptop lid during release (0.487 N), not a clock collision. These are development results; the other checkpoints and final test remain pending.

A read-only collector exports the completed immutable archives without simulations or model calls. The development preview contains all three scenarios, both complete trajectories, actual checkpoint IDs and explicit pending-final-test labels. It is not a frozen final checkpoint selection.

The development preview deployment (run 44491880665, source d0b3ae8) passed its actual-release checks. HTML, JavaScript, manifest and a compressed recording matched deployed bytes. Headless Chrome rendered the paired 3D scenes for scenario 43002 at physical time 234.4 s, showing the retained laptop failure and the trained model continuing toward the globe. The image was inspected; final testing remains pending.

The eight-update checkpoint also completed 3/3 development sequences within the frozen smoothness limits: mean 250.24 simulated seconds and torso-roll RMS 0.274 degrees. The one-update checkpoint averaged 255.02 s and 0.263 degrees. The eight-update version is faster but has slightly greater measured torso roll; neither is claimed to dominate on every measure. The 32-update evaluation and final testing remain pending.

After this evaluation ends, the requested next step is to assess walking, task contact and recovery, write an evidence-grounded next-training prompt and execute it. The next campaign must use a new identity and fresh final-test scenarios.
