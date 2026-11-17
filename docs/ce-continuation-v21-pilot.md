# Categorical continuation v21: locked seed-17 pilot

[Immutable report](../results/ce-continuation-v21/runs/44136095711/report.json) · [Execution](https://github.com/howdymary/mochi-demo/actions/runs/44136095711) · [Methods](ce-continuation-v21.md).

Report SHA-256: `3faa97688d2a272b038e6aa7f1091f32060779aef030aa59dafd6366d5a4ba30`.

## Result

Both arms completed **100 additional optimizer updates**, restoring the same parent weights and Adam state at learning rate 0.00002. Their originally selected checkpoints improved development loss but worsened loss on the reused retrospective cohort.

| Method | Selected additional update | Development 7d loss | Retrospective 7d loss | Retrospective coverage | Mean width, USD/GPU-hour | Median MAE, USD/GPU-hour |
|---|---:|---:|---:|---:|---:|---:|
| Frozen incumbent | 0 | 0.00865214 | 0.01555766 | 20/24 | 0.11702519 | 0.04233698 |
| Original-data continuation | 20 | 0.00793894 | 0.01808340 | 18/24 | 0.06719054 | 0.04690796 |
| Expanded-data continuation | 50 | 0.00818259 | 0.01842522 | 18/24 | 0.05621137 | 0.04576798 |

Original-data continuation worsened retrospective pinball by **16.23%** versus the incumbent; expanded-data continuation worsened it by **18.43%**. Expansion scored **1.89% worse** than matched original-data continuation. These are descriptive differences on 24 seven-day cells across eight groups and three previously examined, dependent dates, not estimates of future performance.

At additional update 100, development loss rose to 0.01142790 for original data and 0.01150546 for expanded data. Those checkpoints were not selected. More optimization did not monotonically improve the forecasting score.

## What the retained predictions show

All net deterioration occurs in A100 40GB cases, principally one source-defined spot-price group. A second A100 40GB group improves slightly. A100 SXM 80GB and H100 SXM 80GB have identical quantile losses to the incumbent on this small cohort; that is not evidence of improved H100 forecasting.

The 15 unchanged-price cases have zero loss difference. The nine changed-price cases account for the complete aggregate difference. Both continuations improve on October 30 but worsen on October 25 and 28.

The weighted q10/q50/q90 contributions to trained-minus-incumbent loss are:

| Continuation | q10 contribution | q50 contribution | q90 contribution | Total |
|---|---:|---:|---:|---:|
| Original data | 0.00165483 | 0.00076183 | 0.00010908 | 0.00252574 |
| Expanded data | 0.00230504 | 0.00057183 | -0.00000931 | 0.00286756 |

The intervals became narrower, covered two fewer outcomes, and central-price MAE also worsened. This supports a specific description of the failure: reduced lower-tail protection and worse central predictions on repricing cases. It does not prove a causal explanation such as overfitting, source shift or objective mismatch. Two development dates cannot establish stable checkpoint selection.

## Exposure and data

Original-data continuation presented all 942 available horizon examples, with 658 repeated presentations. Expanded-data continuation presented 1,600 distinct examples out of 11,511. Both used exactly 1,600 presentations and 100 updates. Corpus size, composition and effective passes differ as registered; this is not an isolated sample-size intervention.

No news, BLS, new providers, model architecture, calibration or reward training was added. All original tasks were preserved. Unknown provider charges remain unknown.

## Decisions and remaining work

The production incumbent remains the frozen v19 checkpoint. The registered development gate passed for both arms, so ordering seeds 29 and 43 can run under the existing limits. Their results cannot change seed 17's operational identity or original checkpoint selection.

The separately registered future comparison keeps the candidate selected by development loss: original-data continuation, additional update 20. A negative opened-period result does not silently rewrite that protocol. The incumbent, candidate and expanded arm will receive matched eligible future inputs; actual issuance and scoring remain pending.

Prospective improvement is not yet established.
