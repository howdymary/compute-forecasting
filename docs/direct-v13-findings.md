# Frozen-weight sampling control v13

Additional retrospective implementation control. No new optimizer updates and no checkpoint reselection. Original v12 forecasts remain unchanged.

| Seed | Frozen update | Base7-day loss | Trained7-day loss | Trained coverage | Mean width |
| --- | ---: | ---: | ---: | ---: | ---: |
| 17 | 50 | 0.04057164 | 0.04483828 | 50.0% | 0.118278 |
| 29 | 20 | 0.03966618 | 0.04472440 | 36.4% | 0.094123 |

22 tasks,66 horizon cells,three reused dependent origins. The same fixed inference budget yields stochastic samples; arithmetic is reproducible from the retained vectors. This does not establish prospective accuracy or supplementary-signal value.

[Registered control](../configs/direct-sampling-v13.json) · [Sampling diagnosis](direct-v13-sampling-correction.md) · [Versioned results](../results/direct-v13/runs/43962711301/report.json)
