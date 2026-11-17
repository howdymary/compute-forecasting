# Direct probability forecasting v18

completed. CE and CRPS use the same registered output levels and matched chronological data.

Retrospective seven-day results; three dependent dates. Prospective improvement is not established.

| Method | Seven-day pinball | Median MAE | CRPS | Coverage | Width |
|---|---:|---:|---:|---:|---:|
| Untuned probability model | 0.0648488355 | 0.130428 | 0.126369 | 24.00% | 0.004512 |
| CE trained, 3 seeds | 0.0538580897 | 0.130986 | 0.111837 | 53.33% | 0.240773 |
| CRPS trained, 3 seeds | 0.0582795529 | 0.131048 | 0.117502 | 45.33% | 0.146152 |
| Native last_value | 0.0652140000 | 0.130428 | not retained | 24.00% | 0.000000 |
| Native last_value_empirical | 0.0622536604 | 0.130428 | not retained | 40.00% | 0.230523 |
| Native drift | 0.0627619120 | 0.133478 | not retained | 40.00% | 0.230523 |
| Native seasonal_naive | 0.0622536604 | 0.130428 | not retained | 40.00% | 0.230523 |

## Previous untuned JSON interface

This diagnostic uses only exact retained matches: six seven-day cases on one October25 origin per seed. It is not the 25-case full-cohort comparison. Provider base-weight revisions are unrecorded, and the older interface uses retained Monte Carlo forecasts.

| Objective / seed | Seven-day cases | Trained probability pinball | Untuned JSON pinball | Trained minus JSON |
|---|---:|---:|---:|---:|
| ce / 17 | 6 | 0.0525823910 | 0.0521758492 | +0.0004065418 |
| ce / 29 | 6 | 0.0451462049 | 0.0548500140 | -0.0097038090 |
| ce / 43 | 6 | 0.0498009206 | 0.0546688083 | -0.0048678877 |
| crps / 17 | 6 | 0.0528749886 | 0.0521758492 | +0.0006991394 |
| crps / 29 | 6 | 0.0535194124 | 0.0548500140 | -0.0013306016 |
| crps / 43 | 6 | 0.0559610486 | 0.0546688083 | +0.0012922402 |

A gain on the full cohort against the new untuned interface or numerical controls does not establish superiority over this older interface. Retained prediction differences are descriptive; no resampling or reselection was performed.

## Interpretation

All comparisons below are descriptive, retrospective and conditional on this registered cohort.
CE: trained-minus-untuned seven-day pinball -0.0109907458; difference from the best official reference -0.0083955707; median-MAE difference +0.000558. 3/3 seeds improved over the common untuned model.
CRPS: trained-minus-untuned seven-day pinball -0.0065692826; difference from the best official reference -0.0039741075; median-MAE difference +0.000620. 3/3 seeds improved over the common untuned model.

Probabilistic score improvement does not establish improved median predictions, every-case improvement, an objective's universal superiority, or prospective accuracy. Original JSON forecasts use a separate six-case seven-day subset; Chronos has no matched origin.

Actual optimizer updates including API preflight: 756. Complete final runs: 6/6.

All candidate runs, original selections, failures and probability vectors are retained in the versioned results folder. Learning rates and checkpoints are selected on development fields only. The original v14 JSON comparison uses a separate exact-match subset.

Provider charges are unavailable. This is a direct price-distribution model, separate from the earlier experiment selector.
