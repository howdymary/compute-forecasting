# Walking, manipulation and arm-recovery post-training

V8 resumes the retained V7 update-96 Qwen3.5-4B LoRA state. It trains repeated observed-state walking commands, four contact-profile choices, and post-task active-arm recovery. The Unitree gait network, standing controller, arm IK solver, simulator and object properties remain fixed. This is decision-policy learning rather than learning motor torques or gait-network weights.

The laptop fix is an engineered upper-edge force-controlled press from a front-right stance. The previous shallow position-step press produced insufficient sustained closing torque. Contact moves the actual hinged lid; the verifier still requires a lid angle below five degrees, low speed, contact-driven progress and release dwell. No lid pose or hinge property is changed to produce success.

Recovery has four actual actuator-control choices: direct fold, clearance withdrawal, the older parking detour, and delayed direct fold. The alarm clearance motion moves the shoulder outward before lowering, avoiding the clock housing. Other tasks can use a direct fold when it is safe. Recovery requires a stable rest pose, low joint speed, no fall and no fixture-contact steps above 0.01 N. Joint travel, hand path, duration and contacts are retained, including failures.

The new route keeps the first two V1 legs and uses a manually specified, swept-clearance-checked corridor to the laptop and globe. It is not a globally optimal route. The 10 mm planning allowance is an engineering allowance, not a proven tracking guarantee.

## Frozen comparisons

- Original V7 weights and original stack: engineering reference.
- Original V7 weights and frozen V8 stack: the actual pre-training baseline.
- Development-selected V8 weights and that identical stack: weight-training comparison.
- Fixed waypoint and task/recovery choices: conventional baseline, chosen using training evidence only.

Training uses seeds 23000–23007. Development uses 24000–24001. The final test uses 25000–25003 only after checkpoint selection. The 19000-series was used to engineer the fix and is not a held-out test. Each checkpoint replay is its own uninterrupted physical episode. All regressions remain visible. Additional updates are counted separately from the 96 parent updates.

Modal branches candidate task/recovery controls from recorded physical states. A fixed geometry follower supplies walking labels. Only successful physical task/recovery candidates supply supervision. Numerical integration state is saved with actuator mode and parameters; state-restoration tests bound reconstruction differences. Exact equality of every derived MuJoCo solver field is not assumed.

Tinker performs six forward/backward calls and one optimizer step per update. All six domains receive gradients. Recovery sampling is balanced across the four tasks. Repeated examples are reported as repeated training, not new physical evidence. Full optimizer states are retained at updates 8, 16, 32 and 64; update zero reuses the parent state. No checkpoint deletion or billing-plan change is part of this study.

Exa searches and source-verified past.dev handoffs occur at initialization and update 16. Recalled proposals choose between two predeclared equal-size training allocations. These services inform the outer research loop; neither is called at the physics timestep. The critic qualifies findings and a private-audience canary checks access isolation. No causal benefit from search or memory is claimed without an ablation.

## Run

From the repository root, with the existing backend provider credentials:

```sh
PYTHONPATH=mochi/src python -m pytest mochi/tests/test_control_v8.py -q
PYTHONPATH=mochi/src python -m mochi.control_v8.train
```

Live numerical progress: https://howdymary--mochi-control-v8-monitor-status.us-east.modal.run/

The additive workflow is `.github/workflows/mochi-control-v8.yml`. Configuration and split/selection rules are in `mochi/configs/control-v8-protocol.json`. Exact outputs, trajectories, unsuccessful branches and private model-state references go to ignored `mochi/artifacts/control-v8/`. Public exports must omit private state paths and credentials.

## Engineering calibration

On calibration seed 19001, fixed controls completed all four tasks, all four arrival checks and all four recoveries, without falling. This establishes a working vertical slice before training. It does not establish learned improvement. Isolated laptop calibration seeds 19000 and 19001 also closed the lid through contact.

Results from new training and held-out evaluation will be reported separately after the run completes. Improvement is not assumed in advance.

## Isolated control checks

After development selection, the same held-out seed block also receives separate task and arm-recovery probes. Navigation failure must not hide the quality of those decisions. Before/after task choices share an initial fixture state. Recovery choices share a post-task state produced by the predeclared B/A/P1/A engineering controls. If that reference task fails, the recovery pair is unavailable and counted as such. These resets belong only to isolated tests; the primary demo remains one continuous four-task episode. The additional batch is bounded at 80 physical rollouts and stays within the study’s 512-rollout cap. No resulting outcomes may select training checkpoints.

## Timing and deployment limits

The selector runs between bounded simulation actions. MuJoCo time pauses while remote model inference is pending; the fast native gait, balance and arm feedback execute inside each action. Completion time is simulated physical time, not real-time inference throughput. Worker wall time and actual Tinker inference calls are retained separately. This is not a real-time hardware control or sim-to-real demonstration.
