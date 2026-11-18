# Free-standing Mochi and the next task set

Research and implementation: 17 November 2026.

The black rod in the previous preview illustrated a fixed pelvis. It was a
rendered stand, while the actual simulation support came from removing the
pelvis free joint. Deleting only the mesh would have concealed that constraint.

The current preview removes both the rod and the world anchor. The pelvis has
six free degrees of freedom. Gravity, foot contacts, arm actuator torques and
arm joint gravity compensation determine the motion. The legs, waist and
fingers retain rigid poses. This is foot-supported standing manipulation,
not walking, a trained balance controller, or a validated physical G1.

[Open the preview](https://howdymary--mochi-desk-tasks-web.us-east.modal.run/).
The globe is the primary episode. The laptop tab is explicitly a failed load
test; it is not presented as a completed task.

## Physical checks

The original standing placement with the old contact controller completed 3/8
globe development cases, with two falls. The full-size laptop hinge also
caused a fall. The robot's model mass is about 160 g; the laptop panel is
140–180 g, and its hinge requires substantial torque. The two tasks impose
very different loads on the standing robot.

The revised globe setup places the pelvis at x=80 mm, y=45 mm, within the native
arm's comfortable reach. A hand-configured controller uses a 0.25 rad/s stroke
cap, 0.025 rad braking margin and 0.3 mm contact depth. No learning was performed.
The shorter reach avoids driving the arm near its extension limit; the gentler
contact lowers the reaction load. These are engineering interpretations of the
observed behavior, not an isolated causal experiment.

| Check | Outcome |
|---|---|
| Globe development seeds 9000–9007 | 8/8 successes, zero falls |
| Worst globe final error | 1.41 degrees |
| Maximum body tilt in that batch | Less than 0.44 degrees |
| Applied force/torque at the six base DOFs | Zero throughout |
| Terminal support | Both feet in contact |
| Laptop load test, seed 9000 | Rejected; the robot fell |

Success still requires the angular target, low angular speed and 0.4 seconds
of terminal settling. Standing validity additionally rejects a base tilt over
30 degrees, a pelvis drop over 25 mm, non-foot ground contact, or missing
terminal two-foot support. The limits are fixed in the evaluator.

These are development checks used during manual setup, not held-out
performance or post-training improvement. Earlier fixed-base 8/8 results
remain separate. Public receipts:

- `web/desk/tasks/free-base-initial-calibration.json`: original free-base cases.
- `free-base-manual-calibration.json`: 12 explicit parameter trials.
- `free-base-placement-calibration.json`: eight shorter-reach trials.
- `free-base-calibration.json`: the final eight globe checks and failed laptop case.
- `free-globe.json`, `free-laptop.json`: complete displayed trajectories.

A physics test removes ground contact and verifies that the base falls. This
checks that a hidden world anchor has not replaced the visible stand. Other
tests verify the free joint, absence of a base actuator/equality tether,
zero applied base force in the delivered run, foot support and native G1 arm
kinematics. Browser and Blender rendering use the same recorded body poses.

## Recommended task progression

The next two tasks should be **top-down button pressing and drawer closing**.
Both are existing [Meta-World tasks](https://metaworld.farama.org/benchmark/task_descriptions/).
A button enclosure and a desktop organizer put the contact surfaces at a
reachable height without adding another miniature table.

| Task | Shared reference | Why it fits / what it requires |
|---|---|---|
| Top-down button press | [Meta-World](https://metaworld.farama.org/benchmark/task_descriptions/#press-button-top) | Clear contact, travel and release events; a light spring; no grasp required. Place the button within measured arm reach. |
| Drawer close | [Meta-World](https://metaworld.farama.org/benchmark/task_descriptions/#close-drawer) | A visible start/end state and a linear joint; use a small organizer with measured sliding resistance. The robot can push the front without gripping. |
| PushCube | [ManiSkill](https://maniskill.readthedocs.io/en/latest/tasks/table_top_gripper/#pushcube-v1) | A clear planar target. An upright G1's hands do not reach low objects on the desktop; this needs a validated crouching/reaching posture. |
| PushT | [Diffusion Policy](https://diffusion-policy.cs.columbia.edu/#pusht), [ManiSkill](https://maniskill.readthedocs.io/en/latest/tasks/table_top_gripper/#pusht-v1) | Richer position-and-orientation alignment and recovery. The same reach limitation applies; multiple contacts make it a later task. |
| Lift, stack, peg insertion | [ManiSkill task cards](https://maniskill.readthedocs.io/en/latest/tasks/table_top_gripper/) | Require active finger/gripper control, reliable grasping and appropriate load/balance checks. The current fixed fingers do not establish those capabilities. |

The original real-world Push-T sequence aligns a T block to a target region
and then withdraws the end effector to an end zone. ManiSkill documents target
coverage for its adaptation. That is not interchangeable with a generic
position-only pushing metric.

For Mochi, button success should verify physical slider travel, contact,
release and standing. Drawer success should verify the final extension,
settling and standing. Exact scaled tolerances, observation/action interfaces
and train/development/test splits must be frozen before controller search.
A before/after should show alignment or stopping failures followed by measured
success on fresh scenarios, with the full batch reported beside the selected
video.

Changing the robot, scale, controller and simulator setup creates a benchmark
**adaptation**. We must not call a Mochi percentage an official Meta-World,
ManiSkill or Diffusion Policy result or compare it directly with those
leaderboards.

## Object choices

[YCB](https://registry.opendata.aws/ycb-benchmarks/) provides an established
Yale–CMU–Berkeley object/model set for manipulation benchmarking, with public
object downloads and CC BY 4.0 licensing. It is useful for later textured
household-object grasping and placement studies. Geometry does not remove the
need to verify collision shapes, scale, mass and inertia in this simulation.

For the first two tasks, prefer source-linked button and drawer fixtures with
simple, calibrated contact surfaces. Keep the Sand3D laptop, globe and lamp
as scene assets or explicitly custom tasks. Sand3D reconstruction and
attractive materials alone do not make a manipulation task standardized.

No YCB assets or replacement benchmark tasks have been integrated in this
revision. The recommendation above is a design decision for the next build.
Exa/past.dev/Modal experiment orchestration and actual Tinker post-training
remain a subsequent phase after the new task definitions are frozen.

## Reproduce

From the repository root, with the existing environment and G1 assets installed:

```sh
PYTHONPATH=mochi/src mochi/.venv/bin/python mochi/scripts/check_free_base.py
PYTHONPATH=mochi/src mochi/.venv/bin/python -m pytest -q mochi/tests/test_g1_model.py mochi/tests/test_desk_tasks.py
mochi/.venv/bin/python mochi/scripts/build_display.py --free-base
blender -b --python-exit-code 1 --python mochi/scripts/render_g1.py -- --task globe --input mochi/web/desk/tasks/free-globe.json --out mochi/artifacts/free-base --frame 45 --samples 64
python -m http.server 8773 --directory mochi/web/desk --bind 127.0.0.1
```

The older fixed-base renderer remains reproducible by providing an older
receipt. Its stand is drawn only for a receipt marked as fixed. Upstream
geometry/material credits remain in the public asset manifests.
