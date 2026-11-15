# Compute Forecast v2: measured findings

All six selected SFT checkpoints lower pooled loss versus starting weights on three reused, dependent A100 dates. This is a retrospective result; it does not replace the original frozen submission.

The development-selected operational checkpoint is soft/seed 17, update 100: 0.01156980 pinball versus 0.01499533 for starting weights (22.84% lower). Agent-feedback-hidden controls tie in 5/6 SFT runs.
Three RL reports cover 99 actual optimizer updates: 0 lower loss versus their SFT parent, 3 tie and 0 increase loss. Completing updates is separate from demonstrating improvement.

The original frozen v1 SFT result remains 0.01781945 versus 0.01735406 starting (2.68% worse). Its 111-row, 37-series November 6 export remains byte-identical.

## What the experiment measures

The pack measures advertised GPU rental offers, not transactions, available capacity or hardware resale values. Original targets and the Pacific scorer are retained.
V2 training has nine eligible tasks across six dates (June 20/27, July 4/11/18/24), with every reward label ending by July 31. Development has six tasks over August 8/15/22. Selector evaluation has four tasks over August 29, September 5/12: 12 series-horizon cells, three dependent dates, A100 40GB and A100 SXM 80GB only.
These evaluation dates were previously inspected during v1 development. They are excluded from new weight updates/checkpoint selection, but are not an untouched test. The original September 27–October 25 final and restricted November 7–13 outcomes are excluded.
The full numerical-grid evaluation has 15 cells. Its scores must not be mixed with the 12-cell selector scores. A100 40GB contributes three selector cells and SXM 80GB nine; pooled SFT improvement is concentrated in SXM 80GB. SFT loss on A100 40GB is 0.00290788 versus 0.00254829 starting, about 14.1% worse.

## Matched selector comparison

All search procedures use the same 42 candidates, two common persistence starts and four additional choices. The final deterministic chooser minimizes revealed matured validation loss. The six-trial budget counts cached result reveals, not equal wall time, dollars or offline training expenditure.

| Procedure | Pinball | Skill vs last value |
| --- | ---: | ---: |
| Official last value | 0.01590833 | 0.00% |
| Starting policy | 0.01499533 | 5.74% |
| Development-selected SFT | 0.01156980 | 27.27% |
| Static, training-validation ranked | 0.01213654 | 23.71% |
| Static, exhaustive training-outcome selected | 0.01404649 | 11.70% |
| Random search, 100-seed mean | 0.01353609 | 14.91% |
| GP, original encoding | 0.01220091 | 23.30% |
| GP, complete metadata | 0.01408559 | 11.46% |
| Single forecaster selected on training: drift | 0.01326771 | 16.60% |

The exhaustive static portfolio is selected among 91,390 possibilities using training outcomes only. Its worse evaluation result is retained. The additional complete-metadata GP preserves the original kernel, acquisition, starts and budget; it is an added retrospective control, not a replacement preregistered result.

## Every training seed

| Mode / objective / seed | Actual updates | Selected update | Development loss | Evaluation loss | Reference loss |
| --- | ---: | ---: | ---: | ---: | ---: |
| sft / hard / 17 | 100 | 20 | 0.01125387 | 0.01156980 | 0.01499533 |
| sft / soft / 17 | 100 | 100 | 0.00905034 | 0.01156980 | 0.01499533 |
| sft / hard / 29 | 100 | 20 | 0.01125387 | 0.01156980 | 0.01499533 |
| sft / soft / 29 | 100 | 20 | 0.01092629 | 0.01027624 | 0.01499533 |
| sft / hard / 43 | 100 | 20 | 0.01125387 | 0.01156980 | 0.01499533 |
| sft / soft / 43 | 100 | 50 | 0.01125387 | 0.01156980 | 0.01499533 |
| rl / soft / 17 | 41 | 0 | 0.00905034 | 0.01156980 | 0.01156980 |
| rl / soft / 29 | 36 | 0 | 0.01092629 | 0.01027624 | 0.01027624 |
| rl / hard / 43 | 22 | 0 | 0.01125387 | 0.01156980 | 0.01156980 |

Checkpoints are selected by development loss with earlier-update ties, including update zero. The global operational SFT choice additionally breaks ties by seed/objective. Evaluation-best seeds are not substituted.
[All evaluated checkpoint IDs, seeds, source revisions and recovery metadata](campaign-v2-checkpoints.json) are retained. IDs hash private sampler resource paths; they are not weight-content hashes. The model resources stay in the owner's account.

## RL execution and storage recovery

