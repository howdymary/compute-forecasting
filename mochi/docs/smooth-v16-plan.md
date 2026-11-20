# Forward book descent and efficient recovery

The new campaign preserves the V15 demo and all archived experiments. Work is isolated in `src/mochi/smooth_v16/`, with separate configurations, artifacts, Modal services, model checkpoints and memory identities.

The physical route is clock, supported book-top clearance, approximately 180-degree turn, forward-facing descent, drawer, loaded contact on the existing Post-it stack, laptop and globe. No props are moved. MuJoCo supplies motion and contact. The browser renders recorded transforms.

The first turn probe hit the clock with the right hip. A lateral clearance attempt with large steps stalled. Smaller supported steps reached a clear stance, but ordinary waypoint navigation then drifted back toward the clock during the turn. The successful alternative uses independent airborne-foot yaw references while the loaded sole remains planted. An isolated attempt completed the full turn in18 rotating-foot placements after four supported clearance steps. It requires fresh continuous verification. These are engineering attempts, not training results.

The Post-it is an existing 44 by 44 mm, 2.4 mm-high physical stack. The first planned landing straddled its edge and was rejected by the fixture-contact audit. The revised plan lands on its top surface and verifies loaded sole contact. An isolated forward descent completed all six 8 mm downward placements with body and foot heading errors below 0.5 degrees. A paper crossing also passed, but the first full route hit its edge during the subsequent native turn. The revised exit continues with controlled steps until both feet clear the stack. Every new attempt runs from an immutable source snapshot. These are engineering results; gradients remain gated on a full continuous pass.

Recovery supervision will prioritize measured joint travel among valid recoveries, then elapsed time. The previous duration-weighted labels favored extra arm movement. A minimum-jerk recovery option is tested alongside preserved direct and clearance options. All options execute through arm actuators.

## Integration inventory

| Service | Reuse and current access |
| --- | --- |
| Tinker | Existing 0.39.0 SDK and decision recipe. Restore completed V15 selected optimizer checkpoint by verified identifier. API credentials are available through existing GitHub Actions secret references; absent from the local environment. |
| Modal | Authenticated local CLI profile, SDK 1.6.4, existing asset images and asynchronous simulation interface. New app, volume and progress names use smooth-v16. |
| past.dev | Existing ingestion journal, source verification and audience controls. New identities and audiences; recall the completed V15 result, including its recovery regression. Credentials remain in Actions. |
| Exa | Existing authenticated backend search adapter through Actions. Queries originate from measured turning, stair or recovery failures. |

