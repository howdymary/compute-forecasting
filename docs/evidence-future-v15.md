# Frozen direct models: prospective execution

This implementation runs the unchanged [paired prospective protocol](../configs/evidence-v14-prospective.json). It adds no training, feature tuning, replacements, or retrospective evaluation periods.

## What runs

A separate Modal app, `compute-forecast-evidence-future-v15`, runs at00:03 and00:45UTC daily. Monday00:03 is inside the thirty-minute issuance window for Sunday's23:59:59UTC origin. Other ticks audit readiness or score matured outcomes. It performs no external forecasting work after March3,2027.

The first registered origin is December6,2026. The implementation permits the twelve calendar origins through February21,2027. A failed or missed origin is retained; it is not silently replaced. If fewer than twelve eligible origins complete, the registered twelve-origin primary analysis remains incomplete and any extension requires a successor registration.

GitHub Actions deploys and audits this runner on `compute-observatory`. It does not rely on GitHub cron running from a nondefault branch. The existing signals-v6 collector, its configuration and existing November23 gate remain unchanged.

## Frozen models and source data

The operational seed17 checkpoints were chosen by original development seven-day loss, not by the retrospective comparison. Both selected update50. Tinker checkpoint paths remain private; the public lock holds full path hashes, the original selection IDs, and the lock timestamp. The states are retained through March15,2027. Creating inference clients performs zero optimizer updates and saves no additional persistent checkpoint copies.

The runner reads existing immutable `/data/signals-v6/snapshots`. It does not collect duplicate quotes. It accepts only same-day provider checks captured between17:00 and19:00UTC, exact original source contract IDs, compatible GPU/contract metadata, positive USD-per-GPU-hour values, and the stated CC BY4.0 source permission. Capture time, quote time and observation day remain separate.

The first initialization capture outside that UTC window is excluded. Original source IDs use the source's existing JSON-hash convention; they are not regenerated with a different serializer. An initial adapter audit exposed that encoding mismatch, which was corrected before any forecast was issued. Failed audit versions remain public.

The registered BLS input still requires a qualified original release vintage. The latest qualified PDF period must agree with the latest period in the retained source's contemporary BLS response. A newer current API retrieval cannot replace the original release timestamp or be backdated. An absent or unqualified current original release gates both primary arms.

## Issuance and scoring

Every eligible issuance includes both frozen trained arms, both corresponding unadapted input conditions, and the four unchanged starter baselines. All eight conditions share the same eligible targets and horizons. Each model gets64 samples per task, up to1024 vectors per origin. Parent parsing, positivity, quantile extraction and last-value fallback rules apply, with failures counted.

Native baseline source bytes are checked before execution. The original numerical code, frozen study pool and official competition CSV are untouched.

The runner binds the forecast to the protocol, engine, model lock, immutable input hashes and actual issuance time. It saves a public hash-addressed artifact and a public-volume publication receipt. A receipt missing the registered deadline is excluded from prospective scoring. Quantile scoring occurs only after the end of the target UTC day and requires an actually retained compatible contract observation.

Public Modal timestamps and volume commits provide an auditable operational record. They are not independently trusted timestamps. Automated future GitHub anchoring is not configured; the initial readiness/model-lock audit is committed through GitHub Actions. This trust boundary remains explicit.

## What can be inspected

The paired-study application loads future readiness independently from its historical training and price charts. The public API exposes readiness, model-lock hashes, registration, issuance ledger and immutable forecast/evaluation artifacts. Missing sources, insufficient history, unqualified BLS vintages, missed deadlines and pending outcomes remain visible.

Tests use explicitly synthetic data to exercise source-ID corruption, wrong units, stale quotes, capture windows, complete eight-condition cohorts, duplicate rows, missing controls, changed checkpoints, issuance deadlines and outcome maturity. Synthetic values never appear as market prices.

[Methods](evidence-v14.md) · [Training findings](evidence-v14-findings.md) · [Prospective source and evaluator](../src/compute_forecast/evidence_future_v15.py) · [Remote execution](../src/compute_forecast/evidence_future_remote_v15.py) · [Live readiness API](https://howdymary--compute-forecast-evidence-v14-web.us-east.modal.run/api/evidence-future).

Prospective improvement is not yet established.

## Verified status: November 16, 2026

The [deployed readiness audit](../results/evidence-v14/audits/43977962380/prospective-readiness.json) confirms one accepted quote day, November16. The initial November15 capture was outside the registered17:00–19:00UTC window and is excluded. Twenty retained days are required for each eligible contract; no future forecasts have been issued.

The [future-only BLS qualification](../results/evidence-v14/audits/43977825560/future-bls-vintage.json) verifies the original October2026 report, published November13 at08:30 eastern. The industry221122/base12-03 row and all five month columns were checked against a separate PDF text parser on page184(one-based). October's index is198.898. The extracted-text hash and actual November16 retrieval time are retained. This record supplements only future inference; it does not change the frozen training dataset. Each later release must also pass qualification before use.

At audit time, current evidence is qualified. Issuance remains pending the first registered origin and sufficient compatible price history. Reasons associated with the preceding, unregistered November15 origin are retained separately from present evidence readiness.

[Successful prospective deployment and tests](https://github.com/howdymary/mochi-demo/actions/runs/43977962380) · [Original BLS release](https://www.bls.gov/ppi/detailed-report/ppi-detailed-report-october-2026.pdf).
