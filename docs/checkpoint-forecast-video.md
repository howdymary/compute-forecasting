# Synchronized checkpoints and price forecasts

A 30-second, 1920×1080 H.264 film showing what the operational soft-target seed-17 selector actually chose at updates 0, 20, 50 and 100.

One continuous cream composition keeps two panels visible. Approximately 60% of the width is assigned to the price case; the six-run learning chart remains alongside it. A shared checkpoint number, cobalt operational run and current-checkpoint marker link the views. Original development-selected rings remain visible.

## What is plotted

The price panel uses the existing retrospectively chosen case:

- afhubbard.hyperscaler_spot.A100_SXM_80GB.spot.median
- Origin August 15, 2026.
- USD per GPU-hour; advertised hyperscaler spot median, with the source's pooled region/provider contract.
- Actual +1, +3 and +7-day q10/q50/q90 forecasts and matching archived outcomes.
- Visible history August 2–15; complete retained input history remains in the source replay.
- Fixed price axis 1.72–2.00 and date axis August 2–22.

The learning panel retains all six SFT runs. Three exactly identical hard-target paths are grouped explicitly. Other coincident segments keep the same coordinates. Rings mark the original development-selected checkpoints.

Tinker trained the experiment selector. The selected numerical method produced each price-forecast distribution. This is a saved-result replay; no model sampling, retraining or numerical fitting occurs.

## Distinct score scopes

| Saved update | Chosen numerical method | Illustrated case pinball, 3 horizons | Aggregate development pinball, 18 cells |
| ---: | --- | ---: | ---: |
| 0 | last_value_empirical | 0.021680288077777807 | 0.01482266973639115 |
| 20 | seasonal_naive | 0.017643885600000023 | 0.018112047819066727 |
| 50 | last_value_empirical | 0.021680288077777807 | 0.011253870422938421 |
| 100 | ewma_0.2 | 0.008459085340716724 | 0.009050336633428241 |

Case and aggregate scores can move in opposite directions. At update 20 the case improves while aggregate development loss worsens. At update 50 the aggregate improves while the case returns to its starting forecast. The final checkpoint lowers loss for this illustrative case.

This example was selected retrospectively for visual explanation; it is not a registered endpoint or evidence for every series. The learning aggregate has six tasks and three dependent development dates. The separate 22.8% retrospective evaluation gain is not plotted. The 38.9% development reduction is not attached to the case. Prospective accuracy and incremental RL gains remain unestablished.

## Motion and source verification

The price panel holds the latest measured checkpoint until t=6.0, 11.7 or 17.8 seconds, then crossfades for 0.45 seconds between two actual saved forecast layers. Prediction coordinates never morph. Metric labels always take a verified checkpoint value. History, archived outcomes, axes and camera position remain fixed.

Straight joins guide the eye between the three issued horizons and between measured learning checkpoints. They do not represent independently evaluated daily forecasts or intermediate optimizer-update scores. Missing historical dates split paths.

Every checkpoint/model/case association is independently checked against the immutable hash-verified archived development traces. All 12 forecast-cell pinball losses and widths are reconstructed, and all 36 quantile values are checked for positivity and order. The existing source permission and hardware, instrument, pricing tier, statistic and units must agree. The original numerical-file hashes and attribution are retained.

Each of the 900 rendered frames verifies its checkpoint index, model identity, case score, aggregate score, crossfade weights and highlighted learning coordinate. Frozen measured SVG geometry is checked for mutation on every frame. Additional checks cover 24 learning values, six original selections, history gaps, text clipping, direct-label overlap, font loading, codec, duration, resolution, frame count, fast-start atom ordering, public-byte hash and HTTP range playback.

## Reproduce remotely

Run **Render synchronized checkpoint price forecasts** on compute-observatory. The rendering command is:

~~~sh
python -m compute_forecast.record_checkpoint_forecasts
~~~

For a credential-free render on a remote runner, install the pinned dependencies and FFmpeg as in [.github/workflows/record-checkpoint-forecasts.yml](../.github/workflows/record-checkpoint-forecasts.yml), then run:

~~~sh
python -m compute_forecast.record_checkpoint_forecasts --no-publish
~~~

The workflow reuses the existing learning input verifier, deterministic PNG-to-FFmpeg pipeline, append-only GitHub publisher and public media route. It does not modify the application or frozen studies.

Artifacts: results/terminal-v10/runs/<workflow-run>/checkpoint-forecast/. Each version contains synchronized-data.json, validation.json, manifest.json, publication.json, caption.txt, replay.html, poster.png, contact-sheet.png, motion-strip.png and the notebook font's OFL license. MP4 bytes are stored behind the existing public media route.

The contact sheet covers all four checkpoint states and the final held composition. The motion strip samples actual encoded frames across all three price crossfades. Full-resolution extracted frames remain in the Actions artifact for inspection.

Sources: [checkpoint registry](campaign-v2-checkpoints.json), [campaign findings](campaign-v2-findings.md), [learning film](learning-curve-video.md), and the hash-verified price replay at results/terminal-v10/runs/43815591384/training-video/.

Attribution: Hubbard, A. (2026). GPU Price Tracker dataset, https://github.com/alex-hubbard/gpu_price_tracker (CC BY 4.0), via the Pacific compilation. Forecast overlays and cropped historical view are derived displays; original source and permission records remain in the data artifact.
