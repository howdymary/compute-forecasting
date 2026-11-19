# Continue MOCHI’s walking and task-policy training

Act as my robotics engineer and training systems architect. Execute a new, bounded MOCHI V13 study inside `mochi/`, using the completed V12 assessment. Keep the forecasting application and previous MOCHI results, checkpoints and demonstrations intact.

## Start from the evidence

Read `mochi/docs/terrain-v12-assessment.md` and its numerical JSON. Verify the completed evaluation artifact and the selected checkpoint. Restore V12’s **selected update 1**, not the last update merely because it is newer. This is 105 cumulative updates in that selected lineage; V12 completed 32 new updates and retained its unpromoted states.

V12’s selected model completed all four tasks within the frozen balance/time limits on 6/6 new simulation scenarios. The parent completed 3/6 and the fixed controller 5/6. This is a small simulation cohort. A walking-domain intervention demonstrated a changed profile choice that avoided an ascent fall. The manipulation-domain intervention produced identical parent and selected outcomes on its one scenario, so do not claim a demonstrated manipulation gain from that check.

The recovery-only full-route intervention also completed under both models on its single scenario. The selected version used 5.643 rad of recovery joint travel per successful recovery versus 5.710 for the parent, and took 0.206 seconds longer overall. These are small, whole-route observations, not a matched-pose recovery result. The next study must test that distinction directly. The completed evaluation and real memory/isolation checks are recorded in [run 44514013316](https://github.com/howdymary/mochi-demo/actions/runs/44514013316).

Keep the distinction precise: Tinker updates the shared Qwen3.5-4B LoRA model that selects walking strategies, task-contact profiles and arm recovery. The native ONNX gait network, contact/IK controllers, action primitives, route, scene and verifiers stay fixed. This campaign does not train motor-network weights or a vision policy.

## What to improve

Preserve the G1 body and furnished desk. Each full demonstration remains one uninterrupted physical rollout:

1. Ascend the books and silence the clock.
2. Descend and close the drawer.
3. Walk to and close the laptop.
4. Walk to and rotate the globe to its verified target.

Improve the learned decisions without sacrificing completion. Address three weaknesses in the previous training procedure: teacher states did not necessarily match those visited by the student; scoring a task alone ignored the withdrawal state it left behind; and checkpoint selection gave tiny raw sway differences priority over substantial time savings.

Before training, freeze practical balance bins of 0.5 degrees torso-roll RMS and 2 mm lateral RMS. Within the safe bins, compare execution seconds plus **0.25 seconds per radian of recovery joint travel**. Keep the original hard validity and smoothness limits. Never count an early failed episode as a fast completion.

## Use the services in the actual workflow

Use the existing authenticated integrations and secret references. Create a separate V13 Modal app, artifact volume, progress and budget records, identities, and shared/private past.dev audiences.

Recall a ready, source-verified prior finding through past.dev. Prefer the previous critic’s final verdict; if it is still pending, say so and recall an available verified historical finding instead. Read the completed numerical assessment independently. Write the current failure evidence, let the researcher choose a bounded research emphasis, and run an Exa search generated from those measured failures. Preserve the query, retrieval time, URLs, excerpts and receipts.

Write the sourced hypothesis to past.dev. Have the designer recall it and use the evidence to choose the predefined six-domain supervision weighting. Have the experimenter recall the resulting proposal before data generation. Do not present search or memory as a proven cause of better performance without an ablation.

## Generate fresh physical training data

Use training seeds 71000–71003, development seeds 72000–72002 and unopened final-test seeds 73000–73003. Verify these partitions are disjoint and do not reuse the previous campaign’s test scenarios as new test data.

Run four real MuJoCo data-collection episodes on Modal. At each of the twelve walking/task/recovery decision points, branch every available action from the same measured state. For manipulation candidates, also execute a measured R0 withdrawal before scoring the candidate. Reject falls, invalid contacts and failed actions.

Let the frozen parent’s preferred action determine the next visited state when it passes the physical guard; otherwise execute the best verified alternative. Label the state with the best measured candidate and record every guard intervention. Describe this as guarded student visitation, not pure on-policy learning. Preserve failures and counterfactual provenance. These branches are training/diagnostic data and must never be spliced into a demonstration.

Before gradients, require at least two complete valid collection episodes, data for all six domains, and substantial measured corrections in both walking and manipulation: avoiding a failed action, improving a frozen balance bin, or at least 0.1 seconds of execution/cost benefit. Stop and report insufficient signal if these gates fail.

## Actually post-train with Tinker

Restore the selected canonical optimizer state. Perform up to **16 new optimizer updates**, each with real forward/backward calls for walking, clock, drawer, laptop, globe and recovery. Preserve batch digests, losses, token presentations, optimizer completion, seeds and RNG state.

Save comparison checkpoints at 0, 1, 4 and 16, plus durable optimizer states at 8 and 12 for recovery. After the first update, verify a measurable decision-probability change in every intended domain. Save private optimizer references before sampling diagnostics. Do not delete checkpoints or silently repeat completed updates after an interruption.

## Evaluate the weights fairly

Evaluate all four comparison checkpoints on the three development scenarios with bounded parallel workers. Select and freeze one checkpoint using the declared safety/balance/cost rule before opening final tests. Retaining update zero is an acceptable result.

On all four final scenarios compare the parent, selected checkpoint, existing fixed controller, and a stronger state-independent baseline whose station preferences come only from training labels. Keep every failed trial in the denominator. Report whether a fixed preference can match the learned model.

Also run exact shared-state diagnostics for walking alone, each manipulation task and arm recovery. Obtain the supported starting states from the first complete fixed-controller route in predeclared seed order; if none completes, use the first route with greatest captured-state coverage and mark missing states. Never choose these states using trained outcomes. Both models must start each component from the identical physical-state hash. Report these as separate diagnostic branches, not full-route demonstrations.

Record complete-sequence/per-task success, book traversal, falls, contacts, physical time, distance, sway, loaded-contact travel proxy, and recovery joint travel. Compare time and movement only on paired cases where both complete. Preserve uncertainty, regressions and unchanged behaviors.

Write results to past.dev, require source-verified critic recall, record its qualified interpretation and let the researcher recall the verdict. Verify the private critic audience with a synthetic canary and a denied designer read. If final ingestion is delayed, journal it and label the review pending; never pretend a dependent recall occurred.

## Publish the actual comparison

Keep the V12 viewer intact. Export a separate V13 checkpoint page only after completed evaluation. Show complete physical recordings from the same scenario, initial state, task order and playback speed, using actual checkpoint identifiers and optimizer counts. Show all development checkpoint versions and every final parent/selected pair. Keep failures and non-monotonic results visible.

Use the measured simulation transforms; do not reposition the root, animate task objects, add hidden supports, filter instability or stitch successful segments together. Label the page as simulation replay. Publish numerical results, source provenance and service evidence, keeping credentials and canonical optimizer paths out of the frontend.

## Hard execution limits

One campaign: 16 new optimizer updates; 224 physical rollouts; 18 simulation-function CPU-hours including conservative reservations; at most four 1-CPU workers; 1,000,000 training-token presentations; 800,000 inference-token reservations; three Exa searches; twelve past.dev write operations; sixteen source-verified recall operations (ingestion polls and verification retries are logged separately). Teacher/evaluation/component function deadlines are 4500/1500/3000 seconds. The main training step has a 335-minute limit and the job leaves time to upload evidence.

Do not reset a budget to hide spent or interrupted work. Stop at a limit with durable artifacts preserved. Promote nothing solely because it used more compute. Execute `python -m mochi.terrain_v13.train` through the dedicated workflow, then run the completed-only assessment/export checks and add the V13 viewer alongside the existing demonstrations.
