# Pacific value study v5

Compute Forecast enters Pacific Direction B: a dated, source-grounded study of GPU rental prices and conditional capital economics. The short-horizon benchmark, retrospective policy studies, current evidence and long-term scenarios remain separate.

## Matching history and publication

The current official event brief explicitly grants CC BY 4.0 for the compilation. The immutable pack's DATA.md section 5 also describes shipped CC BY 4.0, MIT and Apache 2.0 sources, while its older section 5(g) retains default-pending wording. The current brief supplies the compilation grant; source-specific terms and the unresolved marketplace/third-party-aggregate caveats remain relevant.

The v5 adapter publishes 36 of 37 exact submitted target histories from the official starter's November 6 history build. Each carries its series ID, contract, units, point hash, source credit and license. The single marketplace-ask history remains withheld under its source-register owner-decision caveat. Its original forecast remains in the unchanged 111-row official export.

There are 673 files in the pack: 672 indexed members plus MANIFEST.sha256 itself. No file is missing. Archive SHA256 remains f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c.

The historical series are retrospective frozen-vintage observations, not proof of real-time availability. Missing days break chart paths. The exact submitted forecast points occur only at 1, 3 and 7 days; connecting segments do not create daily forecasts. No November 7–13 outcome was retrieved.

Independent Hubbard context retains its separate identity and earlier failed exact-match test. It is not stitched into this matching official-target adapter.

## Official control audit

The registered v5 integrity audit invokes the unmodified starter baselines and scorer on the exact 12 eligible cells already used in the v2 selector study: two A100 series, three dependent dates. This is an additional retrospective control audit and cannot select a replacement submission.

Official drift multiplies the latest value by empirical same-horizon log-change quantiles; its median change supplies drift. It is distinct from the explicitly defined additive adapter in the separate v4 prospective panel.

On these 12 cells the official report prints:
- Last value: 0.015908 pinball.
- Empirical last value: 0.013268, pooled skill 0.165990.
- Drift: 0.013268, pooled skill 0.165990.
- Seasonal naive: 0.015152, pooled skill 0.047574.

These are six-decimal scorer presentations; retained per-cell rows preserve precision. The fixed scorer excludes six Cartesian cells outside this predeclared matched cohort. Sunday's frozen scoring instead defaults omitted forecasts to last value. Baseline-zero series have undefined relative skill. The brief's 97-series examples use different dates and scopes and are not a shared leaderboard.

## Conditional long-term economics

The GPU value view links an archived per-GPU advertised quote to 24- and 36-month cashflow scenarios.

Monthly rate:
rate(m) = anchor × (1 + annual change)^(m/12).

Monthly gross revenue:
rate(m) × 730 hours × billable utilization × posted-to-realized rate factor.

Energy:
[(idle GPU W + utilization × (active−idle W) + allocated host W) / 1000] × PUE × 730 × assumed USD/kWh.

Operating cashflow subtracts fees, energy and other operating costs. Monthly discounting uses (1 + annual discount)^(m/12).

Operating PV includes months 1 through the selected horizon. The income-based residual proxy includes only later months through assumed remaining useful life, multiplied by a terminal haircut. This avoids counting the same cashflows twice.

The residual proxy is conditional income value, not an observed resale price or calibrated forecast. No current hardware resale-dollar anchor is supplied. The control defaults are explicit assumptions, including rental changes −35%, −15%, +5% annually, utilization 60%, realization 85%, fees 10%, PUE 1.2, electricity $0.12/kWh, other opex $20/month, annual discount 12%, life 48 months and haircut 30%. They are not estimates inferred from a few news articles.

Active GPU power is adjustable; 700 W H100 SXM and 400 W A100 SXM defaults are consistent with corresponding Epoch hardware reference rows. Allocated host/idle power and the system's utilization remain assumptions. TDP is not measured whole-server operating power.

The useful decision quantities are conditional rental-rate paths, operating cashflow recovery, operating break-even utilization and sensitivity to the assumptions. Acquisition financing, taxes, execution discounts and resale liquidity require additional inputs.

## Capability premium and memory

The second registered study is descriptive: compare same-collector/tier/instrument SXM80 rental medians against explicitly named precision-matched MLPerf-based contexts. Provider populations are not pair-matched. Capability ratios vary by workload and cannot universally convert GPU prices.

The researcher, scientist and skeptic are bounded model-driven roles with separate identities and contexts. They write facts, experiment results and criticism to past.dev; other roles recall and consume those records. Exact numeric payloads are resolved by a verified returned record ID. A canonical fallback is disclosed and not counted as a successful memory recall.

past.dev holds authored semantic evidence and criticism. Immutable GitHub JSON holds numerical results, configurations, provenance and memory receipts. Markdown explains those artifacts. Private Modal storage retains original evidence bodies and private resources. Numerical tools remain the scoring authority.

The current research namespace never supplies evidence to the archived November 6 forecaster. A changed interpretation is not a learned-weight update or forecasting improvement. Existing negative v1, mixed v2, null RL and v4 evidence findings remain public.

## Reproduction and validation

After installing the unchanged pack's starter requirements, one command reproduces the official CSV without account credentials:

~~~sh
python -m compute_forecast.reproduce_pacific_v5 --pack /path/to/gpu-price-pack-v0.1.1-handover --out /path/outside-pack/reproduction
~~~

The command verifies all 672 indexed files, writes outside the pack, invokes the original starter and checks the exact forecast SHA256:
67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80.

A fresh numerical run still requires access to the pack; original trained samplers need authorized model access. New training remains gated on informative task coverage. All future commitments and their maturity gates remain unchanged.

The source registry, ATTRIBUTION.md and applicable licenses accompany public data. MLPerf is a trademark of MLCommons Association. Derived ladder ratios are not official or verified MLCommons results. No blanket project code license is newly granted.
