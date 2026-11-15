# Prospective market-signal study v6

The question is whether origin-available news, infrastructure and BLS features improve future H100/A100 advertised-rental forecasts beyond matched price-only controls.

**The experiment is running; prospective improvement is not yet established.**

## Actual new work

The [registered configuration](../configs/prospective-signals-v6.json) was committed at [0f1c55f](https://github.com/howdymary/compute-forecasting/commit/0f1c55f3852fc973f9dec1a787902605e6400901), before the first capture and forecast issuance. The [successful initial execution](https://github.com/howdymary/compute-forecasting/actions/runs/43763941660) retained one new price day, froze four exact provider contracts, captured primary evidence and BLS, and issued 48 cold-start reference rows at 2026-11-15 21:30:21 UTC.

The original official export, v1/v2/v4 studies, previous selector panel and November 23 gate are unchanged. New source IDs never imply identity with competition targets.

## Source and cohort

[GPU Rental Prices](https://gpurentalprices.com/data) explicitly licenses its published CSV/JSON data CC BY 4.0. The adapter reads only [today's snapshot](https://gpurentalprices.com/api/latest.json) and [collection health](https://gpurentalprices.com/api/health.json), never historical-price endpoints. Selected numeric derivatives retain credit, source links and input hashes. Full source bodies remain private.

The November 15 check verified these frozen contracts:

| Contract | Advertised USD / GPU-hour | Node size |
| --- | ---: | --- |
| Lambda A100 PCIe 40GB, on-demand | 1.99 | 1 GPU |
| Lambda A100 PCIe 40GB, on-demand | 1.99 | 2 GPUs |
| Lambda H100 PCIe 80GB, on-demand | 3.79 | 1 GPU |
| HyperAI H100 PCIe 80GB, on-demand | 1.80 | Unreported |

The price-independent selection rule chooses the first two lexicographic exact contracts in each GPU family. This is four contracts from two providers, not four independent markets. Regions are unreported. CPU/node/instance metadata enters identity where supplied. A missing or changed contract remains missing; no replacement series is stitched in.

Each selected provider check occurred November 15 around 08:47 UTC. A recently downloaded stale quote is excluded, and provider failures remain visible. A published quote does not establish actually rentable capacity.

GetDeploying's freely licensed export is weekly and differs from its API snapshots. It is documented as a source opportunity, not substituted for daily targets. Protected November 7–13 competition outcomes were not downloaded.

## Point-in-time signal groups

- **News:** official announcement count, price-announcement count and evidence age.
- **Infrastructure:** capacity-plan and hardware-announcement counts. Verified operational capacity is missing until separately supported; plans are not converted into delivered GPUs.
- **BLS:** electricity-distribution PPI PCU221122221122, its latest observed monthly change and age since a new period was first retained.

Exa performs bounded primary-source discovery. Direct primary-page metadata must verify publication time before an event enters predictive counts. Three of the initial six discovered pages passed this screen; the others remain explicitly excluded. Date-only publication is conservatively treated as the end of its UTC day.

The initial BLS vintage has October 2026 index 198.898 and September 209.270, both preliminary. This is an index, not USD/kWh. Availability begins at actual retrieval. Older values returned today do not become invented historical release vintages.

Every response has retrieval time, URL, byte/content hash and revision identity. Existing vintages are preserved. The [BLS API](https://www.bls.gov/developers/api_signature_v2.htm) supplies current observations; it does not supply verified historical release timestamps in this response.

## Forecasting design

The primary endpoint is seven-day mean quantile pinball; one- and three-day results are secondary.

Eight feature masks form the complete 2×2×2 design: news, infrastructure and BLS present/absent. Mask000 is the price-only incumbent; mask111 contains all three groups.

Every arm uses the same fixed Ridge model on matured same-horizon log price changes, alpha10, 180-day window, training-only imputation and scaling, and missingness flags. The last eight matured examples calibrate residual quantiles without entering the weight fit. Minimums are 56 retained price days and 32 matured examples. Quantiles are positive multiplicative values. No tuning occurs on panel outcomes.

All four numerical references run the **actual unchanged Pacific starter baselines.py**, verified against SHA256 e5ed0b9f6342989a89a7e5c3a52a74654bd9eae49700ccdc82486b479e76e81c. This preserves its empirical multiplicative drift definition, seasonal behavior and insufficient-sample notes. These are new-source forecasts, not replacements for the official CSV.

Chronos remains an existing archived comparator; it is deferred from this cold-start panel until an appropriately scoped adapter/context comparison is registered. No new Chronos accuracy claim is made.

## Issuance, truth and analysis

The initial pilot uses November 15 origin and targets November16/18/22. Four contracts × four native references × three horizons produce48 rows. With one price day, intervals collapse to the reference fallback. They are explicitly uncalibrated and excluded from the signal-value test.

The primary panel has26 Sunday origins, November22,2026–May16,2027. Its cutoff is18:00UTC; issuance must finish by20:00UTC. The daily17:30UTC capture is available before that cutoff.

Training requires actual retained feature vintages. The first eligible primary origin can therefore be later than the first registered date. Missing training history is not recreated from today's pages.

Truth is the earliest retained compatible snapshot of the target observation date, with matching provider check date. Scoring unlocks only after that UTC date ends. Later revisions cannot be selected by their score.

The complete eight-arm plus drift intersection defines matched primary cells. A100/H100 cohorts, failures, coverage counts, interval widths and zero-denominator skills remain explicit. Flat prices are retained.

Interim outcomes are descriptive. Final inference waits until May24,2027UTC and at least16 eligible origins. A fixed four-origin moving-block bootstrap uses2,000 replicates and seed17. Resampling respects cell weights within origin clusters; correlated regimes remain a limitation.

Individual group comparisons are conditional leave-one-group-out tests with Holm correction. Basic variation screens require three observed BLS periods, eight news events and five infrastructure events; these are identifiability screens, not a guarantee of adequate statistical power or causal identification.

No candidate is promoted on a development score or an interim peek. The registered primary arms remain fixed. A revised challenger needs a separately registered subsequent test.

## Execution and trust boundaries

A [separate Modal scheduler](../src/compute_forecast/signals_remote_v6.py) serializes capture, issuance and scoring at17:30/18:30UTC daily. Only registered Sundays issue primary forecasts. External work ends May25; later invocations return without collecting or running inference. Removing the deployed cron is a separate operator action.

[Modal scheduling documentation](https://modal.com/docs/guide/cron) explains why the deployed schedule is used. GitHub Actions schedules on a nondefault branch are not represented as working automation here.

Hash-addressed snapshots, commitments and score vintages are append-only under the application contract. Atomic public-index replacement preserves serving consistency. Initial commitments additionally have a nonforce GitHub anchor. Later automatic GitHub anchoring requires a separately configured persistent publishing credential; provider logs and public hash artifacts remain the current timestamp evidence. This is not a claim of a tamper-proof external ledger.

The scheduled service stores only required Exa/past.dev credentials in Modal's encrypted secret store. Private source bodies never enter public JSON.

## Memory and learning

The new researcher/scientist/skeptic loop reads real capture and readiness evidence, performs bounded checks, exchanges records through past.dev and records its next decision. Its planning choices cannot alter the frozen factorial protocol or declare success.

Four actual Tinker planning decisions are separate from weight training. Further optimization remains gated: this study has no informative new market task history or human-checked extraction labels yet. Synthetic fixtures verify implementation only.

## Reproduction

After installing the repository and its test dependencies, public readers can run:

~~~sh
python -m compute_forecast.verify_signals_v6
~~~

This verifies the registration, unchanged official CSV, four current quote identities, exact48 issued rows and pending evaluation. It needs no provider credentials or private source pack.

Numerical reference reruns require the unchanged Pacific pack. Scheduled capture needs authorized Exa/past.dev access. Model planning requires Tinker. All future outcomes are genuinely pending.

The live Signals view separates actual commitments, the registered learning comparison and evidence/memory. It draws no improvement curve before eligible paired outcomes exist.


## Completed cross-role research sequence

[Run43764698758](https://github.com/howdymary/compute-forecasting/actions/runs/43764698758) completed three ingested writers, three verified readers and five cross-role uses.

The researcher selected informative signal history as its focus. The scientist executed a readiness check: one retained day,56 required days,32 required matured pairs and zero primary scores. The skeptic emphasized that an advertised quote does not establish available capacity. The scientist then changed its next check to revision capture and inspected the actual BLS preliminary/revision warnings.

These are four bounded Tinker decisions and actual executed checks. The change followed criticism; this single sequence is not a controlled causal estimate of memory value. No learned weights or forecasting accuracy improved in this run.

[Immutable authorship, recall and task receipts](../results/signals-v6/runs/43764698758/memory.json).
