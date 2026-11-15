# The Compute Forecast notebook

The notebook edition makes the pricing SVG the first experience. Its paper, ink and handwritten annotations are a presentation layer: chart geometry, submitted quantiles, scenario formulas and frozen model artifacts are unchanged.

## Controls and provenance

- Choose **Long-term scenarios** or **Submitted forecast**. These modes remain separate instruments.
- Move the time ruler, hover/touch a chart point or use left/right keys. A margin note explains the actual selected point.
- Adjust annual assumptions and the 12/24/36-month range. Monthly values are compounded from annual assumptions; they are not independently predicted observations. The published assumptions are shared across GPU selections, not fitted per GPU.
- **Pin this observation** captures exact values, date, units, source and all relevant assumptions. Up to three session notes are kept; a fourth replaces the oldest. Changing a rate or GPU does not rewrite an existing note. Pins persist through navigation in browser memory and clear on reload.
- Inspect **Exact values, assumptions & source** on a pin for its full numeric snapshot. Benchmark pins include the unchanged official CSV hash. A scenario pin records its starting value, annual rates and formula.
- Dollar anchors are user assumptions, not quotes. Resale stays indexed. Before-cutoff history remains unavailable while publication rights are unresolved.

Selections and expanded disclosures are preserved through interface rerenders and navigation. No server-side pin storage or new account is introduced.

## Research study notes

Research → Study notes reads /api/notebook, a pure projection of already public experimental summaries and analysis. It does not access raw offers or model APIs.

1. Interval diagnostics show pinball, empirical covered-cell counts, nominal 80% coverage and mean width on the same cells. Per-horizon/series detail is downloadable. These few dependent dates do not establish a calibration guarantee.
2. Feedback diagnostics separate changed action sequences, changed selected forecasters and changes in forecast loss. The final deterministic chooser still uses matured validation in every arm. Pending matched trace counts remain null rather than zero.
3. The ledger separates cached result reveals, completed optimizer updates and fresh operational calls. Equal online result budgets are not equal end-to-end cost, training expenditure or independent data.

These additions are post-hoc descriptive audits, not new tuned forecasting results. The source identities and timestamps are included in the JSON. The original v1 negative result and the expanded v2 retrospective study are explicitly different scopes.

[Peer-review matrix](notebook-peer-review.md) · [Structured sources](notebook-peer-studies.json)

## Visual system and dependencies

Warm ivory paper, deep ink, cobalt benchmark forecasts, emerald/amber scenario paths, conventional numeric typography and a self-hosted Caveat font for short annotations. Decorative underlines, note edges and brackets never displace data points or change axes. The application continues to use native HTML/CSS/JavaScript and SVG; no chart or agent framework was added.

Caveat: Copyright 2014 The Caveat Project Authors, https://github.com/googlefonts/caveat. SIL Open Font License 1.1. Unmodified variable TTF from google/fonts commit a85fc09e44c70c7159761adfdc9d5dd007792c15, Git blob f84acf2ce2d1b3329b194749530dbaec047e6df6. The matching complete license is served at /notebook-assets/OFL.txt. Font and license blobs are checked before publication; the asset receipt records SHA-256 values. Browser font loading is same-origin and does not require an external font service or relaxed CSP.

Implementation references: [MDN pointer events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events), [MDN font-face](https://developer.mozilla.org/en-US/docs/Web/CSS/@font-face), [Explorable Explanations](https://worrydream.com/ExplorableExplanations/). This interface has not undergone a controlled comprehension study.

## Remote build and verification

deploy-pricing.yml runs the full existing foundation checks, Python compilation and Node script syntax validation. It publishes only the licensed notebook assets, pricing adapter and web application; it does not change numerical code, export CSV, model training or recording assets.

validate-notebook-ui.yml runs separately after successful deployment. It repeats all pricing checks, then checks exact pinned snapshots, immutable values after changing assumptions, bounded pin retention/removal, navigation/disclosure preservation, diagnostic metrics against public reports, the licensed font blob, keyboard/touch interaction, reduced motion, API retry recovery and 1512/390/320-pixel layouts. It captures PNG screenshots only and records the source revision and diagnostic request timing.

Existing pricing and experimental UI workflows continue to run independently. Raw offers, private models, credentials and restricted content are not part of these checks or the public assets.


The first remote notebook check observed a 1.0387-second diagnostics HTTP roundtrip at source be399c5 (run 43683991615). This includes network and serving overhead and is not a CPU benchmark. Coverage is displayed with the same-cell starting-policy reference. The feedback summary distinguishes equal loss from changed action sequences. The [post-hoc improvement register](notebook-improvements.json) records hypotheses, cutoffs, acceptance criteria, negative-result interpretations and cost limits.
