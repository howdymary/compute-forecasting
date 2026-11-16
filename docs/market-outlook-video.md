# Price-led outlook film and interactive figure

Updated 16 November 2026, after the event. This is a presentation and provenance release, not a new model study.

The figure answers the market question first: what happened to the selected GPU rental price, what was actually submitted, and which longer-term outcomes depend on assumptions? Training diagnostics answer a different question: how did the learned experiment selector change its decisions?

## Chart justification

| Chart | Question and encoding | Evidence and supported conclusion | Boundary and useful decision | Placement |
| --- | --- | --- | --- | --- |
| History with archived quantiles | Calendar date versus USD/GPU-hour. Ink marks observations; cobalt marks actual q10/q50/q90; a vertical line marks the origin. The shaded polygon and dashed connections guide the eye between three issued horizons. | 234 licensed daily medians for the exact Hubbard A100 SXM 80GB hyperscaler-spot series, plus its unchanged Nov 6 export. Shows historical context, flat median and widening submitted quantile range. | These are posted offers with a changing provider mix, not trades, a fixed-contract index, available capacity or a live quote. Nominal q10–q90 does not prove achieved 80% coverage. Helps inspect a particular price instrument and a near-term budget range. | Hero. Full history, then an explicit origin close-up. |
| Conditional rental paths | Months since a dated dollar anchor versus USD/GPU-hour. Emerald, cobalt and amber identify named annual assumptions. No shaded probability envelope. | Published -35%, -15%, +5% annual assumptions, compounded from the matching $1.8818 Nov 6 observation. Shows sensitivity at 12, 24 and 36 months. | Annual changes are assumptions, not estimated coefficients or independently predicted monthly observations. Contract survival is conditional. Helps stress a procurement or lease assumption; does not establish a likely future price. | Separate mode with new axes and a persistent scenario label. |
| Saved-checkpoint price replay | Calendar date versus price. Four actual selected forecast distributions; amber squares are archived August outcomes. Same axes at every checkpoint. | A100 SXM 80GB, Aug 15 illustrative development case; actual configurations selected at updates 0/20/50/100. Separate case-level pinball readout. | Retrospectively chosen illustration, not a representative or prospective endpoint. Tinker trained the selector; numerical methods produced prices. Helps explain the mechanism behind a changed research decision. | Supporting research chapter. Never spliced into November history. |
| Six-run learning curves | Actual optimizer updates versus aggregate development pinball. Shared paths preserve exact overlaps; rings mark original development selections. | 24 saved checkpoints, six SFT runs, six tasks / 18 cells / three reused dates. Operational soft/17 receives emphasis; hard seeds are explicitly grouped. | Development improvement does not establish future accuracy. The update-20 regression and update-50 plateau remain. Helps select/check training checkpoints, not decide where GPU prices will go. | Secondary to the price panel. |
| Matched loss/contribution comparison | Method or cohort versus paired loss difference, with matched cell counts. | Existing Research artifacts, with v1/v2 and numerical-grid/selector scopes kept separate. | Different targets and denominators cannot share a leaderboard. Helps locate which cases contributed to a result. | Existing Research view, outside this film. |
| Coverage and interval width | Coverage shown together with width and denominators, preferably by horizon. | Existing frozen diagnostics. | A wider interval can increase coverage without improving pinball. Three dependent dates do not establish population calibration. Helps diagnose uncertainty quality. | Existing Research view, outside this film. |
| Evidence/memory timeline and resource accounting | Dated records and actual decisions, with authorship; executions and optimizer counts remain separate. | Existing source-bound research traces and provider receipts. | Process activity, cross-agent recall and credits consumed do not prove forecasting gain. Helps audit reproducibility and causal claims about feedback. | Research/Methods, outside this film. |

## Established practice: five primary references

There is no verified universal formal chart standard for this objective. The following are documented conventions and useful precedents; the final composition is our design judgment.

