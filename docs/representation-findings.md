# Frozen representation findings

[Actual aggregation and metadata verification](https://github.com/howdymary/compute-forecasting/actions/runs/43656330831) · [Original frozen numerical run](https://github.com/howdymary/compute-forecasting/actions/runs/43653016797)

This is **descriptive aggregation after final outcomes were opened**. It retains every registered method and does not change the selected checkpoint, official forecast method or submitted CSV. The script verifies that the four reference-method aggregates exactly agree with the original final report.

Five dependent rolling origins: September 27, October 4, 11, 18 and 25, 2026. Each method has 30 scored series/horizon cells in the narrow eligible afhubbard headline daily-statistics subset. The actual final targets are **A100 40GB and A100 SXM 80GB**; no H100 series is eligible in this subset. The separate official full-catalog export covers the required H100/A100 targets. These cells and configuration comparisons are not independent replications.

## What the representation experiment found

The strongest individual configuration here was level-target Ridge with fixed-basket features, a 56-day window and alpha 1. However, **target-only features have lower mean configuration loss than fixed-basket or raw-composition features** when averaging all matched window, transform and regularization settings. A best-case configuration does not establish a universal normalization benefit.

The 56-day configurations also have lower mean loss than the 28-day configurations in this sample. These are descriptive factorial summaries, not multiplicity-adjusted significance tests or causal estimates of provider-composition effects. Temporal coverage and retrospective vintage remain substantial limitations.

| Feature representation | Mean configuration pinball ↓ | Configurations |
| --- | ---: | ---: |
| Target only | 0.01914378 | 8 |
| Fixed basket | 0.01976813 | 8 |
| Raw composition | 0.02122474 | 8 |

| Factor | Value | Mean configuration pinball ↓ | Configurations |
| --- | --- | ---: | ---: |
| Target transform | level | 0.01997127 | 12 |
| Target transform | log | 0.02011983 | 12 |
| Window | 28 days | 0.02142783 | 12 |
| Window | 56 days | 0.01866327 | 12 |
| Alpha | 1 | 0.02026410 | 12 |
| Alpha | 100 | 0.01982700 | 12 |

Marginals are arithmetic means of each configuration's pooled official pinball loss. They are not ensemble predictions. Candidate selection based on this final table would be retrospective tuning; it is not used to revise the official submission.

## Every registered method

| Configuration | Pooled pinball ↓ |
| --- | ---: |
| ridge_level_fixed_basket_56_1 | 0.01722556 |
| ridge_log_fixed_basket_56_1 | 0.01743059 |
| ridge_level_target_only_56_1 | 0.01781563 |
| ridge_log_target_only_56_1 | 0.01783487 |
| ridge_level_target_only_56_100 | 0.01798781 |
| ridge_log_target_only_56_100 | 0.01801459 |
| ridge_level_raw_56_100 | 0.01855813 |
| ridge_log_raw_56_100 | 0.01861041 |
| seasonal_naive | 0.01865518 |
| drift | 0.01928481 |
| last_value_empirical | 0.01928481 |
| ridge_level_fixed_basket_56_100 | 0.01947531 |
| ridge_log_fixed_basket_56_100 | 0.01962092 |
| ridge_level_target_only_28_1 | 0.01968518 |
| ridge_log_target_only_28_1 | 0.01973274 |
| ridge_level_raw_28_100 | 0.01979088 |
| ridge_log_raw_28_100 | 0.01998964 |
| ridge_level_fixed_basket_28_1 | 0.02010737 |
| ridge_log_fixed_basket_28_1 | 0.02048843 |
| last_value | 0.02063333 |
| ridge_level_raw_56_1 | 0.02068165 |
| ridge_log_raw_56_1 | 0.02070381 |
| ridge_level_target_only_28_100 | 0.02090443 |
| ridge_log_target_only_28_100 | 0.02117498 |
| ridge_level_fixed_basket_28_100 | 0.02174947 |
| ridge_log_fixed_basket_28_100 | 0.02204742 |
| ridge_level_raw_28_1 | 0.02567379 |
| ridge_log_raw_28_1 | 0.02578960 |

## Policy result remains separate

The starting policy scored 0.01735406, frozen SFT 0.01781945, and fixed search 0.01733246. Each policy selects among six revealed results using matured validation folds. Its future score can therefore differ from every single fixed configuration's aggregate. SFT did not improve on the starting policy here.

The official full-headline export remains the development-selected last_value_empirical method, with 111 rows. It was not replaced with the retrospective best candidate from this table.
