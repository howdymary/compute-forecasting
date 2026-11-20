# Walking and arm-recovery post-training results

Tinker completed 16 optimizer updates and 96 domain-gradient calls. The declared joint improvement target was not met.

Development selection chose update 1. On four fresh scenarios it completed 0/4 sequences, with 0/4 within all quality limits. The parent completed 1/4, with 0/4 qualified. Matched qualified pairs: 0.

The target required at least 10% fewer measured steps and 15% less recovery joint travel, without lower completion or longer successful time.
Frozen source: `5cb4bf7e5f65de46b236d10b6501dac9f43fb815`. Run: `mochi-t17-44699655265`.

## Final scenarios

| Policy | Complete | Within all quality limits | Mean steps | Mean recovery travel, rad | Physical seconds |
| --- | --- | --- | --- | --- | --- |
| parent | 1/4 | 0/4 | Unavailable | Unavailable | Unavailable |
| selected | 0/4 | 0/4 | Unavailable | Unavailable | Unavailable |
| fixed | 2/4 | 2/4 | 466.00 | 3.67 | 339.15 |
| static | 2/4 | 1/4 | 453.00 | 3.45 | 325.87 |

Cost means use qualified completions only. Mean recovery travel is per recovery; the replay counter totals all recoveries. Early failures do not count as cheap successful runs.
A comparison with no matched qualified pair has no defined step, time or recovery reduction. Four scenarios in one layout do not establish performance on other desks or hardware.

## Development checkpoints

Counts 0, 1, 4, 8 and 16 are additional updates after the verified 121-update parent. Native gait weights stayed fixed. Tinker updated the shared LoRA model that chooses walking, contact and recovery controllers.

| New updates | Complete | Qualified | Falls | Forbidden contacts |
| --- | --- | --- | --- | --- |
| 0 | 2/3 | 1/3 | 0 | 1 |
| 1 | 3/3 | 1/3 | 0 | 0 |
| 4 | 2/3 | 0/3 | 1 | 0 |
| 8 | 2/3 | 0/3 | 1 | 0 |
| 16 | 2/3 | 0/3 | 1 | 0 |

All versions received the same engineered H0 clock reach, P4 laptop action and W6 globe approach. The fixed native gait, route, scene, task verifiers and quality limits were shared. Local controller engineering is recorded separately from model post-training.

## Recordings and component checks

The audit verified 23 continuous public recordings. The first frame, scenario, task order and playback speed match within each displayed pair. Failed attempts remain available.
Component diagnostics reached 24 branches; 24 passed the frozen branch criteria. Parent and selected policies used identical saved physical states. These branches are separate from the uninterrupted route recordings.

The reference states came from the fixed controller on seed 103001. Their coverage is limited to that reference trajectory. The results motivate collecting and checking the laptop-contact states reached by the learned policy.

## Resource accounting

Accounted physical attempts and stages: 223, including 77 carried attempts. Confirmed completed attempts and stages: 221.
Accounted CPU-hours: 14.886, including conservative bounds for interrupted calls and supervisors. These are budget records, not a billing receipt. Usage stayed within the authorized 224-attempt, 18-hour and 16-update limits.

## Post-test failure localization

All four selected-model attempts completed the clock and drawer and arrived at the laptop. They then failed during the laptop action: two falls and two forbidden contacts. The contact records identify the right knee against the printer output tray on seed 103001 and the left hip against the laptop on seed 103002.
The later development checkpoints also fell during the laptop action on seed 102001. These observations locate the failures; they do not isolate the physical cause of the falls. Laptop stance, force control and fixture clearance are the next controller issues to investigate. No controller was changed after the final tests were opened.


## Preserved interrupted executions

The preceding execution `mochi-t16r1-44686221838` stopped before training with `RuntimeError`. Its original ledger snapshot recorded 162 reserved physical attempts and 9.001 reserved CPU-hours. This continuation uses the same pool after the documented reconciliation of reservations against completed receipts and conservative interruption bounds. It did not open a fresh allowance. Those reservations include unfinished work and are not an invoice.

This continuation reused 3 historical parent-prefix states and measured new alternatives from their recorded physical snapshots. New collection uses exact snapshots between training stages. The displayed evaluations are uninterrupted physical episodes.

The starting budget includes the interrupted R1 stages, supervisor bounds and local controller probes. Two unfinished calls remain charged at full timeout bounds. No previous resource counter was reset.

Recovery examples can retain an already good parent choice. Only measured physical differences establish an improvement. The table reports mean joint travel per recovery; the viewer counter totals the four recoveries.


The earlier execution `mochi-t16-44669222147` has a separately preserved ledger of 154 reserved attempts and 7.103 reserved CPU-hours. It stopped before any optimizer update. Its reservations are not represented as completed work or included in the current pool.


## Variation with identical choices

The first-checkpoint probe selected the same action sequence as the parent, but used 450 steps versus 444 and 328.21 physical seconds versus 326.96. Their initial physical-state hashes match. The cause of this variation was not isolated. These differences do not establish an effect from learned action selection. Interpret small cost differences and static-policy comparisons with this limitation.


Across the three development scenarios, update 1 matched the parent's shared action prefix in 3/3 cases. Of those cases, 1 had a different completion outcome. A changed outcome before any changed selected action does not establish a benefit from learned action selection. Per-checkpoint decision comparisons are retained in the JSON audit.


## Limitations

- Four final scenarios in one fixed furnished layout. No hardware validation.
- Native gait and physical controllers remain fixed; Tinker updates shared LoRA decision weights.
- Engineering changes include home-regularized clock IK, the bounded P4 laptop force/horizon and W6 globe-leg commands. These are shared by all new checkpoints, including the parent.
- Component tests cover the fixed reference trajectory on seed 103001; they do not cover every state reached by the learned policy.
- No causal memory/search ablation. Static-policy equivalence and unchanged decisions limit adaptation claims.

The companion JSON retains per-case qualification failures, static-policy choices, confidence intervals, initial-state checks and provider activity. Search and shared memory were used in the workflow; this study did not isolate their causal effect on performance.
