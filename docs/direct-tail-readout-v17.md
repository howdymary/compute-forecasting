# Matched frozen tail-readout diagnostic

Study: direct-tail-readout-v17. Registered after the v14 outcome analysis; all results remain post-hoc and retrospective.

Question: Can a small correction to the forecast tails, selected using development data only, reduce the observed SFT-minus-base deterioration when both models receive the same fitting budget?

The full configuration is [configs/direct-tail-readout-v17.json](../configs/direct-tail-readout-v17.json). It locks nine lower/upper log-offset multiplier pairs from {0.5, 1, 2}. The median never changes. Identity preserves exact original quantiles. No new weights, checkpoint selections, sampled model outputs or price observations are created.

Each seed/input condition has an untuned and original-development-selected SFT model. Both receive independently fitted corrections using the same 20 development cases and selection rule. The chosen corrections are then compared on the same 22 previously examined seven-day cases, ten series and three dependent origins. Difficult cases remain included. Nonfinite transformations fall back to the original forecast and count as failures.

A descriptive repair criterion was fixed before this diagnostic execution: at least half the original aggregate deterioration is recovered and the training gap improves in at least two of three origins. Passing does not establish future accuracy or a causal training mechanism. The multiplier grid was proposed after earlier results were visible.

Implementation: scripts/evaluate_tail_readout_v17.py. Run with:
~~~sh
PYTHONPATH=src python scripts/evaluate_tail_readout_v17.py
~~~
The remote workflow is “Evaluate matched frozen tail readout v17.” It requires no Tinker, Modal or data-provider credentials and makes zero model requests. The original public v14/v16 verification runs first. Output contains all development candidate scores, selected corrections, four matched model summaries, per-origin differences, every retrospective prediction, a figure and a SHA-256 manifest.

Original forecasts, official exports, v14 checkpoint selections, prospective panels and the November 23 gate are preserved. This diagnostic cannot support a claim that training improved the original forecasts. It tests whether the observed forecast-distribution problem is amenable to one bounded readout change.

[Findings](direct-v17-findings.md) · [Results](../results/direct-v17/latest.json)

## Numerical revision

The first run (44001483178) is retained but superseded: subtracting separately rounded logarithms could introduce a crossed bound when a quantile exactly equaled its median, causing avoidable identity fallbacks. Revision 2 uses the algebraically equivalent positive ratio transformation and preserves exact ties. The grid, model selection, controls and original forecasts are unchanged. Tests include source-scale tied values and both one-sided ties. This is a numerical correction, not additional tuning.
