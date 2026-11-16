# Price history versus price plus BLS

Study status: partial. 2/6 matched training runs published.

The model directly predicts1/3/7-day price changes. Supplementary inputs are original archived electricity-distribution PPI features. News and infrastructure features are not in this comparison.

| Arm | Seed | Updates | Selected | Base7-day loss | Selected7-day loss | Coverage | Width |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Price history | 17 | 100 | 50 | 0.04041970 | 0.04779280 | 45.5% | 0.124047 |
| Price + BLS | 17 | 100 | 50 | 0.04100851 | 0.04789235 | 45.5% | 0.122746 |

326 overlapping training tasks;20 development tasks;22 retrospective tasks,66 horizon cells and3 reused dependent origins. Seed runs replicate the same market outcomes.

Checkpoint selection uses development only. All stochastic samples and failed outputs remain retained. A positive BLS effect is not assumed.

Prospective improvement from supplementary evidence is not established.

[Methods](evidence-v14.md) · [Protocol](../configs/direct-evidence-v14-final.json) · [Artifacts](../results/evidence-v14/README.md)

## Matched effect of the BLS input block

Negative differences favor price+BLS. These are additional retrospective comparisons, not future accuracy.

| Seed | BLS minus price7-day loss | Matched7-day cells |
| --- | ---: | ---: |
| 17 | 0.00009955 | 22 |

Mean across1 paired seed runs: 0.00009955. Descriptive origin-level difference range: -0.00172555 to0.00343616. The same market outcomes recur across seeds.

- 2026-10-11: -0.00019522 BLS-minus-price seven-day loss, averaged over available paired seeds.
- 2026-10-18: -0.00172555 BLS-minus-price seven-day loss, averaged over available paired seeds.
- 2026-10-25: 0.00343616 BLS-minus-price seven-day loss, averaged over available paired seeds.

## Strong numerical references

| Reference |7-day loss | Coverage | Width |
| --- | ---: | ---: | ---: |
| drift | 0.04647507 | 50.0% | 0.203226 |
| last_value | 0.05009091 | 27.3% | 0.000000 |
| last_value_empirical | 0.04528235 | 50.0% | 0.203226 |
| seasonal_naive | 0.04528235 | 50.0% | 0.203226 |