RL uses genuinely sampled bounded actions and logged conditional propensities. Four trajectories share a task; reward is negative subsequent training-period loss divided by a training-only scale and clipped to[-5,5]. A categorical policy-gradient objective uses their mean reward as baseline. Constant groups do not update weights; five consecutive constant groups stop training. The 60-group ceiling counts sampling iterations, separately from optimizer updates.
A training-only curriculum selects registered cases with reachable clipped-reward variation; evaluation still covers all original eligible cases. The RL amendment was fixed before its first updates, after two seed 17 SFT evaluations had been seen; it remains exploratory.
The initial clients hit Tinker's free checkpoint-storage cap after exactly ten updates/thirteen groups each for seeds 17/29; seed 43 could not start. Cleanup removed 26 temporary rollout samplers. Continuations restore the exact Adam/RNG prefixes, discard no optimizer updates and include those 13 groups in the same 60-group limit. Consumed samplers and superseded unevaluated recovery states are removed after successful use/replacement; original and evaluated models are preserved. Six redundant zero-update SFT optimizer copies were also removed after every corresponding sampler was verified; all nonzero SFT optimizer states and selected parents were preserved. [Exact retention receipt and limits](campaign-v2-retention.md). No billing settings changed.

- Seed 29 gate: Five consecutive sampled within-task groups had constant clipped reward; stopped after 36 RL optimizer updates
- Seed 43 gate: Five consecutive sampled within-task groups had constant clipped reward; stopped after 22 RL optimizer updates

RL's incremental reference is its own frozen SFT parent. A zero-update selected checkpoint means no demonstrated benefit from RL selection, even if other updates were performed.

## Feedback, evidence and criticism

The no-observation arm hides history summaries and validation scores from the agent, while retaining tested-arm IDs/budget. The final deterministic chooser continues using matured validation in every arm. A forecast-loss tie therefore concerns feedback to experiment selection, not removal of all validation.

| SFT objective / seed | Primary | Feedback hidden | Fixed critic added | Source metadata added |
| --- | ---: | ---: | ---: | ---: |
| hard / 17 | 0.01156980 | 0.01156980 | 0.01156980 | 0.01156980 |
| soft / 17 | 0.01156980 | 0.01156980 | 0.01315182 | 0.01156980 |
| hard / 29 | 0.01156980 | 0.01156980 | 0.01156980 | 0.01156980 |
| soft / 29 | 0.01027624 | 0.01082398 | 0.01479314 | 0.01333005 |
| hard / 43 | 0.01156980 | 0.01156980 | 0.01156980 | 0.01156980 |
| soft / 43 | 0.01156980 | 0.01156980 | 0.01156980 | 0.01156980 |

Action sequences can change while the selected forecaster/loss stays the same. Added evidence is a fixed source-metadata packet; its negative effects also involve inference-time prompt shift and do not establish that research evidence or criticism is universally harmful.
Training-only teacher alignment is mixed: its validation-oracle choice beats persistence on one task, ties five and worsens three; rank correlations range approximately −0.291 to 0.748. Paired-origin and leave-one-origin-out analyses are in the archive/API. These are descriptive checks across the same three dependent dates, not population confidence intervals.
Hindsight regret compares the selected loss with the best future-scoring arm among 42 after evaluation. That oracle may not be reachable under the fixed validation chooser.

## Numerical models and measurement controls

The registry has 42 configurations: official references, Ridge representations, direct autoregression, EWMA, quantile gradient boosting, convex mixtures and auxiliary-price controls. Chronos was not added. Numerical preprocessing/calibration uses permitted past data, preserves missingness and reports fallbacks.
On the separate 15-cell evaluation, tree_28_3/tree_28_7 score0.01335719 with five fallback cases; tree_56_3 scores0.01353057 without fallback; empirical persistence/drift score0.01412099. These are retrospective rows, not competition leaderboard results or replacement submissions.
Matched price-value removal keeps absolute-level/log targets, 56-day windows, alpha100, train-only imputation and original missingness flags fixed. Removing nine price predictors increases level loss from 0.02037651 to 0.02903200 and log loss from 0.02138023 to 0.03128927, roughly 42.5%/46.3%. It is a 15-cell conditional diagnostic, not an economic mechanism claim. The earlier unmatched diagnostic also changed target/anchor formulation and remains labeled separately.
Actual fit-mask auditing at 18 origins finds evaluation auxiliary imputation about 0.018% for raw composition and 3.03% for fixed basket. Repeated masks are not independent data. The original v1 finding remains mixed: best individual fixed-basket configuration, lower matched-configuration mean for target-only features.

## Operational autonomy and sources

