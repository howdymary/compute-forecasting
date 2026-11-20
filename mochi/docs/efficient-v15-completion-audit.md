# V15 completion audit

Verified 2026-11-20T02:22:52.563868+00:00. Frozen experiment source: `87ba8d482efd13c789bb200ae9424924e0f77ad1`.

[Technical article](https://howdymary.github.io/mochi/) · [Fresh-case comparison](https://howdymary--mochi-efficient-v15-demo-web.us-east.modal.run/?scenario=held-out-93000) · [Execution record](https://github.com/howdymary/mochi-demo/actions/runs/44625135986)

| Requirement | Verified evidence |
| --- | --- |
| Training | 16 completed optimizer updates, 96 domain-gradient calls, distinct checkpoints 0/1/4/8/16; native gait fixed. |
| Frozen method | 149 frozen source files unchanged; development selection precedes disjoint final tests. |
| Final tests | All four policies qualified on 4/4 fresh cases. Selected model reduced paired steps 40.9% and physical time 17.6% versus parent. |
| Component tests | 24 valid branches from 12 matched physical states, with separate walking, object control and recovery diagnostics. |
| Budgets | 204/224 physical rollouts, 10.341/18 function CPU-hours, four-worker bound, 16/16 updates. No retraining during publication. |
| Services | Actual Tinker updates, Modal simulation receipts, one Exa search, six past.dev writes and seven logical recalls. Four writers/readers, five within-campaign verified cross-role reads, private-audience denial passed, no pending ingestion. |
| Recording integrity | 23 hashed continuous recordings; same initial frame within each comparison; all 16 final-policy recordings independently checked for endpoints and contact. |
| Live demo | 19 paired checkpoint/scenario views checked. Complete fresh-case playback observed without scrub or restart. Observer time window expired once and was continued on the same playing page; full horizon then attested. |
| Scrubber | Native slider end-rounding fixed and verified against both completed episode labels; physics and playback rates unchanged. |
| Blog | Published technical article uses the first declared fresh final case first, preserves development checkpoints and historical comparisons, and passes desktop/mobile checks with zero italics, em dashes or field-notes text. |
| Archives | 81 provenance-tracked replay files retain their hashes. V13 remains incomplete with its original negative results and memory error. Forecasting endpoint returns HTTP 200. |
| Workspace | Active metagame checkout and empty normal index preserved; post-experiment research changes confined to mochi/. Website modifications confined to mochi/. |
| Delivery | README, final assessment, reproducible commands and past.dev/Tinker article draft published. |

## Limits

- Fixed-layout simulation, four final cases, no hardware validation.
- A training-derived static policy nearly matches the selected model and is slightly faster; 46/48 categorical decisions match. No meaningful adaptive-selection advantage established.
- Arm joint travel per recovery rose from 5.54 to 6.93 radians, and torso roll RMS rose slightly. Fewer steps does not establish smoother motion by every measure.
- Tinker updates the shared LoRA controller-selection model, not the native gait network or low-level controller library.
- Memory/search API use is verified; causal performance benefit was not isolated by ablation.

Verification reads existing evidence only. Publication added no optimizer updates, policy inference or physical rollouts. Browser checks distinguish recorded physical time from rendering and remote service latency.
