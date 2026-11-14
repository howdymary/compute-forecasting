# Representation benchmark and bounded search protocol v2

This protocol is committed before running the new candidate grid. It supersedes no recorded warmup results; that integration experiment stays separate.

## Questions and scope

Primary question: On the official headline A100/H100 daily-statistics targets from the continuously observed afhubbard collector, how do level versus log modeling and pooled versus fixed-composition auxiliary features affect 1-, 3- and 7-day advertised rental-rate forecast loss?

The primary scope is restricted to this collector because its offer-level configuration data has the long January-November history needed for a composition comparison. Collector, instrument class, GPU model and pricing tier are matched using catalog columns. Series IDs are opaque. The target is always the official daily-statistics series and statistic; auxiliary features never replace its value. Other official headline targets retain the official empirical baseline in a full competition export. AWS spot and late-start collectors are secondary diagnostics, not evidence for provider-composition effects in this primary study.

Secondary question: Under a six-trial budget, does a trained bounded policy select better configurations than fixed or seeded random search? Every policy begins with the same two completed official baseline trials (last_value_empirical and drift), then may reveal four candidate experiment results. An experiment's selectable score consists only of backtests whose labels have matured by the task cutoff. The future forecast is evaluated after the selection is frozen. Cached numerical results count as trials when revealed; no policy gets unobserved candidate scores.

## Frozen configurations

24 Ridge configurations: representation {level,log} x auxiliary features {target_only,raw,fixed_basket} x lookback {28,56 calendar days} x alpha {1,100}. All use the same target-history features, training eligibility and calendar lookup rules. Hyperparameters are not expanded in response to final outcomes. Current and lagged observations must be dated at or before each model origin. Missing dates are not interpolated.

Raw features summarize same-contract offers after retaining the last UTC snapshot per provider/configuration/day. Configuration identity uses the actual schema's provider, sku_raw, region_canonical, gpu_count and gpu_memory_gb fields; missing values are explicit. Raw daily median, provider/configuration counts and concentration are auxiliary predictors, not alternate targets. Do not blend rental offers with indices, resale or executed transactions.

The fixed basket is established from the first seven calendar days available for a contract, using only observations in that anchor interval. Membership never depends on subsequent survival. Anchor prices are per-configuration medians, weights are equal, and the index is the geometric mean price relative. Publish anchor dates, membership hash and daily coverage. Incomplete baskets have a missing index, with coverage retained; imputation is fitted only on each training subset. No changing-member index is described as fixed-composition.

Forecast each horizon directly as a transformed price change. Ridge and feature transforms are fitted only to matured labels in the rolling window. Quantile offsets use chronological out-of-sample residuals, with each residual prediction fitted using information available at that residual's own origin. Quantiles are ordered and strictly positive; no nominal coverage guarantee is asserted. Insufficient history or calibration explicitly falls back to the official empirical baseline and is counted in coverage reports, rather than dropping difficult cases.

## Time and scoring

Training labels end July 31, 2026. Development forecast origins: August 8, 15, 22, 29; September 5, 12. Final forecast origins remain September 27; October 4, 11, 18, 25 and are not opened during development. Weekly outcomes are dependent. The official November 6 origin stays separate from the historical study.

Use the unmodified official builder, baselines and scorer from the verified archive. Build history/catalog before truth so membership does not see future data. Restrict a copy of the official catalog to the declared research universe, keeping every target definition and value unchanged; filter forecast rows to the identical set. Report exact official pooled pinball and skill, mean/median/geometric series skill, interval coverage, counts, missing cells and failures. Retain all official per-cell CSVs. Primary research-subset scores are not mislabeled as the full competition score.

For search tasks, backtest origins are 7, 14 and 21 days before the decision cutoff. Only labels through that cutoff may appear in observations, memory, demonstrations or rewards. Selection outcomes from future forecasts are held by the evaluator and cannot be recalled by the agent. Training tasks and their future evaluation labels must end no later than July 31. Final search decisions and model/checkpoint choice are frozen before final truth is opened.

## Evidence and memory

Exa retrieval happens at the actual research time. Current pages are not historical market features, regardless of publication-date filters. Methodological evidence may influence a documented experiment hypothesis; live GPU-price news is isolated from the benchmark. Each past.dev audience is scoped to a study/task/phase, and every write includes its audience, author, source/result IDs and actual creation time. Do not backdate a present research finding to a historical market cutoff. More than one role must write and read; actual returned source IDs must be referenced by a later decision. Empty or unsupported recall is a failed integration, not a successful memory-use claim.

## Public claims and release

This is a retrospective frozen-vintage study with incomplete source-availability proof. It measures advertised rates, not guaranteed capacity, transaction execution, financing or hardware resale. Report all configurations, fallback counts, failed runs and negative results. Keep raw data private pending the pack owner's licensing confirmation. Preserve source attribution and credit normalization precedents. Training a policy does not itself demonstrate useful autonomy, and a one-origin warmup is not the main experiment.
