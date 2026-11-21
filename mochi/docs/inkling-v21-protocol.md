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
