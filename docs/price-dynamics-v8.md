# Price dynamics v8 — post-event, separately registered study

This study does not replace the November 6 submission or change any frozen selector, signals-v6 configuration, checkpoint, or November 23 gate. Registered on November 16 UTC (November 15 after the conservative 14:00 PT deadline).

## Question and design

Can partial pooling of historical same-horizon log changes, observed-offer replay, or horizon-specific forecast-error calibration lower seven-day quantile pinball loss? One- and three-day results are secondary. Negative results and failed-method fallbacks remain counted.

The immutable configuration is [price-dynamics-v8.json](../configs/price-dynamics-v8.json). Eight declared Hubbard collector medians, 13 weekly origins from August 2 to October 25, 2026, at most 312 target cells. Eligibility uses target availability before candidate performance; missing origin/target pairs are listed. All periods are retrospective development, potentially previously opened. There is no untouched-test claim and no retrospective promotion.

| Arm | Forecaster | Calibration |
|---|---|---|
| A | Unmodified official starter drift | None |
| B | Official drift | Matured forecast errors |
| C | Partially pooled historical log changes | None |
| D | Pooled changes | Matured forecast errors |
| E | Observed-offer replay, gated | None |
| F | Observed-offer replay, gated | Matured forecast errors |

Official last-value and empirical-last-value are additional references. No new Chronos run or Tinker optimization is required. Existing training-readiness gates remain in force.

## Methods and boundaries

Pooling uses changes rather than dollar levels. Groups preserve collector, instrument, tier, GPU family and per-GPU units. Each donor series has equal weight within the pooled component. Own weight is n/(n+40); trailing window 120 days; minimum 12 changes. Two bounded state variables are the last observed step sign and position relative to the last 30 observed prices' median. Conditioning requires 12 matching changes. These components form one combined method; no individual component effect is inferred.

The official target is the rounded median of every shipped offer observation in the UTC day, including multiple snapshots. It may differ from the median of each identity's last quote. The adapter verifies both reconstructions. A snapshot observation ID is not a persistent listing identifier. Composite identities use provider, SKU, region, GPU count and memory. Missing identities, simultaneous conflicting prices or past reconstruction mismatches gate replay to official drift.

Replay uses observed same-identity historical repricing. Membership-changing transitions require explicit collection-completeness attestations; row counts alone cannot supply them. No attestation is currently assumed. Internal last-observed prices are historical state, never fabricated observed quotes. Insufficient scenarios trigger the registered fallback and stay in all denominators.

Calibration is separate for each base model and horizon. Stored past forecasts with target labels matured by the current origin supply quantile-specific signed errors. The 90-day window needs 24 errors. Add empirical q10/q50/q90 error corrections to each corresponding current quantile; floor at 1e-8, sort, and record corrections. Insufficient history retains the base forecast. This does not carry an exchangeable-conformal coverage guarantee.

Primary uncertainty is descriptive: paired differences aggregated by origin and a four-origin moving-block bootstrap, 2,000 draws, seed 17. Thirteen weekly origins and correlated series do not constitute hundreds of independent experiments. Coverage, width, changed-price outcomes, failures and denominators accompany pinball loss.

## Execution and reproduction

All work runs on hosted GitHub Actions and Modal. The unchanged authorized pack stays private; public summaries contain licensed derived rates and results with Hubbard/Pacific attribution.

On a hosted runner with the unchanged pack in the existing private Modal volume:

~~~sh
python -m compute_forecast.price_dynamics_remote_v8
~~~

The [remote workflow](../.github/workflows/price-dynamics-v8.yml) verifies tests, executes horizons in three bounded Modal workers, checks every published cell against the unmodified official scorer, and publishes append-only artifacts under results/price-dynamics-v8/runs/. Canonical configuration/engine hashes reject exact completed duplicates. Runtime is measured; unknown provider cost stays null.

Credential-free arithmetic reconstruction is provided separately. Full numerical reruns require authorized pack access and Modal credentials. No raw offer tables, private checkpoints or credentials are published.

## Future evaluation

A separate compatible-aggregate panel is registered for weekly Sunday origins November 22–March 28. The existing individual-contract signals-v6 pilots are not repurposed as collector medians. New source IDs retain their own population definition. Cutoff is Sunday 23:59:59 UTC; issuance deadline is Monday 00:30 UTC. Require 56 retained observed days and compatible fresh collection, preserve missingness, and score only truth collected after commitment and after target UTC day close. The separately registered pre-issuance duration amendment extends warmup coverage; fixed analysis April 6 requires at least eight eligible origins. Otherwise accuracy remains pending. The original prospective commitments and November 23 gate are unchanged.

## Evidence measurement

The new evidence-measurement-v8 namespace records the query, cap, cap saturation, incomplete coverage, timestamps, content hashes, source IDs and duplicate URL keys. A 24-result search is a discovery sample, not market-wide frequency. Zero retrieved items does not mean zero market events. A bounded primary-source RSS capture records its document coverage and absence of declared pagination. Event status remains unverified until evidence supports operational capacity, delivered availability or an effective price change. This capture is outside the six-arm price-only comparison; it cannot establish signal value. BLS release vintages and release-age treatment remain unchanged in signals-v6.

## Peer attribution

Ideas were informed by the public Pacific submissions:
- [Levitation](https://github.com/ianalin123/gpu-value-scientist): partial pooling, last-step and trailing-level states; news-cap and provider-composition warnings.
- [GPU Value](https://github.com/mahiuchun/gpu-price): empirical offer-transition replay.
- [Butterfly Effect](https://github.com/aaa002/butterfly-effect): state-conditioned change distributions.
- [AI Scientist Agent](https://github.com/tanmiemie/ai-scientist-agent): bounded hypothesis specifications and interval calibration.
- [GPU Value Scientist](https://github.com/yfandev/gpu-value-scientist): coverage on moving-price cases and composition diagnostics.
- [Tripathy Loop](https://github.com/lonexreb/tripathy-loop-e01-t02-gpu-value): interval calibration and rejected-mixture lessons.
- [GPU Scientist](https://github.com/swappysh/gpu-scientist): empirical change distributions and retained failures.
- [Scientist Swarm](https://github.com/andrewsiah/self-improving-scientist-swarm-public): cohort reversals and reproducibility checks.

Their reported improvements are not our results. No peer source code was copied. GitHub metadata did not identify an SPDX license at the check; this is not a grant of permission to reuse their code. See the versioned attribution record.

Data: Pacific Machines (2026), gpu-price-pack v0.1.1-handover, cutoff November 6, CC BY 4.0 compilation; Alex Hubbard GPU Price Tracker, CC BY 4.0 data. Source-specific notices remain in the existing Methods/Downloads source index. Original pack and source licenses remain authoritative.

Implementation uses Modal's documented bounded scaling and starmap interfaces: https://modal.com/docs/guide/scale and https://modal.com/docs/reference/modal.Function.

[Measured findings and limitations](price-dynamics-v8-findings.md). The initial placeholder future duration in the historical config is superseded only by the separate pre-issuance future-panel protocol; the six-arm retrospective config is unchanged.
