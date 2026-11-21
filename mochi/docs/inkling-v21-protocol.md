# Inkling 2 Mini controller research pilot

This pilot uses `thinkingmachines/Inkling-2-Mini` through Tinker to diagnose Mochi's measured failures and propose bounded controller changes. It starts with inference and physical controller experiments. No new optimizer updates or native gait training are claimed in this phase.

The completed C19r1 study, its 236 frozen files, archived checkpoints and twenty-recording demo remain unchanged. Current failed and successful recordings can inform development. They cannot serve as a subsequent unseen test cohort.

## Scope

The bottlenecks are unnecessary station-alignment steps, approach-dependent laptop contact, fixture clearance after contact and arm recovery. Proposals receive actual measurements, relevant source code and recorded simulation images. Images support diagnosis; authoritative simulation state and numerical checks determine outcomes.

The model proposes parameter or controller changes within a declared schema. It cannot edit the simulator, task order, success checks, thresholds, scene or archived records. Generated text is never executed directly. Every proposed parameter is validated before a physical attempt.

Matched restored-state branches are development diagnostics. Any accepted complete-demo change requires from-reset physical evaluation. All four tasks, loaded support, foot clearance, balance and contact limits remain mandatory before comparing step efficiency. Every step, including alignment and unfinished attempts, remains counted.

## Services

An isolated Modal gateway uses Tinker 0.39.2, Cookbook 0.7.1, tml-renderers 0.4.2 and PyTorch 2.15.0. Existing GitHub secret references inject credentials into the backend. The exact model must appear in the account's supported-model response; no model substitution is permitted. Image bytes are rendered with the official Inkling message format.

past.dev receives compact, source-linked observations and proposals under Mochi-specific identities and shared/private audiences. Dependent recalls verify source IDs after ingestion. Failure-driven Exa searches provide mechanisms to test. Exact packets, model receipts and numerical results remain in artifact storage.

The gateway is authenticated through Modal and has no public HTTP endpoint. Calls, actual or conservatively reserved tokens, sources, image hashes and model output are retained. Report inference and controller-engineering results separately from neural weight training.

## Bounds and acceptance

Limits are eight model calls, 200,000 input/output tokens actual or reserved, two Exa searches, 24 physical attempts and three simulation CPU-hours. This phase performs zero optimizer updates. Failed calls and failed physical attempts remain charged and recorded.

Start with exact model access and one bounded proposal batch. Reject invalid schemas, unsupported claims, unsafe contacts and infeasible motions. Fix feasibility before expanding experiments. Select changes on development data; freeze them before opening fresh scenarios. A shorter failed route cannot count as an efficiency gain. Keep the existing validated demo available throughout.

Official references: [release](https://thinkingmachines.ai/news/inkling-2-mini/), [model card](https://thinkingmachines.ai/model-card/inkling-2-mini/), [renderer](https://tinker-docs.thinkingmachines.ai/cookbook/inkling/tml-renderers/) and [image input](https://tinker-docs.thinkingmachines.ai/cookbook/inkling/images/).

## Interpreter revision after the first measured proposals

The first station proposal used the declared 4 mm tracking requirement. It timed out after 367 alignment attempts and did not attempt the laptop task. The original-target controller can only be assumed to track within its native 12 mm window. Subsequent station proposals therefore expose an explicit 8 to 12 mm controller tolerance, with measured realized position reported; the original 12 mm bound is never loosened. This does not rehabilitate the rejected attempt. Its original adapter and experiment source are retained under the first-revision hashes.

The model's XY-only terminal deadband increased the matched laptop leg from 110 to 154 steps, including alignment increasing from 12 to 56. It is rejected on that case. The next proposal interface permits an independently controlled yaw deadband and a bounded change to the existing post-laptop clearance waypoint's y coordinate. Both modify commands or route targets, not physical poses, support checks, object geometry or global validity limits.

The next review receives actual laptop and printer collision AABBs and recalls the earlier model proposal through past.dev. The baseline fixed vector completed the laptop on development seed 221000, then hit the laptop base during the following walking leg. Earlier cases also included a knee striking the printer tray. These are separate contact observations and should not be conflated with hand-contact or arm-recovery failures.

## Stronger contact reference before final tests

The fixed P5 reference failed the second development laptop case before reaching the revised clearance route. Prior measured C19r1 controller choices favored the existing pulsed P6 contact controller. The next component check therefore includes P6 as a conventional control. Final paired tests will use P6 on both sides, with H0/C/G0, W10 and R4 unchanged, so changing the laptop profile cannot be attributed to the clearance proposal. This is a fixed control vector based on recorded choices, not a new live evaluation of the Qwen selector.

The proposal interface can explicitly select P5 or P6. Any such choice is an existing-controller selection, not a new locomotion network. Exact executed contact profiles remain in each episode. There are still zero optimizer updates in this pilot. Final scenarios 223000 through 223003 remain unopened until the chosen configuration is frozen.

## Final selection

The P6 component control fell on the hard development snapshot. Lowering the P5 target to 0.30 rad/s failed to close on both tested failed snapshots. Those contact proposals are not promoted. The clearance-only configuration completed one development route within every quality limit and retained the other development laptop failure.

Before opening final scenarios, freeze clearance y = 0.055 m with P5 retained as the primary reference on both sides. Keep two additional P6 controls on final seeds 223000 and 223001 rather than silently dropping that comparator. This supersedes the tentative P6-primary plan based on development evidence, with no final data observed. The 239-file freeze includes the earlier 236 physical sources plus the current adapter, experiment runner and selected configuration. Four fresh pairs and two extra controls bring total physical attempts to the unchanged ceiling of 24.
