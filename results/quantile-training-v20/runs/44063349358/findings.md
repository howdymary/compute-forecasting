# Direct quantile training v20

Status: completed_pilot. Prospective improvement is not established.

Fixed equal-weight ensembles combine the three frozen v19 price-only models. They are postprocessing controls, not additional weight training. The ensemble was selected on reused development cases before the new retrospective ensemble arithmetic.

| Method | Development seven-day pinball | Exploratory seven-day pinball |
|---|---:|---:|
| quantile_average | 0.008316478349733775 | 0.014689380974901037 |
| probability_pool | 0.008025936777096825 | 0.017239911050114395 |

| Seed | Optimizer updates | Selected update | Selected retrospective pinball | Head-zero pinball | Frozen parent pinball |
|---|---:|---:|---:|---:|---:|
| 17 | 64 | 64 | 0.02287759193346648 | 0.03790730882100627 | 0.015557662085394464 |

The three internal head softmaxes encode scalar quantiles. They are not a predictive probability distribution. Quantiles are sorted during both optimization and evaluation. Head zero uses the same parent weights with this new interface; it differs from the parent categorical forecast.

Training effects are measured against head zero. Comparisons with the original parent change both representation and objective. Warm starts and development dates were already selected and reused. The retrospective comparison has 24 seven-day cases on three dependent dates and is exploratory.

All original official forecasts and studies are preserved. New future outcomes must mature under the separate registered panel before an accuracy claim. No news, BLS or availability feature effect is tested here.

Public arithmetic: run python -m compute_forecast.verify_quantile_v20 after installing the package. See docs/quantile-training-v20.md for provenance, limits and reproduction.
