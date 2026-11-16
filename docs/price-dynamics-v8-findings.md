# Price dynamics v8 — measured findings

Post-event study, registered before execution. Source: [configuration](../configs/price-dynamics-v8.json), [immutable measured artifact](../results/price-dynamics-v8/runs/43785185915/study.json), [successful numerical run](https://github.com/howdymary/mochi-demo/actions/runs/43785185915).

## Result

None of the new methods improved the prespecified seven-day endpoint on this retrospective cohort. Eight H100/A100 Hubbard collector medians, 13 dependent weekly origins, 104 seven-day cells. Across horizons, 304 eligible target cells and eight missing origin/target pairs; all eight arms/references share each eligible cell. All 2,432 published scores agree with the unchanged official scorer.

| Method | Seven-day pinball | Coverage | Mean width, USD/GPU-hour | Fallback cells |
|---|---:|---:|---:|---:|
| official_drift | 0.02034373 | 79.81% | 0.146849 | 0/104 |
| official_drift_calibrated | 0.02213526 | 86.54% | 0.201272 | 0/104 |
| pooled_change | 0.02159600 | 86.54% | 0.187122 | 0/104 |
| pooled_change_calibrated | 0.02188947 | 86.54% | 0.255259 | 0/104 |
| offer_replay | 0.02034373 | 79.81% | 0.146849 | 104/104 |
| offer_replay_calibrated | 0.02213526 | 86.54% | 0.201272 | 104/104 |
| last_value | 0.02797644 | 64.42% | 0.000000 | 0/104 |
| last_value_empirical | 0.02026991 | 79.81% | 0.146849 | 0/104 |

Pooled changes were 6.16% worse than official drift on seven-day loss. The paired difference was +0.00125227, descriptive four-origin block-bootstrap 95% range −0.00326186 to +0.00490969. Calibrated drift was 8.81% worse; paired difference +0.00179153, range −0.00054364 to +0.00409203. These wide ranges include zero and do not establish reliable harm or benefit.

Coverage rose from 79.81% for drift to 86.54% for pooled changes and calibrated drift. Their wider intervals did not lower primary loss. Three-day calibrated drift was 2.34% better on this secondary retrospective endpoint; this does not justify switching the primary endpoint or claiming future improvement. No retrospective winner replaces the original submission.

## Why replay is not a modeling success

All E predictions used the registered drift fallback; all F predictions calibrated that fallback. Thus E=A and F=B are fallback equivalences, not evidence that replay works.

Raw offer observations have unique observation IDs, but that is not a persistent listing identity. The official daily target includes multiple snapshots. Last-per-identity medians differ on many dates, some identities omit region/SKU fields, H100 NVL has conflicting prices at the same composite identity/timestamp, and no complete-collection attestations establish that missing offers are market exits. These gates are retained rather than forcing a different target.

One initial raw-target audit has 27 scalar-rounding discrepancies for A100 40GB spot. A separate diagnostic compares Python scalar and NumPy vector rounding; it does not change original forecasts, gates or scores. See the versioned rounding artifact once published. All discrepancies remain inspectable.

## Future evidence

A separate aggregate panel uses independent source IDs and preserves all original prospective commitments, signals-v6 and the November 23 gate. Initial metadata listing ends November 8; no protected November 7–13 object was downloaded. No qualifying November 16-or-later observations were available, no future forecast was issued, and no accuracy outcome is established.

The [future protocol](../configs/price-dynamics-v8-future.json) extends the initial placeholder endpoint to March 28 before any issuance: a 56-observation warmup beginning November 16 otherwise permits too few weekly origins. Fixed analysis is April 6, with at least eight eligible weekly origins. Daily shadow commitments supply genuinely issued calibration errors; only Sunday-origin commitments enter the primary panel. Unknown or incompatible truth remains missing.

## News measurement and shared memory

The separate evidence capture returned 24 Exa items at its 24-item cap and 20 items from one NVIDIA RSS document. The search is saturated and its market-wide recall is unknown. RSS coverage is finite and has no declared pagination. Metadata is dated and hashed; unresolved publication/effective dates, operational status, contract, SKU or quantities are not invented. URL duplicate handling does not establish global event deduplication. These records are current research, outside the six-arm price-only experiment and frozen signals-v6 features. BLS vintages are unchanged.

The three bounded deterministic researcher/scientist/skeptic roles wrote four records and completed four cross-role recalls. A required source ID was verified in the past.dev response; its exact numerical payload was resolved by that returned ID from the canonical record. This is explicit ID-based memory retrieval, not a claim that the API supplied verbatim numerical text. Unrelated namespace IDs are not published. Criticism supported retaining replay gates and withholding retrospective promotion. No accuracy benefit from memory is established.

## Reproduce publicly

On a remote hosted runner after fetching this branch:

~~~sh
python -m pip install -e .
python -m compute_forecast.verify_price_dynamics_v8 results/price-dynamics-v8/runs/43785185915/study.json
~~~

This credential-free check reconstructs all scores, cohort denominators, summaries, paired descriptive bootstrap ranges and official-export preservation. Private-input regeneration requires the unchanged authorized pack and Modal credentials. See [methods and peer attribution](price-dynamics-v8.md).

Preparation took 229.24 seconds. The three horizon workers took 3.40, 4.87, 5.84 seconds, in parallel. No optimizer updates were launched. Modal provider cost was not reported and remains unknown; Exa reported $0.021 for the capture. No credits or billing settings were changed.

## Supported public claim

We implemented and audited three peer-inspired forecasting mechanisms under matched, fixed controls, reproduced every published score with the official scorer, and retained negative results and failed replay gates. The experiment explains why wider or more complex forecasts need not improve loss. Prospective improvement is not yet established.