[Tinker training API](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/trainingclient/) separates gradient calculation, optimizer updates and checkpoint saving. [Modal asynchronous execution](https://modal.com/docs/guide/async) uses the `.aio()` interface. Both were reviewed for this campaign.

## Budget and evaluation

The complete campaign, including engineering, permits 16 new optimizer updates, 224 physical rollouts, 18 simulation function CPU-hours and four concurrent simulation workers. Local probes retain their count and single-worker duration in `artifacts/smooth-v16-engineering/ledger.json`; training must import those costs rather than reset them. Failed probes count.

Three new training scenarios, three development scenarios and four unopened final scenarios are planned. Save updates 0, 1, 4, 8 and 16. Compare parent, selected, competent fixed and training-derived static policies. Isolate walking, manipulation and recovery with matching physical states, separately from uninterrupted routes.

Targets are at least 10% fewer steps and 15% less recovery joint travel, without lower completion or longer successful completion time. Qualification also requires the turnaround, forward descent, Post-it contact and existing balance/contact limits. These are targets, not results. Do not claim native gait training: Tinker updates the shared controller-selection model, while the native locomotion network remains fixed.

The final comparison will use identical initial conditions and playback speeds, real checkpoint IDs, measured footstep events, arm travel and task outcomes. Preserve full recordings and failed attempts. Report static-policy equivalence and negative results.

## Frozen selection rule

Each development checkpoint is ranked by qualified full completion, falls and forbidden contacts. Among equally qualified checkpoints, meeting both the 10% step and 15% recovery-travel targets without longer completion time takes precedence. Otherwise minimize mean steps divided by the parent mean, plus mean recovery joint travel divided by the parent mean, plus 0.1 times normalized physical time. Prefer the earlier update on exact ties. If no parent case qualifies, compare completion without claiming an efficiency percentage.

The new route has a 420-second physical feasibility horizon, declared before gradients. This replaces the older route's 275-second horizon for every new model and baseline. It is not a retrospective modification of an archived result. The turning and Post-it requirements add physical work, so old-route and new-route costs are reported separately.

Three training scenarios with at most 40 physical rollouts each, 15 development episodes, 16 final-policy episodes, 24 component branches and one remote preflight require at most 176 remote rollouts. At most 32 local engineering attempts are permitted within the overall 224-rollout ceiling. Local single-thread durations are charged conservatively as one-worker simulation hours; remote costs use the actual one-CPU function receipts. Reservations, failures and partial work remain charged.

## Physical scene revision

The longer route exposed passive laptop-hinge creep. In continuous-route-2, the initial lid angle declined from 1.227 radians to 1.128 radians by 319 seconds, then fell closed during the approach without any recorded hand contact. The unchanged contact verifier rejected the task. A closed lid alone does not establish successful manipulation.

The new scene revision is `richdesk-v16-open-hinge`. It adds 0.015 N m of passive hinge friction using MuJoCo's physical friction-loss parameter. It does not clamp the lid, change its state, move a prop or weaken task verification. Both new-model baselines and every checkpoint use the revision. Exact-state snapshots now preserve the friction-loss array as well as the previous dynamics fields. The fresh continuous reference and remote preflight must demonstrate that the actual hand can still close the lid.

A 12-placement book turn was tested and rejected after its support transfer stalled. The new campaign retains 18 rotating-foot placements for all actions. The faster walking option keeps the native gait's balancing arm motion; an earlier option that disabled it struck a pencil and was discarded before training.

The revised hinge also requires a later physical release. All new laptop profiles use 42 degrees, so gravity can finish closure across the declared friction and mass range. The previous 56-degree release could leave the higher-friction hinge partially open. Contact, force, final-angle, velocity and dwell predicates are unchanged. This is controller engineering before gradients.


## Route comparison before training

A matched-state paper-crossing diagnostic compared the south detour with a direct continuation after the verified drawer-departure waypoint. Both reached the same supported exit beyond the Post-it. The detour required 218 measured attempts and 71.226 seconds; the direct route required 108 attempts and 57.776 seconds. That is 50.5% fewer attempts and 18.9% less time for this isolated engineering comparison. It is not a Tinker result or a whole-route performance claim. Full continuous validation is required before training.

The frozen route will use the direct continuation for every model and baseline. The research comparison cannot take credit for the shortcut. New final scenarios remain unopened until checkpoint selection is saved.


## Continuous physical reference

Both final engineering references completed clock, turnaround, forward descent, drawer, loaded Post-it crossing, laptop close and globe alignment from the same initial state. The W4 reference used 476 attempts and 347.366 physical seconds. W5 used 462 attempts and 331.919 seconds. Both used direct arm recovery, the new hinge friction and 42-degree laptop release. All four tasks required actual hand contact, and both references had no falls or forbidden contacts.

These demonstrate available physical controller options, not an effect of Tinker training. The training parent and all saved checkpoints use the same options, route, scene revision and verifiers. The prior V15 route and its results remain archived without modification.


## Execution and reproduction

The additive workflow is `.github/workflows/mochi-smooth-v16-training.yml`. It injects the repository's existing Tinker, Modal, Exa and past.dev secret references on the backend. The local Modal profile is authenticated; other API keys are absent from the local environment. The new Modal app is `mochi-smooth-v16-learning`, with its own artifact volume, progress store and budget ledger. Forecasting and earlier demos are preserved.

Provider calls are in `src/mochi/smooth_v16/train.py`, `remote.py`, `services.py` and `parent.py`. The training client restores the verified V15 optimizer state, computes domain gradients and awaits 16 optimizer updates. Save optimizer states and sampling snapshots separately. IDs published in the viewer hash canonical optimizer references; they are not raw-weight checksums.

For a fresh physical reference, install `./mochi[robotics,remote,dev]`, run `python mochi/scripts/fetch_visual_models.py`, then run `python mochi/scripts/probe_smooth_v16.py --id local-reference --kind full --parameters '{"walk":"W4","recovery":"R0","seed":41001}'` with the configured Python environment. The wrapper sets the project root and creates an immutable source snapshot. A full reference starts from a fresh world and does not require unpublished historical state files.

The two completed engineering recordings are in `web/desk/smooth-v16-engineering/`, with compressed and uncompressed hashes in `evidence/smooth-v16/engineering.json`. They are explicitly labeled as engineering, not training results. The independent completed model viewer will be `mochi-smooth-v16-demo`. Its exporter is `scripts/build_smooth_v16_preview.py`, its deployment entry point is `scripts/deploy_smooth_v16.py`, and its checkpoint-view test is `scripts/check_smooth_v16_ui.mjs`.
