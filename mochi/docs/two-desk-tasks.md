# Laptop screen and desktop globe

The 22.1 cm humanoid performs two separate contact episodes in the same desk
workspace. Its 40/37 mm arm segments and 52/48 mm leg segments match the
proportion study. The pelvis is supported; episode resets place it at the
appropriate station. This does not demonstrate locomotion or balance.

## Run and inspect

[Open the published two-task preview](https://howdymary--mochi-desk-tasks-web.us-east.modal.run/).
The additive Modal app `mochi-desk-tasks` serves only this preview and its
measurement files. It has no provider secrets attached and does not replace
either existing deployment. Deployment: [workflow 44196113940](https://github.com/howdymary/mochi-demo/actions/runs/44196113940).

From the repository root:

```sh
PYTHONPATH=mochi/src mochi/.venv/bin/python -m mochi.desk.tasks --task both --out mochi/web/desk/tasks
PYTHONPATH=mochi/src mochi/.venv/bin/python -m pytest mochi/tests/test_desk_tasks.py -q
python -m http.server 8773 --directory mochi/web/desk --bind 127.0.0.1
```

Open <http://127.0.0.1:8773/tasks.html>. Choose an episode, replay or scrub it,
and switch between its close view and the whole desk. The interface reads
recorded MuJoCo body transforms and measurements. It does not animate a
successful object trajectory independently of the simulator.

## Physical tasks

| Task | Action | Target | Variable conditions |
|---|---|---|---|
| Laptop | Push the screen's upper corner | 90 degrees from the desktop | Starting angle, screen mass, hinge resistance, contact friction |
| Globe | Push tangentially, hold the hand still to brake, then release | Coral marker aligned to the fixed brass pointer | Starting angle, sphere mass, bearing resistance, contact friction |

The arm has three shoulder axes and one elbow axis, position actuators with
force limits, and analytical inverse kinematics. Physics runs at 500 Hz and
control at 50 Hz. Only the arm has actuators. Each task object has one passive
hinge. Joint state is set at reset; contact determines its motion thereafter.

Success requires an angular error of at most 3 degrees and angular speed at
most 0.07 rad/s for 0.4 seconds at the end of a seven-second episode. A hand
pad or palm must contact the object. Forearm and other object contacts
invalidate the attempt. Nonfinite states and excessive globe rotation are
also invalid. An additional MuJoCo data instance exports synchronized body
poses without altering the rollout state.

## Current evidence — 17 November 2026

These are local **development contact checks**, not a trained-model evaluation.
The hand-coded controller uses speed 0.45 rad/s, braking margin 0.025 rad and
contact depth 1.2 mm. Seeds 8000–8007 were used during implementation.

| Task | Development successes | Worst final error | Forearm/other object contacts |
|---|---:|---:|---:|
| Laptop | 8 / 8 | 1.87 degrees | 0 |
| Globe | 8 / 8 | 1.29 degrees | 0 |

The displayed seed is 8000 for both: 1.48 degrees final laptop error and
1.01 degrees globe error. `web/desk/tasks/calibration.json` retains all sixteen
measurements. The two replay JSON files retain body poses, contact flags,
controller settings and the dimensional specification hash.

Initial attempts were rejected because the laptop was moved by the forearm,
or because the globe overshot. A fourth arm DOF permits a collision-free elbow
plane without lengthening the limbs. The globe controller now establishes
contact before advancing its stroke and brakes at the actual hand position,
rather than continuing toward a previously queued target.

## Rendering and assets

The task screen panel, spherical globe, hand pad and limb lengths use the
physical dimensions. Decorative shell panels, display graphics, original
stylized globe cartography, the bracket and pointer, mug and paper are visual
assets. They do not add simulated manipulation capability. The globe map's
north axis is aligned with the physical Z rotation axis. All geometry and
cartography are original procedural assets; Three.js uses the existing
version 0.170.0 import map.

## Training status

No Tinker post-training or new Exa/past.dev/Modal campaign has been run on
these two tasks. The earlier cancelled eraser campaign and earlier published
scores are separate. The existing `desk/train.py` targets the superseded
eraser geometry and must not be described as training these tasks.

Before restarting: define a controller catalog and varied scenarios that make
controller selection informative, freeze the success verifier and separate
training/validation/test splits, then post-train the selector with Tinker.
Compare starting weights, post-trained weights and a train-selected fixed
controller on the same fresh scenarios. Preserve negative results.
