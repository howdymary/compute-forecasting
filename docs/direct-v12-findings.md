# Direct GPU-price forecasting v12 findings

Additional post-event retrospective study. Prospective improvement is not established.

Data: 326 training tasks; 20 development tasks; 22 retrospective tasks. A task contains three dependent horizon cells.

| Seed | Updates | Selected update | 7-day base loss | 7-day selected loss |
| --- | ---: | ---: | ---: | ---: |
| 17 | 100 | 50 | 0.05900519 | 0.05317809 |
| 29 | 100 | 20 | 0.06167626 | 0.06259394 |

Different collectors, configurations and instruments retain separate IDs. The primary loss is USD-per-GPU-hour quantile pinball; lower is better. Source windows overlap and the three evaluation origins are dependent.

Checkpoint selection uses development only and includes the unadapted base at update zero. A selected base means trained checkpoints did not earn promotion. Additional RL is not established.

Supplementary evidence accuracy is not established. Current source access and archived-vintage eligibility are separate from forecasting value.

[Protocol](../configs/direct-forecast-v12.json) · [Methods](direct-forecast-v12.md) · [Public artifacts](../results/direct-v12/README.md)

## Uncertainty and numerical controls

Seed 17: selected-model seven-day coverage 18.2%, mean interval width 0.00000000 USD/GPU-hour. Native drift seven-day loss 0.04647507; empirical-last-value loss 0.04528235.
Seed 29: selected-model seven-day coverage 18.2%, mean interval width 0.00000000 USD/GPU-hour. Native drift seven-day loss 0.04647507; empirical-last-value loss 0.04528235.

All published selected-model intervals have zero width. Repeated sampled vectors do not provide useful distributional uncertainty. Sampling-mode diagnostics are separate from this frozen accuracy comparison; no post-hoc correction has replaced these forecasts.
