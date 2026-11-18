# Approved scope: Mochi learns to walk and complete four desk tasks

**Approved by Mary on 17 November 2026: execute the walking and four-task post-training pilot.**

Act as my robotics engineer, model-training engineer and visual demo director.
Extend Mochi inside `mochi/` in the existing `howdymary/mochi-demo` repository.
Preserve the active checkout, forecasting application, archives, existing working
demo and unrelated changes. Reuse available integrations and credentials. Keep
new code and artifacts in `mochi/`, apart from necessary additive Mochi workflows.
Do not spawn assistant sub-agents in this side conversation.

## One continuous physical sequence

Use the same detailed 22.1 cm Unitree G1 to perform this exact sequence:

1. Walk to the alarm clock, press its top button and release it.
2. Walk to the desktop organizer and push its drawer closed.
3. Walk to the laptop and close its screen safely.
4. Walk to the desktop globe, rotate its marker into alignment with the pointer,
   release it and finish upright.

Use one MuJoCo world, one simulation clock and one evolving robot state. Walk
between all four stations. Do not reset, teleport, animate the base along a path,
change robots or hide support at task boundaries. Camera movement may be directed
for presentation; robot and task-object movement must come from physics.

Retain one human-size desk, realistic materials and the detailed G1 hands and
body. Keep objects, foot clearance and contact points within validated physical
reach. Restore real leg actuation: the existing rigid-leg standing model is not
a walking controller. Validate a licensed G1 locomotion controller in its source
model before adapting it. Verify miniature mass, inertia, timing, contact, gain,
torque and joint-mapping assumptions rather than assuming checkpoint transfer.

## Four contact tasks

- **Alarm clock:** a passive, spring-loaded top button. Verify hand contact,
  sufficient physical travel, release and standing validity. The alarm/display
  indicator changes only after a measured successful press.
- **Drawer:** a passive sliding drawer in a desktop organizer. Verify remaining
  extension, low final speed, hand release, settling and standing validity.
- **Laptop close:** begin with the screen open and close it to a frozen angular
  tolerance without excessive impact, pinching the hand or tipping the robot.
  Verify contact-caused progress and a safe withdrawal. Validate the full reach
  or a controlled release/crouching strategy. The previous failed laptop-opening
  trial is not a closing demonstration and must not be relabeled as one. An
  untouched lid falling shut under gravity does not establish task success.
- **Globe:** rotate the passive sphere until its marker aligns with the fixed
  pointer, brake, release and remain within angular/speed tolerances for the
  required dwell time. Reject a transient pass through the target.

Initialize task-object states only at episode reset. Do not directly actuate or
assign their joint states during a run. Treat the button and drawer as sourced
benchmark adaptations and the laptop/globe as separately defined Mochi tasks.
Preserve original references, licenses and asset provenance.

## Tinker must train walking and all four task-control skills

Use one shared, task-conditioned model, initially `Qwen/Qwen3.5-4B` with LoRA
rank 16, subject to compatibility checks. Train its weights through Tinker.
The curriculum must contain physical experience for walking and every task;
training only one domain and describing the rest as learned is unacceptable.

The model has two kinds of responsibility:

1. **Closed-loop walking decisions:** repeatedly observe target-relative pose,
   heading, body orientation/velocity, foot contacts and recent actions. Produce
   bounded steering, speed, turning and stopping commands while walking. It must
   react to changing state, not merely select a prerecorded route or gait clip.
2. **Task-control decisions:** learn bounded contact parameters or profiles for
   approach, alignment, force/compliance, pressing, holding, drawer closure,
   laptop closure, globe rotation/braking and release, as applicable to the
   active task. Apply its choices to actual feedback-controlled contact motion.

A fast pretrained balance/motor controller may execute movement commands.
State exactly which component is reused and which weights Tinker changes.
Do not claim Tinker learned low-level leg torques or balance from scratch unless
that was implemented and measured. State-based observations are acceptable;
do not imply camera-based perception unless it exists.

