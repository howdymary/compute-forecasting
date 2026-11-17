# Direct probability forecasting v18

partial. CE and CRPS use the same registered output levels and matched chronological data.

Retrospective seven-day results; three dependent dates. Prospective improvement is not established.

| Method | Seven-day pinball | Median MAE | CRPS | Coverage | Width |
|---|---:|---:|---:|---:|---:|
| Untuned probability model | 0.0648488355 | 0.130428 | 0.126369 | 24.00% | 0.004512 |
| CE trained, 1 seeds | 0.0538834433 | 0.130431 | 0.109910 | 56.00% | 0.288249 |
| CRPS trained, 1 seeds | 0.0561228290 | 0.131628 | 0.115145 | 52.00% | 0.196729 |
| Native last_value | 0.0652140000 | 0.130428 | not retained | 24.00% | 0.000000 |
| Native last_value_empirical | 0.0622536604 | 0.130428 | not retained | 40.00% | 0.230523 |
| Native drift | 0.0627619120 | 0.133478 | not retained | 40.00% | 0.230523 |
| Native seasonal_naive | 0.0622536604 | 0.130428 | not retained | 40.00% | 0.230523 |

Actual optimizer updates including API preflight: 380. Complete final runs: 2/6.

All candidate runs, original selections, failures and probability vectors are retained in the versioned results folder. Learning rates and checkpoints are selected on development fields only. The original v14 JSON comparison uses a separate exact-match subset.

Provider charges are unavailable. This is a direct price-distribution model, separate from the earlier experiment selector.
