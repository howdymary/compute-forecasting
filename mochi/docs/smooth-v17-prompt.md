# Continue MOCHI with feasible contact actions and real model post-training

Continue inside `mochi/`. Preserve both stopped executions, their checkpoints, all failed attempts, the working viewers and the forecasting application.

The first V16 execution timed out before training. Its successor preserved exact states but found that all existing laptop actions failed on training case 101000. Both completed zero optimizer updates. Do not describe either as a trained-model improvement.

## Freeze the engineered capability before comparing models

The new library adds three classical controller choices:

- H0: the existing clock contact settings with a 0.0007 m/rad joint-rest prior in inverse kinematics. A matched development test reduced subsequent R4 recovery travel from about 9.06 to 3.62 rad while still physically pressing and releasing the clock.
- W6: globe-leg speed cap 0.12 m/s and turn cap 1.0 rad/s with bounded feedback gains. It passed two development states. In a matched case it used 122 steps versus 138 for W5 and 16.70 versus 18.66 physical seconds; native acceleration and torque-change checks remained within their fixed limits.
- P4: steady 0.60 N laptop control with a 16-second action horizon. It closed the hard training case within 12.72 seconds with peak contact force about 0.619 N. The global 0.8 N force limit, contact predicates and task-success checks are unchanged.

The H0/P4 fixed-reference sequence, before adding the separately tested W6 option, passed locally in 339.60 physical seconds and 470 measured steps, including the supported book turnaround, forward descent, loaded Post-it crossing and all four tasks. This is controller engineering, not a Tinker result. Keep that distinction visible.

All parent, intermediate, selected, fixed and static policies must see the same extended library, scene, route and verifiers. Reevaluate the parent with the new choice descriptions before training. Never use the older, narrower library to make the new checkpoints look better. Native ONNX locomotion weights remain fixed.

## Use the saved data without hiding the failures

Reuse the recorded parent-prefix state before the laptop from each interrupted training sequence. These are offline states produced by the verified 121-update parent. Do not describe their stored actions as fresh behavior from the extended policy.

From the saved clock-approach state, measure every clock choice with the same R4 withdrawal. Prefer valid task completion and less recovery joint travel, then time. Add recovery examples from the actual H0 terminal state by physically testing R0 and R1 and reusing the actual R4 subsegment already recorded after that same H0 reach. Verify its exact initial-state hash; do not run or charge that segment twice. Keep the original prefix and failed alternative records.

Continue each saved laptop-prefix state through the remaining tasks using new physical stages. Persist every result, state, cursor and receipt. If one training case has no valid action, retain its failed prefix and let the other cases finish. Require at least two complete training sequences and all six decision domains before scaling training. Never turn a failed task into a positive label.

Final evaluations and displayed demonstrations must be single uninterrupted rollouts from reset. Training-state restoration and counterfactual branches must never be spliced into a demonstration.

## Actually train and test

Restore the verified parent optimizer state and post-train the shared Qwen3.5-4B LoRA decision weights through Tinker. Every optimizer update includes walking, clock, drawer, laptop, globe and recovery data. Retention examples remain legitimate where the parent already chooses well; they do not prove a physical improvement.

Before scaling, verify a real completed optimizer update, changed walking and recovery probabilities on informative training-only probes, and a physical development rollout. Save additional-update checkpoints 0, 1, 4, 8 and 16. Keep optimizer state, RNG state, exact example counts and provider receipts.

Select using development data before opening the four reserved final scenarios. Preserve the fallback ranking already declared for an unqualified parent: qualified completion first, then falls and contacts, then steps/500 + mean recovery travel/5 + 0.1 times physical seconds/420, with earlier checkpoints breaking exact ties.

Compare parent, selected, competent fixed and training-derived static policies. Run separate matched-state diagnostics for walking, manipulation and recovery. Report whether the target of 10% fewer steps and 15% less recovery travel was met without lower completion or longer successful time. An unavailable qualified parent comparison must stay unavailable.

## Keep the existing budget

The budget is the same pool opened by execution 44686221838: at most 224 physical attempts or stages, 18 accounted CPU-hours, 16 optimizer updates and four concurrent physics workers. Do not create a fresh allowance.

The reconciled starting debit is 77 physical attempts and 3.870402069239898 accounted CPU-hours. It includes all 53 started remote stages, the preceding three local state probes 16 additional local engineering attempts and two completed cloud state/segment probes and three globe-command probes. Two interrupted remote calls retain full timeout bounds, and the old supervisors retain conservative CPU bounds. The original reservations and reconciliation remain archived. Preserve the existing inference, search and memory counters as well.

Use real Modal physics workers and low-CPU supervisors. Count new child calls and supervisor CPU separately. Join collection before checkpoint evaluation so concurrency stays within four physics workers. Run expensive component diagnostics serially if necessary to honor the remaining budget.

Use past.dev to recall the interrupted study, share the observed control gap and recovery-headroom finding, record the revised experiment, and publish the qualified result with actual cross-role recalls and audience controls. Use Exa in the main research loop to investigate the measured posture or hinge-control question. Distinguish source corroboration from the manually engineered changes. Never manufacture service usage or consume credits just to increase a counter.

## Deliver the evidence

Publish a separate synchronized checkpoint viewer with the same initial state and playback speed in each pair. Show actual checkpoint IDs, update counts, task verification, time, steps, recovery travel, intermediate checkpoints and failures.

Retain the full clock, drawer, laptop and globe rollouts, including book turnaround/descent and the paper crossing. Report which gains come from engineering, learned choices, changed task-end posture or recovery selection. Check static-policy equivalence. Do not claim native gait learning, hardware results or generalization beyond the measured simulation conditions.
