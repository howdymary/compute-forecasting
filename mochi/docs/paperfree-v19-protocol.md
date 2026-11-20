# Paper-free desk and step-first controller selection

## Change under test

C19 removes the sticky-note stack from the MuJoCo model, scene specification and renderer. Its forced crossing, contact predicate and twelve planned foot placements are removed. The drawer-to-laptop leg is ordinary flat-desk walking. The books, printer, clock, drawer, laptop, globe, collision envelopes and previous safety limits remain.

This scene change is controller engineering shared by every C19 model and control. Comparing C19 with an earlier scene cannot isolate a training gain. The checkpoint comparison reruns the parent on the new scene.

## Measured objective

A failed, colliding, unbalanced or insufficient-clearance attempt is ineligible. Every valid branch receives `1000 - measured_step_attempts`, with bounded penalties below 0.0011 in total for arm travel and elapsed physical time. One fewer measured step therefore outweighs every possible tie-breaker. Every attempted step counts, including turns, alignment, corrective motion and unfinished attempts. No reward is calculated from a declared waypoint count.

Full qualification requires all four tasks, supported recovery, book ascent, supported turnaround and forward-facing descent, three successful flat walking legs and zero applied base force. Each flat leg must have at least two measured moving swings and at least 4.5 mm median minimum-sole clearance. Existing roll, lateral sway, loaded-contact travel, native acceleration, torque-change, forward-facing and time limits remain unchanged. Standing still, stopping early and returning to low-clearance shuffling cannot qualify.

Labels maximize this measured reward among physically valid alternatives restored from the same actual simulator state. Manipulation alternatives include their subsequent R4 release and arm recovery. Recovery alternatives are measured separately. These labels supervise post-training; this is not a claim of direct policy-gradient optimization of the step reward.

## Model boundary

Tinker updates the existing Qwen3.5-4B LoRA controller selector. Three flat walking decisions, four manipulation decisions and four recovery decisions use structured physical observations, including measured support state. Walking choices change native command speed, turn bounds and alignment gains while retaining contact-gated physical swing lift. The low-level ONNX gait weights and the safe book-traversal controller remain fixed. The model is outside the physics control loop.

W8 is the engineering reference. W9 uses faster flat commands without a forward foot residual. W10 additionally changes turn and forward alignment gains. All use the same vertical foot-lift target. A selected manipulation profile must close the actual laptop through contact and release safely. Branch diagnostics are never spliced into a continuous demonstration.

## Frozen comparison

Before new optimizer updates, hash the simulator, verifiers, action library, objective, scenario partitions and this protocol. Validate a complete reference first. Generate two guarded teaching sequences and compare alternatives from matched states. Require informative walking outcomes and valid teacher completion before training.

Run eight optimizer updates, each accumulating six explicit domain batches before the optimizer step. Save and physically evaluate updates 0, 1, 4 and 8 on three development scenarios. Select by qualified completion, then fewer measured steps, less recovery arm travel, less physical time and earlier update. Select before opening four fresh paired scenarios. Also evaluate fixed and training-derived static controls on two of those scenarios.

The primary target is four of four qualified selected-policy attempts, at least two qualified parent/selected pairs, at least 10% fewer mean paired steps and no longer mean paired time. A training-improvement claim additionally requires a nonzero selected update. Publish all failures and intermediate results even when this target is missed. This small fixed-layout pilot does not establish hardware performance or global route optimality.

## Services and evidence

Exa searches the observed walking-efficiency problem in the main loop and retains source links. past.dev transfers the sourced hypothesis, allocation plan, measured teaching data and final assessment between distinct identities; dependent reads wait for ingestion. A private critic canary tests audience isolation. Tinker supplies real optimizer updates and checkpoint sampling. Modal runs bounded physical experiments with receipts, immutable archives and uninterrupted recorded body transforms.

The bounded campaign includes local engineering usage: at most 112 physical attempts, 10 simulation CPU-hours, eight optimizer updates, four simultaneous Modal workers, 600,000 training-token presentations, 900,000 inference tokens, two Exa searches, ten memory writes and twelve recalls. Reservations and unfinished calls remain accounted. These bounds are ceilings, not usage targets.

## Preliminary engineering caveats

Keep all local attempts, including failures. The first seven probes preceded per-attempt source hashing and used provisional profile settings; retain that limitation rather than inventing provenance. Later attempts capture source hashes at launch. The final frozen protocol and parent/trained comparison use one common library. Snapshot branches are isolated diagnostics, while full demonstrations always start from reset.
