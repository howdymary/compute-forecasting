# Research explorer v3

## What shipped and what it establishes

The notebook now separates independently licensed historical context, the archived official forecast, and assumption-based scenarios. The Research atlas shows actual saved checkpoint trajectories, same-cohort forecast comparisons, coverage versus interval width, paired feedback traces, and separate resource units.

The expanded campaign completed six SFT runs (600 updates) and three RL runs (99 updates: 41, 36, 22). All three RL selections returned update zero, the frozen SFT parent. This is not incremental RL improvement. The operational SFT soft seed17/update100 scored 0.011569797542840439 on 12 retrospective cells versus starting 0.014995328587716763. Selection used development; choosing another run in the interface does not select a new winner. Frozen v1 remains separate and negative (SFT approximately 2.68% worse).

## Historical source-by-source publication decision

Checked 2026-11-15 UTC (2026-11-14 Pacific).

|Source|Governing evidence|Decision|
|---|---|---|
|Alex Hubbard independent S3 archive|[Explicit DATA_LICENSE at ac287bacc95f3b2ceaa97af10a50031ee0abcacf](https://raw.githubusercontent.com/alex-hubbard/gpu_price_tracker/ac287bacc95f3b2ceaa97af10a50031ee0abcacf/DATA_LICENSE), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)|Publish independently downloaded, derived **standalone context** for A100 40GB and T4. Preserve attribution, license, changes and retrieval vintage. No raw offer rows.|
|Competition compilation|[Event resources](https://iterate.inc/ai-research?welcome=true); private catalog source license labels alone are insufficient|Keep its historical values unpublished; exact compilation redistribution grant unresolved.|
|GPU Rental Prices upstream CSV|[Data page with CC BY4 terms](https://gpurentalprices.com/data)|Not used as matching benchmark history: cheapest-per-day is a different statistic from the median targets.|
|FastGPU historical compilation|[Upstream dataset](https://huggingface.co/datasets/fastgpu/cloud-gpu-prices)|No matching independently licensed historical archive verified; do not publish private compilation values.|

The independent run [43688836187](https://github.com/howdymary/compute-forecasting/actions/runs/43688836187) retrieved **436 pre-cutoff Parquet objects, 93,886,733 bytes**, and zero post-Nov6 price objects. It reconstructed daily medians from quality-ok AWS/Azure/GCP spot listings, normalizing full-SKU price by GPU count. Mixed regions and provider populations can change; this is not a fixed basket, transactions or guaranteed capacity.

Each of the two published contextual series contains **234 observed UTC dates, January12–November6, with65 missing calendar dates**. No gap filling, inferred observations or cross-contract stitching. Current retrieval of recorded snapshots does not prove historical availability or unchanged/revision-free vintages.

A predeclared exact-agreement gate (all overlap differences <=1e-6, at least30 dates) **failed**. A10040 and T4 maximum differences were approximately0.00005 USD/GPU-hour. We did not relax the gate after seeing outcomes. They may reflect precision differences, but that is not established by the audit. The published context has separate IDs, no benchmark overlay, no history-to-forecast connector, and no automatic scenario dollar anchor. A10080/SXM and V100 mappings were not verified and are excluded.

The source's DATA_LICENSE explicitly covers the S3 archive and mirrors. This grant, not public accessibility or aggregation alone, supports contextual publication. Source license SHA256: `5935a23bebd1f3add38258ebd4167ad55ca9a001bfb88e32396b36b77152f7cb`. Private compilation history remains blocked.

## One fixed additional numerical comparator

[Registration](../configs/chronos-control-v3.json) preceded evaluation; the model is outside the frozen42-arm selector pool. No official export, selector configuration or selection artifact changed.

- [Amazon Chronos-2 model](https://huggingface.co/amazon/chronos-2), revision `29ec3766d36d6f73f0696f85560a422f50e8498c`, Apache2.0.
- [Official library v2.3.2](https://github.com/amazon-science/chronos-forecasting/releases/tag/v2.3.2), Torch2.8CPU, Transformers4.57.1.
- Univariate zero-shot native q10/q50/q90; no covariates, fine-tuning, quantile repair, calibration, clipping or hyperparameter search.
- Past-only daily target contexts with NaN gaps; model context limit8192. Same4 eligible selector tasks,12 exact origin/series/horizon keys, Aug29/Sep5/Sep12. No15-cell numerical-grid mixing.
- Run [43689130190](https://github.com/howdymary/compute-forecasting/actions/runs/43689130190) succeeded after an engineering-only image assembly retry (the first attempt stopped before inference).
- Pinball **0.012113554233974892**, coverage **8/12**, mean interval width **0.08246805270512893** USD/GPU-hour.
- Starting selector0.014995328587716763; operational SFT0.011569797542840439. These are same-cell scores, not an equal-compute comparison between forecasting a series and selecting experiments.
- CPU execution29.564438419s, including retrospective evaluation and issuing the separate future commitment. Attributable cost unknown; no zero-cost claim.
- Model weights SHA256 `ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42`.

This additional control uses an already opened retrospective period. It is not independent validation, a commercial-system leaderboard, H100 policy evidence, or proof of general research intelligence. Pretraining knowledge/vintage contamination cannot be ruled out.

## Future commitment and locked evaluator

Chronos commitment issued2026-11-15T07:16:58.324190Z, hash `3b1dcd48ab1382cc7266d8e4eb61a7a47fbb6dfdebc28ff3decbc841db769c53`. It matches the14-series/42-row empirical baseline commitment `428296e044ca0a5c362ee5b96d9488c6fe47cd59be6a3d70000ac2c51cbf29d2`. Both use the same stale Nov6 snapshot, originNov15, targetsNov16/18/22.

Outcomes remain **pending**. The evaluator in `prospective_control_v3.py` gates on actual UTC time before reading any private records. It rejects scoring before Nov23UTC, changed commitments, incompatible targets, duplicates, invalid quantiles and incomplete truth provenance. Missing exact cells produce pending status with no score. It never fetches outcomes automatically and no future scoring job is scheduled.

A future authorized remote runner can invoke `python -m compute_forecast.prospective_control_v3 --baseline PRIVATE_BASELINE --chronos PRIVATE_CHRONOS --truth AUDITED_TRUTH --output RESULT` only after maturity. The separately supplied private truth JSON contract is schema1, sourced URLs, collection_vintage, identity_audit.status=verified, measurement=advertised_rental_offer_rate, unit=USD per GPU-hour, statistic=exact_registered_series_daily_median, and rows {series_id,target_date,horizon_days,value}. This is our prospective adapter contract, not an invented claim about a competition starter schema. Target identity must be reviewed against the original series definitions before using it. No future truth has been loaded.

## Reading the atlas

- The learning curve shows actual optimizer updates and saved development scores. RL0 is explicitly the frozen SFT parent. Rings mark selections made before evaluation.
- Scope selects **either** one horizon or one series; unavailable intersections are not invented. Random seeds remain separate observed controls. Fixed and GP controls show exact same12-cell or corresponding subset scores. Chronos has a distinct compute/information budget.
- Coverage must be read with width and denominator; 80% is nominal. No population confidence interval is warranted by three dependent dates.
- Paired traces show six real reveals from operational soft17/update100. Different sequences can produce identical final forecasters and losses. The deterministic final chooser retains matured validation in feedback-hidden arms.
- Cached reveals, fresh Modal executions, optimizer updates, elapsed wall time and partial provider receipts remain distinct. Gross reported charges can lag and exclude credits; remaining balance is unknown.
- History pins store exact date/value/unit, source URL, retrieval time, point hash and artifact version at pin time. Changing controls never rewrites them.

## Reproduce and verify remotely

No local checkout is required. GitHub Actions fetches immutable commit tarballs. Publication uses one validated atomic public payload and a separate immutable comparator report. The public server mounts only the public volume and shares its existing I/O lock. Numerical experiment files, frozen CSV bytes and the automatic campaign publication pipeline remain intact.

- [Metadata audit](https://github.com/howdymary/compute-forecasting/actions/runs/43687797141)
- [Independent archive identity audit](https://github.com/howdymary/compute-forecasting/actions/runs/43688836187)
- [Licensed publication and paired traces](https://github.com/howdymary/compute-forecasting/actions/runs/43689301328)
- [Chronos control](https://github.com/howdymary/compute-forecasting/actions/runs/43689130190)
- `/api/research-assets`: contextual observations, attribution, publication decisions and exact paired trace hashes.
- `/api/chronos-control`: registered settings, revision, package versions, cell keys, context audit, scores and future commitment.
- Existing `/api/notebook`, `/api/experimental` and official download stay available.

Remote unit checks enforce publication permission identity, units, cutoff, missingness, hash integrity and time gates. A separate PNG-only research-explorer UI workflow checks values against artifacts, historical gaps, matched comparison counts, checkpoint rings, paired traces, pin immutability, keyboard/touch, narrow layouts, loading/retry states and concurrent requests. Existing pricing/notebook/experimental checks continue. No recording jobs or video files are touched.
