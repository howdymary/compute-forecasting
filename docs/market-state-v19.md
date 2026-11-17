# Market-state v19: a matched direct forecasting study

**Question.** Does source-specific market-price context improve future advertised GPU rental forecasts beyond an otherwise matched price-history model?

This is a separately registered, post-event study. It preserves the official export, earlier studies, the November 23 gate, and the v18 December 6 / February 1 panel. It does not test news, availability, infrastructure or BLS effects.

## Registered comparison

- [Training protocol](../configs/market-state-v19.json), [feature definitions](../configs/market-state-v19-feature-definitions.json), and [readiness thresholds](../configs/market-state-v19-readiness.json).
- Two conditions: target history and shared history summaries; identical inputs plus other-provider within-group price changes and observed collection composition.
- Qwen/Qwen3.5-4B, rank-16 LoRA, categorical CE over the unchanged v18 19-level future-price support. Tinker 0.39.1 / cookbook 0.6.1; fixed learning rate 0.0001.
- Seeds 17, 29, 43; identical examples and seed-specific order across conditions; one epoch or 200 updates, whichever comes first. At most two simultaneous runs.
- Save update zero as the public untuned model identity without redundant storage, and states at 25%, 50%, and 100% of the epoch. Select lowest development seven-day pinball, including zero; earliest update breaks exact ties.
- Deterministic quantiles of actual conditional answer-token probabilities. No decoded-number gradients or Monte Carlo sample quantiles. CE targets are nearest support levels for actual matured outcomes; actual scoring outcomes are not clipped.
- Learned states have 180-day retention, covering the April analysis. Existing states are not deleted. A storage preservation failure gates optimization.

