# Navigation across unseen cluttered desk layouts

Research date: November 20, 2026.

The November 21 [alignment amendment](navigation-v23-alignment-amendment.md) preserves the interrupted one-update probe and repairs its shared controller before rerunning all comparisons. The current run restores the exact untrained parent and permits fifteen further updates, keeping sixteen as the total pilot ceiling. Its scheduled checkpoints are 0, 4, 8 and 15; an actual-endpoint checkpoint is allowed if the bounded dataset contains unlabelled failures. Final layouts remained unopened throughout the repair.

The primary question is whether actual Tinker post-training improves physical navigation on unseen desk arrangements over the parent model, a collision-aware planner and conventional tuning. A separate experiment asks whether shared memory improves adaptation within three attempts. Exact geometry is privileged state. This study makes no perception or native gait learning claim.

The existing G1, MuJoCo 3.3.7, pinned ONNX gait, actuator control and strict fall/fixture checks are reused. V22's fixed-layout GMR changes are not promoted. Initial engineering uses a new layout adapter and frozen low-level controller choices; the parent and every checkpoint share that implementation. No physical root or feet are animated. All layout changes occur at reset. New source, assets, outputs and service identities use navigation-v23 paths. Existing demos and 339 frozen files remain unchanged.

## Plan and learning interface

First validate a complete physical navigation attempt in a furnished, rearranged desk. Derive collision footprints and a conservative robot envelope from the actual model. Plan continuous-clearance routes with A*, then execute waypoints through the existing turning and native walking controller. The model receives robot-relative geometry, goal pose and each bounded route/controller candidate. It chooses direct, buffered or careful clearance/control. Native gait weights remain fixed.

The navigation LoRA adapter uses the existing trainable Qwen3.5-4B and Tinker decision-model recipe. The parent and trained versions use the same new action contract, with the exact untrained parent restored after the controller amendment. Use real measured candidate outcomes as supervised targets. Each optimizer iteration receives a fresh generated training layout. Save parent and updates 4, 8 and 15; verify actual forward/backward, optimizer completion and behavioral changes. Reinforcement learning is excluded from this pilot unless a separately declared extension establishes informative rewards.

The generator moves printer assemblies and the mug, changes blocked corridors, and relocates stations. Decorative objects remain consistent between render and physics. Phase A is flat navigation: the existing 8 mm book steps are obstacles. Book-height and traversal generalization remain gated on physical validation. The four-task extension uses a separate unopened layout set and object-relative task primitives; archived task verifiers are unchanged.

## Splits, controls and memory

Generate sixteen training layouts and eight fixed development layouts. Seal eight final navigation layouts and eight final sequence layouts before checkpoint selection. Final layouts use held-out combinations of printer/mug corridor placements and goal headings. Report static generation rejections without filtering based on policy outcomes. Layout IDs and split names are excluded from model observations.

Use two physics seeds per development/final layout. The frozen implementation selects checkpoints by development qualified count first, then lower mean steps among qualified routes, then the earlier update. Distance and time are reported separately, not used as extra selection tie-breakers. Open the final navigation layouts only after source, model selection and training memory are frozen. Any later tuning uses a new final set.

Compare parent, selected model, competent collision-aware planner, training-derived conventional contextual tuning, and the strongest fixed training strategy. Conventional methods receive the same measured candidate outcomes. Audit policy equivalence and layout-dependent choices. The planner uses a neutral geometry-derived envelope and declared swing allowance, rather than certifying every dynamically changing body configuration.

Primary parent/selected tests disable memory in both. A separate selected-model memory comparison holds weights, scene, seeds and prompts fixed, changing retrieval only. First-attempt memory contains training facts only. Adaptation permits at most three reset attempts, with per-layout audiences and no cross-case test leakage. Parent and selected policies receive equal retry budgets. Report first-attempt and retry results separately.

## Verification and budget

Freeze navigation arrival, supported dwell, roll, contact, foot-clearance and horizon criteria before the main campaign. Existing whole-four-task aggregate acceleration thresholds are not repurposed as short navigation criteria. Their raw measurements remain reported. All four-task verifiers remain unchanged.

Measure goal arrival, falls, collision events, distance, excess distance over the declared planned route, all measured steps, minimum clearance, heading, foot sliding, sway, arm travel, overrides and latency. Efficiency comparisons require paired qualified completions. Report layout-level counts and paired uncertainty. A geometric route is not a successful physical rollout.

Pilot ceilings are 512 physical attempts including engineering, twelve summed single-core simulation hours, four physics workers, sixteen optimizer updates, 1.5 million training-token presentations and two million inference input/reserved-output tokens. API ceilings are four Exa searches, 96 memory writes, 256 actual recall HTTP calls, 350,000 ingested bytes and 2,000 estimated past.dev credits. Modeled total provider usage is capped at $50 using the saved official pricing snapshot. These are ceilings, not spending targets; existing billing settings and checkpoints are preserved.

Exa searches measured failures in the main research loop. past.dev carries sourced hypotheses, plans, observations and qualified verdicts across distinct writer/reader identities, with ingestion polling and a private canary. Modal executes real bounded physics batches. Tinker performs actual post-training. Existing backend secrets are checked by presence only; Actions secret references remain a fallback if the saved Modal secrets lack a provider.

The Phase B gate is at least 90% qualified development navigation with zero falls and zero invalid contacts. If unmet, retain the four-task archive and report the navigation limitations instead of opening the sequence final set.

Deliver the per-layout viewer using V22 materials, actual MuJoCo trajectories, routes and footprints; published split/checkpoint hashes; service receipts; reproducible commands; full failures; and a qualified result. Distinguish neural training from shared controller engineering and API activity from measured service benefit.
