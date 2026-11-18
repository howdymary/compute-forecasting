# Laptop screen and desktop globe

The current preview is the [free-base standing study](free-standing-and-tasks.md). The supported-base results below describe the preceding revision.

The current preview uses a 22.1 cm supported Unitree G1 miniature with native
seven-joint arms. [Open the replay](https://howdymary--mochi-desk-tasks-web.us-east.modal.run/).
See [the G1 refinement record](realism-v4.md) for assets, licenses, reproduction
commands, rendering, and limitations. The earlier four-DOF procedural robot
remains an archived prototype in `desk/tasks.py` and `body.html`.

| Task | Action | Target | Variable conditions |
|---|---|---|---|
| Laptop | Left hand pushes the screen's right edge | 90° from the desktop | Starting angle, screen mass, hinge resistance, contact friction |
| Globe | Right hand pushes tangentially, holds to brake, then releases | Marker aligned to fixed brass pointer | Starting angle, sphere mass, bearing resistance, contact friction |

`desk/g1_model.py` scales the pinned Menagerie model; `desk/g1_tasks.py` runs
position feedback, native-arm inverse kinematics and force-limited joint
actuators. MuJoCo runs at 500 Hz, control at 50 Hz, and trajectories export at
25 Hz including the exact reset and seven-second terminal poses. Arm joints are
the only actuators. The screen and globe each have a passive hinge. Their
states are initialized at reset and moved by simulated contact thereafter.

The fixed pelvis is placed at each station during a reset. Waist, legs and
fingers are fixed in the source stand pose. Added rubber fingertip pads make
the contact point explicit. Appearance is more detailed than the simplified
screen/sphere contact surfaces; no balance, walking or physical deployment
claim follows from this simulation.

Success requires ≤3° error, speed ≤0.07 rad/s and a 0.4-second terminal dwell.
A hand must contact the task object. Non-hand task object contacts, nonfinite
states and excessive object rotation invalidate an episode.

## Development checks — 17 November 2026

Controller: angular speed cap 0.35 rad/s, braking margin 0.025 rad, contact
depth 0.7 mm. Joint and contact gains are fixed simulation settings.

| Task | Development successes | Worst error | Non-hand object contacts |
|---|---:|---:|---:|
| Laptop | 8 / 8 | 1.98° | 0 |
| Globe | 8 / 8 | 1.38° | 0 |

Seeds 9000–9007 are development checks. Displayed seed 9000 has 1.70° laptop
error and 1.31° globe error. Raw measurements and all body transforms are in
`web/desk/tasks/`; they are not a trained-model evaluation.

Tinker post-training and the new research campaign remain paused for this
visual pass. No prior eraser/puck scores apply to these tasks. The existing
`desk/train.py` targets the superseded eraser, not this G1 environment.
