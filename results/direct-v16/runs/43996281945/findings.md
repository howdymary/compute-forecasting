# Diagnosis of the frozen direct-forecasting comparison

All six saved results were independently reconstructed. Across six paired runs on the same22 seven-day cases, mean untuned loss was0.0409712518; selected SFT loss was0.0462887607, a12.98% increase.

Three reused dates remain three market origins;132 repeated cells are not132 independent forecasts.

| Arm | Seed | Selected | Untuned loss | SFT loss | Difference | Median MAE change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
|price_only|17|50|0.04041970|0.04779280|0.00737310|0.00342931|
|price_only|29|50|0.04093738|0.04571006|0.00477268|-0.00446570|
|price_only|43|20|0.04164530|0.04554101|0.00389571|-0.00087195|
|price_evidence|17|50|0.04100851|0.04789235|0.00688384|0.01052186|
|price_evidence|29|50|0.04253107|0.04580366|0.00327259|-0.00181777|
|price_evidence|43|50|0.03928555|0.04499269|0.00570714|-0.00000444|

## Exact primary-loss contributions

Each contribution is the subgroup's summed trained-minus-base loss divided by all132 repeated primary cells. Contributions within each grouping sum to the aggregate difference.

| Collector | Repeated cells | Mean difference | Weighted contribution |
| --- | ---: | ---: | ---: |
|afhubbard|36|0.00434661|0.00118544|
|fastgpu_daily|72|0.00727981|0.00397081|
|gpurentalprices|24|0.00088696|0.00016127|

| Quantile | Contribution after the scorer's one-third quantile weighting |
| --- | ---: |
|q10|0.0024526431|
|q50|0.0001886475|
|q90|0.0026762182|

## Interpretation boundaries

This is an artifact-based diagnosis, not a new model comparison on untouched dates. Conditional sample bootstraps condition on the retained vectors and fixed outcomes; they do not estimate market-population uncertainty. No inference or optimizer updates were requested. Source-mix, representation and objective explanations require interventions before causal attribution.

Raw malformed completions and the original tokenizer commit were not retained. Those limitations cannot be repaired retrospectively by inventing missing records.