[Tinker custom losses](https://tinker-docs.thinkingmachines.ai/training/losses) and [checkpoint APIs](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/trainingclient/) describe the mechanisms. Model training directly changes price-distribution probabilities; this is separate from the earlier experiment-selector study.

## Data and readiness

The frozen Pacific pack checksum is `f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c`. Its 672 manifest entries plus the manifest itself explain the 673-file description.

The audit found 571,191 H100/A100 rows and 239,580 daily provider/configuration groups before final eligibility filtering. The registered preparation retained **314 training windows / 942 horizon examples**, 12 source-defined groups, eight providers, and 90 distinct training origin dates. Fifty-seven windows had changed seven-day prices. Other-provider return context was available on 89.49% of training windows. Development has 16 seven-day cases on two dates; retrospective evaluation has 24 on three reused, dependent dates and eight eligible groups.

Windows overlap. These counts are not independent market experiments. The base-model pretraining cutoff and historical outcome exposure are not established; origin-safe prompts do not prove absence of pretrained knowledge. Historical timestamps are source-reported snapshots in a frozen pack, not independent proof of original public availability.

Targets are daily medians within source / provider / GPU / instrument / tier / SKU / region / node groups. They are **new targets**, not the official collector medians, persistent listings, or executed transactions. Ambiguous same-timestamp groups are excluded before performance inspection. Missing region/node metadata remains missing.

The existing feature name observed_quote_count counts observed daily source-defined provider/configuration groups, not individual raw offers or guaranteed available machines. Dollar ratios require matching recorded region, GPU count and memory. No such ratios were usable in the training cohort. Return context instead computes changes within each stable source-defined group, aggregates once per other provider, then summarizes the other providers. It is an indirect signal; it does not imply comparable contract prices.

The audit and dataset bind to the protocol and preparation/feature-engine hashes. Both arms use the same examples. The engineering readiness gate is not a statistical power guarantee. Training ends October 4 with labels through October 11; development uses October 11/18 and retrospective evaluation October 25/28/30. Protected November 7–13 outcomes are not loaded.

## Sources and publication decisions

Checked November 17, 2026 UTC (November 16 in Los Angeles). Compilation and component rights are checked separately.

| Source | Measurement / rights | v19 decision |
|---|---|---|
| Pacific pack / GPU Price Tracker component | Compilation CC BY 4.0; approved component rows retain source URL and licence ID. DATA.md, ATTRIBUTION.md and source register govern attribution. | Use approved quality-ok CC-BY-4.0 H100/A100 observations. Publish attributed derived histories and predictions; keep unchanged pack and raw offers outside this release. |
| [GPU Rental Prices data](https://gpurentalprices.com/data), [current JSON](https://gpurentalprices.com/api/latest.json), [health](https://gpurentalprices.com/api/health.json) | CC BY 4.0 source; posted per-GPU-hour offers, source-day/provider checks. Collection does not establish quote-update time or guaranteed capacity. | Continuing open-data path. Exact variants only; stale checks and conflicting same-contract prices excluded. |
| [GetDeploying dataset](https://getdeploying.com/dataset/gpu-prices), [API](https://getdeploying.com/help/api) | Public dataset and richer authenticated API have distinct access/terms. Weekly medians are not individual contracts. | No new ingestion or paid access. Historical vintage, identity and API access must pass separately. Already represented in the pack. |
| [Price of Compute API](https://priceofcompute.com/api) | Advertised free attributed API; access permission does not alone settle every source's redistribution or target identity. | Not ingested. Methodology, freshness, deduplication and source-specific permission remain to verify before use. Do not fetch full history across the protected period. |
| [Vast offers](https://docs.vast.ai/api-reference/search/search-offers), [metrics](https://docs.vast.ai/api-reference/machines/show-gpu-metrics) | Authenticated marketplace products; metrics/rented state are not market-wide demand or independently measured workload utilization. | No ingestion. Authorized credentials, precise measurement and redistribution basis required. |
| [Runpod catalog](https://docs.runpod.io/api-reference-v2/catalog/list-gpu-types) | Availability depends on product/cloud/geography/count; maxCount is not stock. | No ingestion. Authenticated product-specific measurement and reuse checks required. |
| [AWS announcements](https://aws.amazon.com/blogs/aws/), [NVIDIA RSS](https://nvidianews.nvidia.com/rss) | Dated primary evidence, not delivered capacity. Announcement and effective dates may differ. | Excluded from training: no verified joint historical feature panel. Current discovery remains separate from frozen inputs. |
| BLS / infrastructure | Release vintages and event availability required; electricity PPI is an index. | Excluded from this study. Earlier BLS results remain unchanged. |

Current-source identities preserve provider, GPU variant, node, region, product, commitment, source URL and host details. Duplicate aggregator copies are not pooled: this primary capture uses one source. A future new aggregator must deduplicate underlying provider contracts before combination.

The first v19 capture retained 43 exact-variant offers from 13 providers for **November 16**, first observed November 17 UTC. It is not relabeled a November 17 observation, and is ineligible for origin issuance. Source bodies and revision vintages remain on the private volume. Public captures contain permitted normalized observations and hashes, not credentials.

## Controls

Run the four unchanged starter-kit methods on all available past observations for the new target identities: last_value, last_value_empirical, multiplicative drift and seasonal_naive. The native source hash is verified. Omitted native rows use flagged persistence.

A fixed, training-only quantile GradientBoostingRegressor (50 estimators, depth 2, learning rate .05, seed 17, leaf minimum 8) receives price summaries in one arm and the same market fields in the other. Fixed zero imputation has explicit missing indicators. Quantile crossings are corrected and recorded. The numerical learner uses the shared history summaries, horizon, anchor and GPU family, rather than the LLM's full raw history sequence. Its two conditions are matched to each other; it is a diagnostic of information value, not an equal-capacity architecture comparison.

Frozen v18 collector medians have no exact target match here, so their aggregate scores are not reused as matched controls. No eligible exact future-rate announcement is in this cohort; an announcement-aware rule is therefore not claimed as tested. Calibration and RL are outside this primary comparison.

## Independent future panel

[Protocol](../configs/market-state-v19-prospective.json): earliest December 20, 2026; sixteen weekly origins through April 4, 2027; final analysis not before **April 12, 2027 UTC**. Collection stops April 19. The original v18 panel is unchanged.

This is an explicitly labeled **individual-contract transfer cohort**, distinct from historical provider-group medians and competition targets. Before first issuance, choose 8–12 contracts with at least 30 retained price days, three providers, and two contracts in each GPU family. Selection is deterministic, price-independent provider/family round-robin; freeze once with no replacement.

Daily capture is scheduled at 17:40 and 18:40 UTC, with a finite 400-attempt cap and body-size limits. Failures and revisions remain visible. First observed vintages are preserved. Only same-day collections within the registered 17–19 UTC window can serve as origin data or truth. A stale archive is not a new quote.

A separate Actions workflow issues Monday at 00:05 UTC for Sunday's origin, within the registered one-hour deadline. It requires complete frozen cohort inputs, origin-safe features, frozen model and numerical-state hashes, and selected seed-17 checkpoints. No prospective optimizer updates occur.

Each commitment retains full probabilities, quantiles, contracts, inputs, source hashes, actual issuance time and failures. GitHub artifact receipts provide server timestamps, but this repository caps downloads at 90 days. The runner therefore also signs the forecast manifest using [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations). The bundle is retained in the versioned repository. [CLI verification](https://cli.github.com/manual/gh_attestation_verify) checks the artifact digest, repository, branch, signer workflow and cryptographically verified transparency timestamps. Predicate dates and author-entered commit dates are not timing evidence. The genuine initial proof was a readiness manifest with zero forecasts, not an issued prediction. Missing or late publication cannot establish an eligible prospective result. Outcomes are resolved only against exact first-vintage contracts; missing truth stays missing.

Primary endpoint is seven-day dollar pinball, with one-/three-day scores, median MAE, width, coverage and failures alongside it. Seeds share outcomes. Origin clustering and common shocks must be respected; sixteen dates do not establish adequate power. No early promotion or repeated significance testing. Negative or inconclusive results remain publishable; a later extension requires a new registration.

## Reproduction

Public arithmetic, without credentials:

```bash
python -m pip install -e .
python -m compute_forecast.verify_market_v19
```

Run this in an authorized remote environment; development here uses GitHub Actions and Modal, with no local checkout.

Remote workflows:
- prepare-market-v19.yml: source-bound data preparation and readiness, no model calls.
- train-market-v19.yml: the registered six-run campaign. Completed recoveries are reused; incomplete runs refuse duplicate optimization.
- controls-market-v19.yml: substantive Modal baseline and numerical execution.
- publish-market-v19.yml: reconstruct, validate and publish retained outputs.
- capture-market-v19.yml: source-day vintages.
- future-market-v19.yml: fixed future issuance and gated scoring.
- validate-market-v19-ui.yml: strict arithmetic, HTTP/2, desktop/mobile and PNG-only validation.

Authorized pack access is required to regenerate training data. Tinker credentials/private states are required for exact model inference; the public base identifier and all probability vectors remain inspectable. Provider cost is unknown unless a receipt supplies it. Checkpoints expose resource-identity hashes, not weight-byte checksums or private paths. No new video or recording is part of this work.

## Visual explanation

The upper chart shows matching history, three actual forecast points, their quantile intervals and archived development outcomes. Its axes are fixed within a case across seeds/checkpoints. Missing days break history paths; dashed forecast connections are guides, not daily predictions.

The supporting chart shows actual development checkpoint quality and original selections. It is not prospective accuracy. Default cases follow origin/series order, independent of model performance. Pins retain source-bound text and report identity even when controls change.

The separate future status contains only issued commitments and matured permitted outcomes. Pending outcomes remain empty. The experiment is running; prospective improvement is not yet established.


The issued-forecast figure is implemented but remains empty until eligible commitments exist. Coverage, width and paired origin differences remain pending until the locked evaluator runs. Synthetic contract fixtures exercise future controls remotely; they are not market observations and are not published as price histories. A prototype null model-lock registration field is preserved in its original file; a separate format-upgrade receipt records its removal from the new storage format without changing the scientific protocol, dates or candidates.


### Retained environment

The [actual dependency lock](../requirements/market-state-v19.txt) is committed independently of temporary Actions downloads. Package-name spelling tinker_cookbook normalizes to tinker-cookbook; its actual version is 0.6.1. Tinker is 0.39.1, matching registration. This was a package-name assertion issue in archival validation, not a different training environment. The full six-run comparison uses the same locked environment.
