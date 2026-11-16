# Single H100 price canvas

The [main pricing view](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/terminal) is now a quiet cream canvas for one H100 SXM 80GB neocloud on-demand target: `gpurentalprices.neocloud_rate_card.H100_SXM_80GB.on_demand.median`.

One historical line, three actual submitted forecast points, and their actual q10–q90 band form the entire main experience. A restrained handwritten cutoff note, warm paper, serif headline and conventional numeric typography provide the visual style. The source-and-exact-values disclosure contains provenance and the official export checksum. There is no watchlist, secondary plot or scenario panel in this view.

The history window switches between the complete approved record and the last 30 calendar days. The same linear calendar and fitted dollar scale apply to historical and forecast points. Missing dates break the line. No daily forecasts are inferred between the actual 1-, 3- and 7-day points. The archived November 6 origin stays explicit; these are not current quotes. The readout supports pointer, touch, arrow keys, Home and End.

History loads independently of forecasts and has a tested retry state. Both numerical values and source identity must match the existing public pricing/history artifacts. Publication approval is verified before joining history. Post-cutoff rows and mismatched metadata are refused. The single-series layout does not change official CSV bytes or any numerical study.

[The advanced terminal](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/terminal/advanced) retains the prior watchlist and scenarios. The existing v10 recording URL with `capture=1` continues to render the original v10 terminal, so existing recordings and their reproduction flow remain separate. This release runs no recording jobs.

Handwritten annotations reuse the already self-hosted Caveat font under its [SIL OFL](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/notebook-assets/OFL.txt); plotted geometry is exact SVG. No new framework, bitmap asset or external font request is introduced.

## Verified release — 15 November 2026 PT

[Live view](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/terminal) · [Implementation](https://github.com/howdymary/mochi-demo/commit/beb3636816e8afbb78f182fa23cb46597db04c92) · [Release manifest](../results/price-canvas-v11/release-2026-11-15.json).

The [source-to-screen report](../results/price-canvas-v11/runs/43806459417/report.json) verifies the exact selected series, 89 published historical observations, three submitted forecast points, ordered quantiles, metadata/cutoff guards, genuine gaps, keyboard/touch inspection, source-disclosure preservation and history-error retry. The forecast remains usable while history is delayed or unavailable.

[Desktop PNG](../results/price-canvas-v11/runs/43806459417/1512-canvas.png) · [Mobile PNG](../results/price-canvas-v11/runs/43806459417/390-canvas.png) · [320px PNG](../results/price-canvas-v11/runs/43806459417/320-canvas.png). These rendered screenshots were inspected. All four widths passed, as did all twelve browser workflows and the 165-test deployment suite (3 skips). The initial loading-placeholder overlap was corrected and now has an explicit visibility assertion. Numerical and HTTP checks remain strict.

No recording job was launched. The prior dark terminal and its previously published film remain separate from this interface-first release.