| Primary reference | What it establishes | What we adopt |
| --- | --- | --- |
| [Hyndman and Athanasopoulos, Forecasting: Principles and Practice, chapter 5](https://otexts.com/fpp3/toolbox.html), especially distributional forecasts and horizon-specific temporal cross-validation | Historical series with forecast distributions are conventional; horizons require their own evaluation. The chapter includes financial-price examples. | History plus actual quantile marks; visible horizon and origin; no extrapolated precision. |
| [Bank of England, Bernanke review, 12 Apr 2024](https://www.bankofengland.co.uk/independent-evaluation-office/forecasting-for-monetary-policy-making-and-communication-at-the-bank-of-england-a-review/forecasting-for-monetary-policy-making-and-communication-at-the-bank-of-england-a-review) | Critiques fan-chart precision without quantitative grounding and recommends stronger communication of alternatives under structural uncertainty. | A simple labeled submitted quantile band rather than a decorative multi-band fan; separate conditional paths with assumptions. |
| [NGFS, scenario purpose and guidance, Jan 2024](https://www.ngfs.net/system/files/import/ngfs/medias/documents/ngfs_guidance_note_on_the_scenarios.pdf) | Scenario pathways explore conditional futures and are not forecasts; users must adapt them to the question. | Explicit rental scenarios without probabilities. This is a communication precedent, not evidence that climate models validate GPU-price assumptions. |
| [TensorFlow, TensorBoard scalars documentation](https://www.tensorflow.org/tensorboard/scalars_and_keras) | Loss versus training progress and comparisons across runs diagnose learning and overfitting. | Actual optimizer-update axes and all six saved SFT runs in a supporting panel; no price inference from a loss axis. |
| [Silicon Data, Silicon Index methodology](https://www.silicondata.com/products/silicon-index) | Vendor methodology standardizes per-GPU-hour units and contract characteristics before provider aggregation. It is a commercial precedent, not independent validation of our results. | Exact source/contract/units and clear population caveats. Our collector median is not represented as Silicon Data's basis-adjusted index. |

Verdict: a price-led history/quantile chart is conventional and effective for this market question. A learning chart alone is insufficient. Conditional scenarios are appropriate farther out; making them look like a calibrated fan would mislead. Cream paper, direct labels, annotations and the chapter timing are design choices, not industry mandates.

## Historical identity, rights and vintage

- Exact ID: `afhubbard.hyperscaler_spot.A100_SXM_80GB.spot.median`.
- A100 SXM 80GB; collector `afhubbard`; hyperscaler spot; median USD/GPU-hour; UTC day, all regions pooled. Catalog median provider count is three; membership can change.
- Complete approved span: Jan 12–Nov 6 2026, 234 observations over 299 calendar days, 65 missing days. Paths break at every missing day.
- Vintage: frozen Nov 9 compilation with Nov 6 cutoff. Observation dates do not establish original real-time availability.
- The existing source-specific publication decision is approved CC BY 4.0. Reuse it rather than reopening a generic license blocker.
- Attribution: Hubbard, A. (2026). GPU Price Tracker dataset. https://github.com/alex-hubbard/gpu_price_tracker (CC BY 4.0), through Pacific Machines' gpu-price-pack v0.1.1-handover compilation. Preserve [license and attribution notices](../results/value-v5/runs/43757456253/notices/).
- Input Git blob identities are locked in the render configuration. Render artifacts additionally record SHA-256 of every input and output.

No November 7–13 competition outcomes are retrieved. The August outcomes in the checkpoint case were already retained and approved.

## Horizon decision

Seven days is the longest **already-issued, audited statistical export in this composition**. This is not a universal upper limit or proof of independent seven-day forecasting skill.

| Horizon | Exact observed origin/target pairs in this archive | Saturday pairs since July 15 | Current evidence and decision |
| --- | ---: | ---: | --- |
| 1 day | 228 | 16 | Actual official quantiles; frozen short-horizon comparisons exist. |
| 3 days | 222 | 16 | Actual official quantiles; frozen short-horizon comparisons exist. |
| 7 days | 213 | 15 | Actual official quantiles; retain as the furthest archived forecast. |
| 14 days | 201 | 14 | Potential retrospective pairs only; no audited selected forecast, independent test or horizon-specific calibration here. Do not plot a new prediction. |
| 30 days | 174 | 11 | Same limitation, fewer candidate origins and greater overlap/structural risk. |
| 90 days | 120 | 4 | Very limited temporal opportunities; no validated model or interval evidence. |

These counts are descriptive availability, not executed backtests or independent sample sizes. Weekly origins still share shocks; long horizons overlap. Existing SFT development uses three dependent dates. Direct numerical and selector studies must retain their different cohorts.

Strong controls for any extension remain official last_value, last_value_empirical, multiplicative empirical-log-change drift and seasonal_naive; pinned Chronos may be reused only on matching cells. No longer-horizon control or interval-quality result is invented here. A future extension needs a registered cohort, matured-label temporal evaluation, coverage/width/failure accounting and untouched later observations.

This exact series ends Nov 6. The Nov 15 signals pilot has genuinely later individual-provider quotes, but different PCIe/on-demand contracts and one retained day. It cannot extend this SXM spot aggregate by stitching. No new statistical forecast is issued by the renderer.


### Retained interval evidence for the selected series

The report reconstructs all four official baseline controls on the exact A100 SXM80 subset: Aug 29, Sep 5 and Sep 12, three cells per horizon. It checks each cell's quantile loss, target date, coverage and width; no model is fit or selected again.

For official multiplicative drift:

| Horizon | Cells | Mean pinball | Coverage | Mean q10–q90 width, USD/GPU-hour |
| --- | ---: | ---: | ---: | ---: |
| 1 day | 3 | 0 | 100% | 0 |
| 3 days | 3 | 0.030074 | 33.3% | 0.012218 |
| 7 days | 3 | 0.020449 | 33.3% | 0.140420 |

These are tiny reused, dependent cohorts. The zero one-day reference loss makes relative skill undefined. There are no failed cells in these retained matched outputs; that is not a claim that all earlier operations succeeded. These diagnostics support showing the actual quantiles with a calibration caveat, not a claim of reliable 80% coverage or validation at longer horizons. The full four-control table and exact arithmetic are in the versioned horizon audit.

## Scenario arithmetic and economic boundaries

For month m, rental rate = $1.8818 × (1 + annual change)^(m/12). The three annual assumptions are -35%, -15%, +5%; monthly positions are explicit compounding.

At 36 months the rental indices are 27.4625, 61.4125 and 115.7625 (Nov 6 = 100). Their dollar values use the exact series anchor, not the $1.95 anchor of a different source/contract.

The separate hypothetical resale index uses annual depreciation 40%, 25%, 10%, yielding 21.6, 42.1875 and 72.9 at 36 months. It is never drawn as a rental curve or dollar resale forecast.

The broader [Pacific value model](pacific-value-v5.md) separately treats utilization, revenue realization, power/PUE, operating expenses, useful life, discounting and terminal assumptions. Those do not secretly affect the plotted rental-rate paths. The render manifest carries those assumptions with a clearly labeled A100 400W active-power assumption instead of the H100-default 700W. No new residual-value accuracy result is claimed. Capability substitution motivates scenarios but is not treated as a universal throughput-to-price conversion.

## Choreography and controls

| Source seconds | Output seconds | Meaningful state |
| --- | --- | --- |
| 0–6 | 0–3 | Full approved history and its gaps. |
| 6–10 | 3–5 | Fade through paper to the origin close-up. |
| 10–16 | 5–8 | Actual submitted +1/+3/+7 quantiles. |
| 16–22 | 8–11 | Seven-day range and explicit longer-horizon boundary. |
| 22–28 | 11–14 | Separate 12-month rental assumptions. |
| 28–34 | 14–17 | 24-month compounded values. |
| 34–40 | 17–20 | 36-month values and separate resale-index caveat. |
| 40–44 | 20–22 | Saved checkpoint zero and its actual price forecast. |
| 44–48 | 22–24 | Update 20: aggregate regression, different case outcome. |
| 48–50 | 24–25 | Update 50 returns to the starting case forecast. |
| 50–54 | 25–27 | Update 100 and its actual chosen forecast. |
| 54–60 | 27–30 | Stable final composition; limits remain visible. |

The brief update-50 revisit is unchanged data, not a headline reading state. Headline holds are 2–3 output seconds; the final composition holds for at least three. Incompatible chart modes fade through paper and never overlap different axes. Checkpoint paths on identical axes crossfade; prediction coordinates never morph. Scenario positions are calculated assumptions; the time ruler moves smoothly along the explicitly compounded paths while the selected horizon readout remains tied to its actual 12/24/36-month calculation. Each frame samples `source_time = 2 × output_time`; playback does not change market dates or optimizer counts.

The HTML figure includes opt-in 2× playback, keyboard-native chapter selection and a source-time scrubber. No autoplay; the player remains usable with reduced motion. Captures hide the controls.

## Reproduce and verify remotely

Workflow: [record-market-outlook.yml](../.github/workflows/record-market-outlook.yml).

On a hosted runner/container with the repository, pinned rendering dependencies, Chromium and FFmpeg:

~~~sh
python -m compute_forecast.record_market_outlook --verify-only
python -m compute_forecast.record_market_outlook --no-publish
~~~

Verification and rendering read public, permitted retained artifacts and require no model API credentials. Publication additionally uses GitHub and Modal credentials held as Actions secrets. No training, new numerical fitting, protected-truth retrieval or canonical publication replacement occurs.

The output is exactly 900 frames, 1920×1080, 30 fps, 30 seconds, H.264/yuv420p with fast-start. The report checks exact plotted coordinates, 234 observations, 9 official quantiles, 36 checkpoint quantiles, 24 learning checkpoints, original selections, 111 scenario calculations, timing on every frame, full encoded decode, clipping and keyboard interaction.

A versioned run publishes the MP4, preview, playable HTML, manifest and validation through existing media storage; source/provenance, full-resolution encoded PNGs, transition contact sheet, frame ledger and reproduction outputs are committed under `results/terminal-v10/runs/<run_id>/market-outlook/`.

The official forecast checksum remains `67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80`. Existing frozen studies and commitments remain unchanged. The 38.9% reduction concerns operational soft/17 aggregate development; 22.8% concerns a different retrospective evaluation and is not attached to this illustrative case. Neither proves incremental RL benefit or prospective accuracy.