Start with supervised LoRA post-training on numerically verified simulation
experience. Reward-based refinement is optional if its signal is informative.
Use actual `forward_backward` and `optim_step` calls, save optimizer state and
sampler weights, and retain losses, completed updates and checkpoint receipts.
Log training-example counts and learning metrics separately for walking,
button pressing, drawer closing, laptop closing and globe alignment. Model
inference, hand-tuned gains and pretrained walking alone do not count as Tinker
training. Tinker-produced decisions must actually drive evaluated rollouts.

## Freeze and evaluate before making claims

Freeze the simulator, action bounds, success/fall verifiers, observations,
scenario distributions, train/development/held-out splits, comparison methods and
budget before training. Keep the evaluator outside the model's editing interface.
Exclude seeds, hidden physics, outcomes and teacher labels from observations.
Check that the data contains informative choices and sufficient coverage for
every domain. Do not manufacture an intentionally bad baseline to create gains.

Measure both isolated skills and the uninterrupted sequence:

- Walking: station arrival, position/heading error, falls, foot slip, travel time
  and stability while stopping and handing off to manipulation.
- Each task: its physical completion criteria, safe contact/impact, release,
  terminal settling and robot stability.
- Full sequence: all four tasks completed in order, with actual walking between
  them and no resets. A successful final task does not erase an earlier failure.

Compare starting weights, successive trained checkpoints, the reused locomotion
baseline, a simple waypoint controller and training-selected fixed task-control
profiles. Keep other components frozen when comparing model checkpoints. Report
per-skill results and full-sequence results, paired sample counts and uncertainty.
An aggregate gain must not conceal worse walking or a failed individual task.
Explain when a simpler controller matches the learned policy.

## Show real learning across checkpoints in one seamless demo

For the initial pilot, save actual checkpoints at **0, 8, 16, 32 and 64 completed
optimizer updates**. Replay a fixed development route and all four task setups
with those checkpoints. Each checkpoint run is one continuous walk–press–walk–
close-drawer–walk–close-laptop–walk–align-globe episode.

Show actual behavioral differences: navigation mistakes, poor stopping,
misalignment, failed presses, incomplete closures, globe overshoot, recoveries
and any measured improvement. Display the checkpoint ID, completed updates,
current phase and real measurements. Keep the robot prominent; show its feet
while walking and close views of contact without cutting to a different rollout.

Provide an iteration timeline, autoplay and synchronized checkpoint comparisons
inside the same persistent desk scene. Clearly label the experimental reset
between checkpoint trials. Do not splice different checkpoints together and
present them as one uninterrupted physical episode, or hot-swap weights mid-run
without an explicit experiment definition.

A best-so-far walkthrough is acceptable if rejected/regressed candidates remain
visible in the experiment history. Do not fabricate improvement at every update,
substitute animation, cherry-pick starting/trained scenarios or smooth motion to
imply learning. If a checkpoint does not improve, show that. Select checkpoints
on development results only, then run a fresh held-out route/task set and display
its full results beside the chosen demonstration.

## Services, budget and delivery

Use Modal for bounded parallel simulation, initially at most eight CPU workers.
Use Exa for failure-specific research and past.dev for source-linked findings
and verified cross-role recalls. Keep provider credentials server-side and report
configured, attempted, failed and successful integrations accurately.

Start with a pilot capped at 64 optimizer updates and 3,000 simulated trials.
Verify that this covers walking and all four tasks before freezing the protocol.
Record actual resources, durations and costs where available. Any expansion
requires a stated reason and revised budget.

Deliver the four working tasks, validated physical walking and handoffs, the
continuous sequence, real checkpoint-based visual comparisons, Tinker training
receipts, matched evaluation, Blender rendering and reproduction commands.
Keep engineering, manual calibration, reused pretrained control, Tinker learning
and held-out results distinct. If walking or a task remains unreliable, report
its exact limitation rather than claim the full sequence is complete.

**Review gate satisfied by Mary’s instruction to execute this scope.**
