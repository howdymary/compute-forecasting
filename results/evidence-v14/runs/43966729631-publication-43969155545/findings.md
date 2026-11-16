# Price history versus price plus BLS

Study status: awaiting_training. 0/6 matched training runs published.

The model directly predicts1/3/7-day price changes. Supplementary inputs are original archived electricity-distribution PPI features. News and infrastructure features are not in this comparison.

| Arm | Seed | Updates | Selected | Base7-day loss | Selected7-day loss | Coverage | Width |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |

326 overlapping training tasks;20 development tasks;22 retrospective tasks,66 horizon cells and3 reused dependent origins. Seed runs replicate the same market outcomes.

Checkpoint selection uses development only. All stochastic samples and failed outputs remain retained. A positive BLS effect is not assumed.

Prospective improvement from supplementary evidence is not established.

[Methods](evidence-v14.md) · [Protocol](../configs/direct-evidence-v14-final.json) · [Artifacts](../results/evidence-v14/README.md)