4 completed research cycles made 24 numerical trials through 20 fresh Modal calls, with 33 verified cross-role memory reads. Repeated training-origin observations are not independent new market evidence.
Criticism of zero-loss July 24 tasks led the starting scientist to choose a non-flat July 18 task. The restored development-selected SFT policy also executed five fresh calls on July 18, made context-sensitive choices and ultimately selected empirical persistence; its alternatives did not improve the task. Different operational contexts prevent a causal trained-versus-starting comparison.
Exa supplied 40 distinct methodological searches plus one Snapshot capability probe and 76 unique URLs. Current evidence stays outside historical market inputs. Accepted Snapshot parameters do not verify historical entitlement, page/ranking vintage or numerical-data vintage. Raw bodies remain private; an initial retention failure and subsequent re-retrieval are disclosed.
past.dev records preserve authorship, IDs and required-source recall checks. Canonical authored text is used after verification or a disclosed fallback. This establishes cross-role use, not a measured memory-system accuracy gain. The skeptic is bounded deterministic code, not an independently trained researcher.

## Prospective commitment and publication

The corrected prospective manifest was issued November 15 at 02:55:42 UTC for November 16/18/22, using a nine-day-old November 6 snapshot. There are 42 predictions across 14 H100/A100 series; outcomes are pending and do not mature before the event. Numerical rows remain private pending publication review. The earlier UTC-misaligned manifest is retained as superseded.
Commitment 428296e044ca0a5c362ee5b96d9488c6fe47cd59be6a3d70000ac2c51cbf29d2 hashes the private record's sorted-key Python JSON serialization, with default separators and ensure_ascii=True, not its pretty-file bytes. See the public manifest for exact hash semantics.
The pack compilation license is described as CC BY 4.0, owner's default pending confirmation, with upstream terms unresolved. Aggregation does not establish redistribution permission. Raw offers, restricted excerpts, private resources and credentials stay private.
Provider/configuration normalization is established practice: [Silicon Data](https://www.silicondata.com/products/silicon-index) and [SemiAnalysis](https://semianalysis.com/gpu-pricing-index/). Our contribution is an inspectable empirical study, not an invention/first-benchmark claim. [Targeted primary-source related-work review](campaign-v2-related-work.md) places the study alongside earlier cloud-price forecasting, learned experiment selection and agent benchmarks. A frozen data vintage and pretrained-model contamination remain limitations.

## Runtime, cost and verification

The numerical stage ran 18 origins and 756 method-origin results in 541.215 wall seconds, about 1.996 origins/minute. Function durations sum to 41.04 minutes. This includes stage cold-start/client overhead and does not establish serial speedup or GPU utilization.
Costs below are provider-reported estimates before credits where available. They can lag and do not establish remaining balances; unknown is not zero.

- tinker: USD 16.22596422; status provider_receipt_partial.
- modal: USD 1.00634482; status provider_receipt_partial.
- exa: USD 0.412; status retained_request_receipts.

See [the complete usage/provenance JSON](campaign-v2-final-status.json) for attribution scope, timestamps and receipt counts. SDK retry/failure totals are not completely instrumented; memory HTTP statuses and engineering failures remain in traces/Actions.
The measured finalizer verified protected source blobs, all nine reports, the unchanged official CSV, real API values, desktop/mobile layouts, keyboard focus, reduced motion and outage/retry recovery. PNGs only; no recording job was run.

[Download the immutable derived archive](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/experimental/downloads/43677783872.zip). ZIP SHA-256: 5ec7ef997571dd925ef521895f9b950373f87d85cf8111bfe52adf5937e8c3e5. It includes member hashes, all permitted reports/traces, failed prefixes, cleanup receipts, client versions and the archived CSV; raw inputs/private resources are excluded.
Failed prefixes also appear at the beginning of their resumed records. Do not count those updates twice. Independent numerical reproduction requires authorized pack access; model resources remain in the owner's account.

## Defensible public claim

Compute Forecast is an auditable GPU rental forecasting study with 42 numerical configurations, 600 SFT updates and 99 cumulative RL updates. It runs real, evidence-guided numerical research and measures trained selection against fixed/random/adaptive controls. SFT lowers loss on three reused A100 dates, while feedback value and generalization remain limited; incremental RL has 0 improving, 3 tied and 0 worsening seed results versus its SFT parents.
Automation, state-sensitive adaptation, weight learning and forecast value are separate claims. No H100 policy result, broad research-intelligence gain, calibrated long-term confidence interval or competition win is established. Long-term rental/resale curves remain explicit assumption-based scenarios.

[Remote runbook and canonical execution links](campaign-v2-reproduction.md) · [Live research view](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/experimental)
