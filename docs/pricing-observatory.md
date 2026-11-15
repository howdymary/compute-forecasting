# GPU pricing observatory

> Historical release note. For the current product, completed campaign, publication decisions, and validation receipts, see the [current methods](research-explorer-v3.md) and [project overview](../README.md). The original observations below retain their release-time scope.

The product starts with **Explore**, then separates **Research**, **Methods** and **Downloads**. The main chart shows either the actual archived forecast or assumption-driven long-term scenarios. It does not merge those instruments into one apparent model forecast.

## Data contract

/api/pricing is a versioned public projection containing verified catalog metadata, the 111 original forecast points and the published outlook assumptions. All 37 November 6 headline series use median USD per GPU-hour. Names are formed from catalog GPU model, market class and source; identifiers remain available in details.

The metadata was read from the existing private Modal November 6 export, with the original archive hash checked. [Metadata audit](https://github.com/howdymary/compute-forecasting/actions/runs/43657301892). The public web service has no private-data mount or account credentials. The pricing publisher writes **only pricing.json**; it never rewrites the official CSV or existing assets.

Historical price values are not published. The compilation permission remains pending owner confirmation and upstream terms apply. Component metadata license labels do not resolve all compilation permissions. No history is fabricated from a forecast, and the chart marks the region before the cutoff as unavailable.

Official forecast CSV SHA-256:

~~~text
67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80
~~~

The adapter checks that exact hash, complete 37×3 coverage, origin, finite positive ordered quantiles, and agreement with the catalog. November 7–13 outcomes are not loaded. The existing numerical code and selection freeze are unchanged.

## Forecast interaction

Choose **Submitted forecast**. This is an archived November 6, 2026 forecast, not a current quote. The only generated points are horizons 1, 3 and 7 days; connecting lines are visual guides. The band spans submitted q10–q90 values and is not advertised as calibrated at this origin.

Hover, touch or use arrow keys on the chart to inspect an actual point. A floating readout keeps date, values, units and source/data type beside the cursor. The separate slider provides the same keyboard-accessible control. Three-/seven-day view controls change the displayed range without creating additional forecasts. Inspector values retain exact data behind the formatted currency display.

A comparison overlay is offered only when GPU, instrument class, tier, statistic and available configuration fields match. It draws a separately labeled median, not a combined price or an average. Source populations can still differ, so these are source-series comparisons, not matched individual provider offers. Incompatible series never enter the comparison selector.

## Scenario interaction

**Long-term scenarios** is the initial Explore mode. Dashed lines and an assumption label distinguish it from the benchmark quantile band. The chart defaults to index 100 on November 6, 2026. The 12/24/36-month controls choose the scenario window.

Published rental annual changes are −35%, −15% and +5%. Published resale annual depreciations are 40%, 25% and 10%. The three paths are named supply expansion, moderate decline and persistent constraints. Their assumptions are illustrative, not fitted coefficients or assigned probabilities.

For month m:

~~~text
rental(m) = starting value × (1 + annual rental change)^(m / 12)
resale(m) = 100 × (1 − annual depreciation)^(m / 12)
~~~

Monthly points are deterministic compounding calculations. They are not independently predicted observations. The adapter checks its 24-/36-month default endpoints against the existing outlook JSON before publishing.

Each annual slider can be adjusted independently. Crossed paths are allowed and do not become quantiles. Reset restores published annual rates, index basis and a blank dollar anchor; it preserves the selected series and view window.

Rental scenarios optionally accept a positive user-supplied starting USD/GPU-hour rate. That rate is explicitly an assumption, not an observed November 6 quote. USD display is unavailable without a valid anchor. The optional monthly spending example multiplies the selected month's scenario rate by **total billable GPU-hours per month**; it does not estimate utilization, reservation terms or cumulative spend. Resale stays indexed because no observed resale-dollar anchor is available.

## Design and architecture

The implementation retains FastAPI on Modal, the existing public Volume and dependency-free browser SVG. No database, frontend framework or chart-library dependency was added. The responsive chart computes its dimensions from its actual container, supports touch and keyboard inspection, and respects reduced-motion preferences. On narrow screens the chart comes before the detailed controls.

- pricing_audit.py: private metadata inspection, no historical values returned.
- pricing_contract.py: public schema, frozen forecast checks and compounding math.
- pricing_publish.py: verified public projection; pricing.json is the only modified data file.
- explore_ui.py: pricing-first experience; existing measured research components are reused.
- release_web.py: serves the new UI and /api/pricing; /api/release remains available.
- validate_pricing_ui.py: public browser validation and screenshots, without media recording.

The health response distinguishes the deployed UI revision from the original research data revision. Loading errors display no substitute numbers. Research loading can fail independently without disabling pricing exploration. Selections are preserved during in-page navigation.

## Research integrity

The existing 50-update Tinker SFT run and all saved results remain intact. Frozen SFT pinball is 0.01781945, starting-policy pinball 0.01735406, and fixed search 0.01733246. SFT was about 2.68% worse. The final policy evaluation contains five dependent dates and only A100 40GB/A100 SXM 80GB targets; it does not establish H100 policy performance. The separate official CSV covers the complete headline catalog, including H100/A100 targets.

Representation effects remain mixed: the strongest individual candidate used fixed-basket features, but target-only features had lower mean configuration loss across matched settings. No final-period retuning, replacement of the official submission, reinforcement-learning claim or memory-performance-gain claim is introduced.

## Remote validation and deployment

**Deploy pricing observatory** runs compilation, the existing causal tests plus pricing math/publication tests, browser-script syntax checks, frozen source-hash validation, and protected-file checks. It downloads the pinned successful metadata audit artifact, publishes the adapter, deploys on Modal, waits for the exact UI revision, and verifies public payload and official CSV hashes.

The separate **Validate pricing UI** workflow runs after a successful deployment, or manually on compute-observatory. It verifies every plotted forecast against the original CSV, scenario endpoints and custom-rate/reset behavior, dollar anchoring, resale separation, matching-series restrictions, range controls, keyboard/touch interaction, navigation preservation, all Research sections, and desktop/390px mobile overflow. It retains screenshots and a JSON validation receipt. It records no media and has no account API credentials.

All source work is direct through GitHub on compute-observatory. Builds, tests and deployment run remotely. No workstation checkout is used.

## Verified release receipts

- [Deployment, 64 tests, frozen-code guards and public hashes](https://github.com/howdymary/compute-forecasting/actions/runs/43658918382).
- [Independent desktop/mobile UI validation](https://github.com/howdymary/compute-forecasting/actions/runs/43659021941): every forecast point matched the CSV; scenario math, reset, anchoring, resale separation, comparison filtering, keyboard/touch tooltips, research navigation and 390px overflow checks passed. No page errors or failed public API requests were observed.
- Deployed interface/adapter revision: 0133224571e66fc783018f0a9cdde101f8fe5635. Documentation may advance independently of this deployed code revision.

The deployed scenario cursor/readout and archived forecast band were also visually reviewed in Safari. Historical data remains unavailable for public plotting. The 2026-11-06 forecasts are archived, and long-term paths remain user-adjustable scenarios rather than trained predictions.


## Interactive notebook edition

The [notebook guide](notebook-experience.md) documents source-bound margin notes, immutable session pins, licensed self-hosted typography and separate coverage/feedback/budget diagnostics. The [15-source peer review](notebook-peer-review.md) explains the research precedents and contribution boundary. Pricing formulas, the original CSV, publication limits and numerical selection remain unchanged.
