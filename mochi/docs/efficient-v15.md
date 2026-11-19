# Directional walking and step efficiency training

This campaign integrates the validated turning fix into physical data collection, parent inference, every trained checkpoint and the fixed baselines. Tinker updates shared Qwen3.5-4B LoRA decision weights for walking commands, clock/drawer/laptop/globe contact choices and arm recovery. The native ONNX gait, physics, route, verification rules and the new bounded action library are frozen before the model comparison.

## Objective and physical measurements

The target is at least 20% fewer measured step attempts than the frozen parent on matched successful final scenarios, without reduced completion, additional falls or forbidden contacts, or longer completion time. A 10% time reduction is a stretch target. Qualification also requires the existing balance, sliding and time limits, at least 90% forward-facing travel, and bounded native-walking acceleration and torque-change proxies. These are declared simulation tolerances, not hardware safety certificates.

A step requires measured unloading below 0.02 N, at least 30 ms and 2 mm sole motion or 8° rotation, then a loaded touchdown above 0.08 N with a 40 ms dwell above 0.05 N. Unfinished attempts remain counted. Sole poses and contact loads are sampled at 100 Hz. Turns, book traversal, alignment and clearance steps count separately and in the total. The detector reproduces all 20 ascent and 14 descent steps in the historical recording. Its 25-Hz historical total is 807; the corresponding new 100-Hz total is 810. Only matched 100-Hz counts are used for new efficiency claims.

Success and physical validity outrank step count. Failed early episodes cannot win for being short or using few steps. The verifier, physical task tolerances and detector are outside the model's action interface. No support forces, root repositioning, animated object states or hidden changes to playback speed are permitted.

## Engineering before training

The unchanged W0 controller reproduces the retained directional trajectory and task results exactly. The new W3/W4 actions expose bounded forward-speed, turning-rate and approach-gain choices. Existing W0/W1/W2 meanings are preserved. Book ascent continues to offer the three previously validated strategies; flat legs offer W0/W3/W4. Native gait weights remain fixed.

In one matched engineering scenario, W0 completed all four tasks in 810 steps and 265.686 physical seconds. W4 with the new G0 globe-braking profile completed in 474 steps and 224.162 seconds, without falls or forbidden contacts. The first W4/A attempt overshot the globe tolerance and remains a failed run. G0 and G1 were subsequently tested from the same supported approach state. These measurements establish useful controller alternatives; they are not results of Tinker training. [Engineering evidence](../evidence/efficient-v15/engineering.json).

Native-walking acceleration RMS was 134.48 rad/s² for W0 and 138.94 for W4/G0. The corresponding sampled torque changes were 0.003091 and 0.003157 N m. The pilot caps are 161.4 rad/s² and 0.00371 N m, approximately 20% above W0. Phase-specific measurements avoid describing a shorter episode's lower overall acceleration average as smoother individual strides.

## Parent and partitions

The previous training job remains unchanged. The new workflow shares its resource concurrency group and waits for it to finish. Use its selected checkpoint only if the run completed final evaluation and passes the declared qualification. Otherwise restore the completed V12 selection, update 1 in that campaign and 105 cumulative updates. Resolve its canonical optimizer state by the recorded hash through Tinker's inventory. Never promote the newest checkpoint merely because it is newer.

Use four new training seeds 91000–91003, three development seeds 92000–92002 and four unopened final seeds 93000–93003. The known seed-41001 engineering example is used only for the remote preflight. It is not fresh benchmark data.

## Training procedure

First verify a real fixed-controller remote preflight, then evaluate the frozen parent on all development scenarios. Record its numerical step and time targets before gradients.

Launch four parent-visited data collectors with a global limit of four simulation workers. Each branches all available actions from identical physical states at twelve walking, task and recovery decisions. The parent preference determines visitation when physically valid; otherwise a measured guard chooses a valid alternative. Task candidates are scored together with actual R0 withdrawal. Every completed branch is archived immediately, so a timeout cannot erase the branches already measured.

After two complete collectors provide all six domains and substantial corrections in both walking and task control, perform the first real optimizer update and a physical development probe. If the first two collectors lack sufficient signal, wait for the rest before gradients. Remaining collectors keep the pinned parent snapshot; their policy does not change during concurrent training. Join all collectors before update 2 and record both dataset stages. This is supervised post-training with guarded parent visitation, not unrestricted online reinforcement learning.

Perform 16 new Tinker optimizer updates, with actual forward/backward calls for every domain in every update. Compare saved snapshots at 0, 1, 4, 8 and 16; keep an additional durable state at 12. Verify changed decision probabilities after update 1 and retain actual checkpoint identifiers, domain losses, batch digests, RNG state, token counts and optimizer receipts. The official API specifies gradient calculation, optimizer updates and durable state restoration separately. [Tinker training API](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/trainingclient/).

Select using development outcomes, with qualified completion and safety first, then step count and physical time. Open final scenarios only after saving the selection. Compare parent, selected, competent fixed W0 and training-only static station preferences. Separate shared-state walking, task-plus-withdrawal and recovery probes identify which behavior changed. Keep unchanged choices, regressions and negative results visible.

Paired step and time changes include deterministic 20,000-resample descriptive intervals when at least two matched successful cases exist. These describe the small fixed-layout cohort; they do not establish performance across other layouts or hardware. Classify quality before persisting rows so every exported result retains its actual qualification.

## Sponsor integrations

past.dev stores observed failures, sourced hypotheses, the chosen training allocation, results and qualified conclusions. Source-verified cross-role recalls must affect the workflow. Shared and private audiences use actual access controls; a synthetic private canary checks denied access. Ingestion identifiers are journaled, and dependent reads wait for completion. Counts distinguish unique writing and reading identities from numbers of records.

Exa runs inside the research loop. A model chooses a bounded query emphasis from the measured turning, alignment and globe-contact evidence. Sources inform the frozen supervision-allocation choice; they do not edit physics or success criteria. No causal search or memory benefit is claimed without an ablation.

Modal runs real parallel physical experiments in `mochi-efficient-v15-learning`, with a separate artifact volume and progress/budget stores. Tinker performs real model post-training and fixed-checkpoint inference. All credentials stay on the backend through existing GitHub Actions secret references.

## Budget and publication

One campaign permits 16 new optimizer updates, 224 total physical rollouts, 18 simulation CPU-hours, four concurrent 1-CPU workers, 1,000,000 training-token presentations and 800,000 inference tokens. Sponsor limits are three Exa searches, twelve memory writes and sixteen recalls; ingestion polls and source-verification retries are logged separately. Maximum planned rollouts are 204: one preflight, up to 148 training branches/continuations, fifteen development episodes, sixteen final episodes and twenty-four component probes. Function deadlines are 5400/1800/3600 seconds for collection/evaluation/components; reservations and failed or interrupted work remain charged to the ledger.

Export only completed model comparisons. Each displayed version is one uninterrupted clock → drawer → laptop → globe episode, using identical initial conditions and playback speed. Show checkpoint IDs, actual optimizer counts, measured step counters, physical time and task outcomes. Preserve all development checkpoints and every final parent/selected pair. Publish the 20% goal as achieved only when the declared tests support it; retaining update zero or missing the target is an acceptable recorded result.

The additive workflow is `.github/workflows/mochi-efficient-v15-training.yml`. The independent completed viewer is `mochi-efficient-v15-demo`; it does not replace earlier demos or forecasting deployments. Exact provider integration paths are in `src/mochi/efficient_v15/train.py`, `remote.py`, `services.py` and `parent.py`. Public exports exclude canonical optimizer references and raw source excerpts.
