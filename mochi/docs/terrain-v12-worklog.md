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
updates. Its remote research workflow is prepared but has not been launched.

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
It still has not completed verified ascent/descent.

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
point transforms were preventing toe-edge rotation. That diagnostic is running.

Earlier QP variants stayed upright with torso roll below one degree but stalled
while seating the next sole. Stalled low-motion runs are not successful walking.
The best joint-inverse attempt reached 17 of 18 planned steps, then fell before
centering; this is not a verified book-top arrival. No new held-out scenario is
open and no checkpoint comparison has begun.

## Files and execution

Main modules: `world.py`, `contact.py`, `qp.py`, `probe.py`, `budget.py`.
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
