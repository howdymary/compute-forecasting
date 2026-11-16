# Price history versus price plus BLS

Study status: completed. 6/6 matched training runs published.

The model directly predicts1/3/7-day price changes. Supplementary inputs are original archived electricity-distribution PPI features. News and infrastructure features are not in this comparison.

| Arm | Seed | Updates | Selected | Base7-day loss | Selected7-day loss | Coverage | Width |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Price history | 17 | 100 | 50 | 0.04041970 | 0.04779280 | 45.5% | 0.124047 |
| Price history | 29 | 100 | 50 | 0.04093738 | 0.04571006 | 36.4% | 0.095716 |
| Price history | 43 | 100 | 20 | 0.04164530 | 0.04554101 | 31.8% | 0.087672 |
| Price + BLS | 17 | 100 | 50 | 0.04100851 | 0.04789235 | 45.5% | 0.122746 |
| Price + BLS | 29 | 100 | 50 | 0.04253107 | 0.04580366 | 45.5% | 0.101600 |
| Price + BLS | 43 | 100 | 50 | 0.03928555 | 0.04499269 | 40.9% | 0.068071 |

326 overlapping training tasks;20 development tasks;22 retrospective tasks,66 horizon cells and3 reused dependent origins. Seed runs replicate the same market outcomes.

Checkpoint selection uses development only. Valid sampled vectors and invalid-sample counts are retained. Raw malformed completions were not retained by the frozen trainer. A positive BLS effect is not assumed.

Prospective improvement from supplementary evidence is not established.

[Methods](evidence-v14.md) · [Protocol](../configs/direct-evidence-v14-final.json) · [Artifacts](../results/evidence-v14/README.md)

## Runtime status

The Actions workflow reported a runtime failure; completed results are accepted only after independent artifact reconstruction. See retained workflow status.

Seed43 price-only wrote its complete100-update result and uploaded all9 artifact files before Python exited134 during teardown. The original failed job remains visible; optimization was not repeated. [Runtime log](https://github.com/howdymary/mochi-demo/actions/runs/43966729631/job/133649491782).

## Matched effect of the BLS input block

Negative differences favor price+BLS. These are additional retrospective comparisons, not future accuracy.

| Seed | BLS minus price7-day loss | Matched7-day cells |
| --- | ---: | ---: |
| 17 | 0.00009955 | 22 |
| 29 | 0.00009360 | 22 |
| 43 | -0.00054833 | 22 |

Mean across3 paired seed runs: -0.00011839. Descriptive origin-level difference range: -0.00187790 to0.00440537. The same market outcomes recur across seeds.

- 2026-10-11: -0.00187790 BLS-minus-price seven-day loss, averaged over available paired seeds.
- 2026-10-18: -0.00177694 BLS-minus-price seven-day loss, averaged over available paired seeds.
- 2026-10-25: 0.00440537 BLS-minus-price seven-day loss, averaged over available paired seeds.

## What training accomplished

Fine-tuning increased seven-day retrospective loss versus the corresponding unadapted model in6/6 completed runs. Development checkpoint selection did not establish an out-of-sample training benefit. The tiny average BLS-input difference must be read alongside this negative result and the strong numerical controls.


## Strong numerical references

| Reference |7-day loss | Coverage | Width |
| --- | ---: | ---: | ---: |
| drift | 0.04647507 | 50.0% | 0.203226 |
| last_value | 0.05009091 | 27.3% | 0.000000 |
| last_value_empirical | 0.04528235 | 50.0% | 0.203226 |
| seasonal_naive | 0.04528235 | 50.0% | 0.203226 |
