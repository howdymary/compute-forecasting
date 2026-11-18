# Build prompt: Mochi desk curriculum and Tinker post-training

Act as the robotics engineer and training engineer for Mochi. Work inside
`mochi/` in the existing checkout. Preserve the forecasting application,
archives, active branch, and unrelated changes. Use an isolated Git index for
publishing to `mochi-desk-v3`. Reuse the existing credential and remote execution
paths; keep provider keys on the backend.

Extend the current miniature Unitree G1 into one continuous desktop demonstration:
walk to an alarm clock, press its top button, release, walk to a desktop
organizer, push its open drawer closed, and stop. Use one MuJoCo world, one robot
state, one simulation clock and one exported trajectory. Keep the existing globe
preview available while the new sequence is being validated.

## Physical tasks

- Alarm clock: an attractive, human-size desk alarm clock with a passive,
  spring-loaded top button. Verify button travel through hand contact, release,
  and the robot remaining upright. The display may change only after the
  measured press event. Freeze the travel/release thresholds before training.
- Drawer: a desktop organizer with a passive sliding drawer. Verify the remaining
  extension, low final speed, release and terminal settling. Vary initial opening,
  position and sliding resistance. No object joint may be directly actuated or
  assigned during an episode.
- Both are adaptations of Meta-World task families, not official benchmark runs.
  Preserve source references and publish Mochi's own task definitions.

## Walking

Restore actual leg actuation and a free base. First validate an official,
licensed G1 locomotion controller in its source simulator model, then validate
any geometry/dynamics scaling and joint mapping in the miniature model.
A source controller is not automatically valid after miniaturization.

Move the base through simulated foot contact and actuator torques. Never
translate the robot root along a path or replay a walking clip as evidence of
physical locomotion. Check falls, body tilt, ground contacts, heading, travel
distance and stopping accuracy. Preserve walking failures. At each station,
blend actuator targets into the manipulation controller; do not reset or
teleport the base. If a controller cannot be made reliable, report the exact
limitation and keep working alternatives explicit.

## Actual Tinker training

Train a bounded, task-level controller selector with Tinker LoRA post-training.
The selector chooses contact/stopping profiles; it is not the motor controller
and must not be described as having learned walking. Keep the low-level walking
controller common to starting-weight and post-trained comparisons.

1. Freeze the simulator, verifier, scenario distributions, observation fields,
   controller catalogue, train/development/test splits and experiment budget.
2. Generate physical outcome labels for the catalogue on training scenarios.
   Check that examples offer meaningfully different outcomes and that more than
   one useful profile is needed. Exclude seeds, hidden physics, outcomes and
   teacher choices from model observations.
3. Use Tinker's real training APIs: create a LoRA training client, perform
   `forward_backward` and `optim_step`, and save optimizer state and sampler
   weights. Record completed updates, losses and checkpoint receipts. Inference
   calls alone do not count as post-training.
4. Select a checkpoint using development results only. Freeze it before opening
   the test scenarios.
5. Compare starting weights, post-trained weights, the best training-selected
   fixed profile per task and a simple observable-feature baseline. Report
   paired counts and uncertainty. Do not require a positive result or hide a
   fixed-controller explanation.
6. Show a synchronized before/after from the same fresh scenario. Explain how it
   was selected and show the full test batch beside the demonstration.

Use bounded Modal CPU parallelism for MuJoCo trials. Use the existing Exa and
past.dev adapters for source-grounded ideas and verified evidence handoffs,
with Mochi-specific identities and audience isolation. Sponsor services should
produce actual receipts, not labels in the interface. Do not let a memory or
research failure silently become a fabricated successful integration.

## Delivery

Add the two tasks, an uninterrupted walk–press–walk–close trajectory, a polished
replay with phase and contact telemetry, Blender rendering commands, the frozen
protocol, training and evaluation receipts, and reproduction instructions.
Preserve the current working demo until this sequence passes physical checks.
Keep setup, task engineering, pretrained locomotion, manual tuning, neural
post-training and held-out evaluation clearly distinguished.
