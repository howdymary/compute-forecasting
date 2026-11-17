# Direct probability forecasting v18

[Live comparison](https://howdymary--compute-forecast-evidence-v14-web.us-east.modal.run/probability) · [Configuration](../configs/direct-probability-v18.json) · [Measured findings](probability-v18-findings.md) · [Result pointer](../results/probability-v18/latest.json) · [Data/API audit](../results/probability-v18/audits/44006306188) · [Training execution](https://github.com/howdymary/mochi-demo/actions/runs/44006731633)

This post-event study asks whether directly training a future-price distribution improves seven-day quantile pinball over the same untuned interface and demanding numerical controls. It compares categorical cross-entropy (CE) with exact discrete CRPS. It does not change the original competition submission or the earlier selector, JSON-return, calibration or prospective studies.

## Data and chronology

The frozen Pacific pack contains source-specific advertised rental prices, not transaction prices or guaranteed capacity. Qualification uses the November 6 catalog's metadata, H100/A100 models, approved CC BY 4.0 daily-statistic sources and headline status. Hyperscaler spot and neocloud on-demand contracts retain separate IDs. A shared model conditions on their identities; no histories are stitched together.

| Partition | Origins | Windows | Series | Forecast cells |
|---|---|---:|---:|---:|
| Training | Eligible dates through October 4; labels through October 11 | 498 | 11 | 1,494 |
| Development | October 11 and 18 | 18 | 11 | 54 |
| Retrospective | October 25, 28 and 30 | 25 | 11 | 75 |

There are 25 seven-day retrospective cases and three dependent dates. Training contains 286 Hubbard, 172 GPU Rental Prices and 40 FastGPU windows; retrospective cases contain 6, 4 and 15, respectively. FastGPU remains underrepresented despite now appearing in training. A100 supplies 400 training windows and H100 98.

The 42-calendar-day contexts require at least 20 observations. Missing dates remain missing. Targets are exact observed prices at 1, 3 and 7 days; only matured labels enter training. A deterministic date cap is defined before execution. All 498 training value histories are distinct, but overlapping windows are not independent market observations.

The pack is a frozen collection vintage, not proof of original real-time availability. November catalog qualification is retrospective. Previously examined periods remain retrospective; neither expanding the data nor changing the output representation creates an untouched test. Unknown base-model pretraining exposure is an additional limitation.

## Model and objectives

Tinker trains Qwen/Qwen3.5-4B with rank-16 LoRA, the qwen3_5_disable_thinking renderer, and matched attention, MLP and unembedding adapters. Both objectives use the same seed-specific order, examples, batch size, candidate-token normalization and output support. Tinker is 0.39.1; cookbook is 0.6.1. Tokenizer content hashes and exact installed versions are retained; the provider does not expose an immutable base-weight revision.

The model assigns probabilities to 19 ordered log-price changes, including exact zero. The grid has nine geometrically spaced levels on each side. Its extent is max(log(2), 1.1 times the largest absolute training return). Positive prices are anchor × exp(log change). Levels use training outcomes only; observed outcomes are never clipped to them.

The original 21-choice API preflight failed because long prompts permit at most 20 scored token IDs. Before optimization, revision 2 registered 19 choices. [Original configuration](../configs/direct-probability-v18-preflight-v1.json) and [failed execution](https://github.com/howdymary/mochi-demo/actions/runs/44005208079) remain available. Numerical inputs, eligibility and split dates were unchanged. The successful preflight verified unique answer tokens, alignment, stable probability readout and gradients.

CE minimizes the negative log probability of the nearest dollar support level. CRPS uses the actual unrounded price:

CRPS = Σ p(j)|z(j) − y| − ½ Σ p(i)p(j)|z(i) − z(j)|.

Both losses backpropagate through the same softmax-normalized candidate-token log probabilities. Labels occur only in client loss metadata, never the forecasting prompt. One fixed median training anchor, 1.8809, rescales CRPS for optimization; reported CRPS remains in dollars. This does not introduce per-series weighting.

Quantiles are the left inverse CDF at 0.1, 0.5 and 0.9. There are no generated JSON samples or Monte Carlo quantiles in this study. The finite support limits resolution: development median nearest-support absolute error is 0.01137, compared with 0.041 for persistence. Support covers all retained development and retrospective outcomes, but this does not establish prospective tail coverage.

## Training and selection

Two equally budgeted learning-rate pilots per objective use seed 17 and rates 0.00002 and 0.0001. Each run makes one pass over the 1,494 horizon examples: 94 updates, batch size 16. Checkpoints are 0, 24, 47 and 94.

The lowest development seven-day mean dollar pinball selects the checkpoint; checkpoint zero is eligible. Exact ties favor the earlier update, then the smaller rate. The winning seed-17 pilot is reused, and seeds 29/43 train at the chosen rate. The final comparison has six runs; all eight candidate runs remain public. The separate API mechanism check makes four updates and is not a forecasting result.

Limits are two parallel training jobs, two hours per model, a ten-hour campaign envelope, at most 24 new permanent states and a preflight-checked storage margin. Existing checkpoints are not deleted. Private recovery receipts save optimizer identities, exact completed update counts and public outputs. Completed optimization is not repeated to repair publication.

## Evaluation and interpretation

Seven-day dollar pinball is primary. Point MAE is the average absolute error of q50 forecasts. One- and three-day results, raw dollar CRPS, median error, 80% interval coverage, width, failures and support diagnostics are reported together. Native controls execute the unchanged starter-kit last-value, empirical last-value, multiplicative drift and seasonal-naive implementations on identical eligible cells. Registered persistence fallbacks retain failures in denominators.

The original untuned JSON forecaster is compared only on exact retained matches, with a separate denominator. The retained Chronos comparison has August/September origins and no overlap with this October cohort; it is unavailable here rather than being compared on unrelated scores.

Source, series, GPU family, instrument, origin, horizon and changed-price diagnostics use retained cell values. Weighted loss contributions sum to the displayed aggregate difference. Three-seed variability and leave-one-origin sensitivity are descriptive; three dependent market dates do not support a population-significance claim. Relative skill remains undefined when the reference loss is zero.

A win against the new untuned probability interface alone is insufficient evidence of practical superiority. Any claim must also state the numerical-control comparison. This study changes both representation and training data relative to v14, so it cannot isolate which change explains a difference from that older study.

## What the three charts answer

- **Historical prices and forecast quantiles:** what exact price forecast did the selected model or development checkpoint produce? The series history and saved model probability artifacts supply every value. Price axes stay fixed within a case. Connections between 1-, 3- and 7-day points are visual guides.
- **Development checkpoint curves:** did development forecasting loss improve during actual optimization? Only measured updates appear. Original selected checkpoints are marked. Retrospective forecasts are not recomputed at every checkpoint.
- **Probability mass:** where does each model place uncertainty? The retained 19-level vectors supply the points. Categories have uneven numeric spacing, labeled explicitly; the vertical probability scale stays fixed.

Retrospective and development modes are distinct. Pins preserve the original value, series identity, dataset hash and report hash. Keyboard and touch inspection, reduced motion, error/retry and mobile layouts are tested without recording video. A pending run has no invented curve.

## Separate later evaluation

The [new registration](../configs/probability-v18-prospective.json) fixes seed 17 for CE/CRPS, retains their development-selected states and starts eight weekly Sunday origins on December 6. Issuance closes 60 minutes after the UTC origin ends. At least 20 retained daily observations are required, with at most four source-verified contracts.

Continuing exact competition collector medians are unverified. This is therefore an explicitly separate individual-provider transfer cohort with its own source IDs, units and contract hashes. Snapshot collection time does not establish the provider's quote-update timestamp. Missing origin quotes prevent issuance; unavailable outcomes remain pending.

Commitments bind probabilities, quantiles, attributed public price contexts, input-vintage hashes, model/configuration hashes and actual issuance/publication receipts. The public HTTP response must match the commitment hash before the deadline. This verifies availability, not an independent trusted timestamp. Origin anchors and every public input date are checked before issuance; existing shared-volume reload/read locking is preserved. Final outcome analysis is locked until February 1, 2027 UTC; collection and issuance stop after the registered eight-week panel. A separate three-query synthetic read-only preflight checks the deployed credentials, tokenizer and selected model access before activation. Per-query timeouts, persistence fallbacks and sanitized failure receipts keep failed methods visible; synthetic probe outputs are never market forecasts. No new training occurs. Existing panels and the November 23 gate remain unchanged.

## Reproduce and verify

After installing the project's ordinary Python dependencies, the following credential-free command reads the current immutable result pointer and reconstructs saved probabilities, quantiles, scores, selection, denominators and contribution arithmetic:

    PYTHONPATH=src python scripts/verify_probability_v18.py

It does not regenerate hosted model weights or claim stochastic training is byte-identical. Exact source hashes and the official CSV preservation check are included.

Authorized full data rebuilding runs probability_data_v18 on Modal against the unchanged pack; audit-probability-v18.yml performs the tokenizer, storage, support and custom-gradient gates. train-probability-v18.yml executes the bounded campaign. publish-probability-v18.yml assembles retained outputs without repeating optimization. The [credential-free verification workflow](../.github/workflows/verify-probability-v18-public.yml) runs the same arithmetic and contract checks using only public artifacts. The dedicated UI workflow publishes desktop/mobile PNGs. Re-running an incomplete matching model is refused until its exact recovery state is resolved.

Public artifacts permit arithmetic verification without Tinker or Modal credentials. Full numerical data rebuilding needs pack access; private checkpoint regeneration needs authorized Tinker access. Provider charges remain unknown when no receipt is available.

## Sources and attribution

Pacific Machines (2026), gpu-price-pack v0.1.1-handover, cutoff November 6; compilation CC BY 4.0. Source components are Alex Hubbard's GPU Price Tracker, GPU Rental Prices and FastGPU. Exact source URLs, contracts, licenses and history hashes are in the data audit. See [source rights](DATA_SOURCES.md) and the [copied pack notices](../results/value-v5/runs/43757456253/notices). Raw offer tables and model resources are not redistributed.

Method foundations: Thinking Machines' [probability-model recipe](https://tinker-docs.thinkingmachines.ai/cookbook/recipes/decisions/), [custom losses](https://tinker-docs.thinkingmachines.ai/tinker/losses/custom/), [direct time-series example](https://thinkingmachines.ai/news/inkling-2-small/) and [forecasting study](https://thinkingmachines.ai/news/training-llms-to-predict-world-events/); Gneiting and Raftery (2007), [proper scoring rules](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf). Their results do not establish GPU-price accuracy. The exact GPU-price adaptation and discrete CRPS comparison are evaluated here. Upstream answer-position references: [distribution-training datums](https://github.com/thinking-machines-lab/tinker-cookbook/blob/1991897cba59ea9d9b0030d183d1867b28eba9d9/tinker_cookbook/recipes/decisions/train.py#L69-L103) and [probability readout](https://github.com/thinking-machines-lab/tinker-cookbook/blob/1991897cba59ea9d9b0030d183d1867b28eba9d9/tinker_cookbook/recipes/decisions/decision.py#L23-L47). The deployed read-only preflight also records actual installed 0.6.1 source-file hashes and verifies that the training target row aligns with inference's answer position.

All prospective accuracy claims remain pending until the registered compatible outcomes mature.

## Serving and publication

GitHub remains the canonical record. The existing serialized deployment workflow mirrors both committed study reports onto the existing public Modal volume, then deploys the read-only application. HTTP data requests read those hash-verified snapshots and never fetch GitHub. Both study APIs and future artifacts share a reload/read lock, following [Modal's volume consistency requirements](https://modal.com/docs/guide/volumes#filesystem-consistency). No private volume or model credentials are mounted in the web application. Desktop/mobile validation runs after canonical deployment and compares the served values with the immutable GitHub artifacts.
