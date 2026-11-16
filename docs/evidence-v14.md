# Price history versus price plus BLS

This separately registered post-event study trains fresh Qwen3.5-4B LoRA forecasting models under two matched input conditions. The model predicts observed 1-, 3-, and 7-day log-price changes directly; 64 stochastic samples produce empirical quantiles. No fixed request seed is supplied.

The primary question is whether original-release electricity-distribution PPI features improve seven-day quantile pinball beyond price history and configuration metadata. News and infrastructure features are excluded. Current pages have not established origin-safe historical event features.

## Registered comparison

[Final protocol](../configs/direct-evidence-v14-final.json) · [Initial hypothesis](../configs/direct-evidence-v14.json) · [Source registry](../configs/evidence-v14-bls-sources.json).

Six runs combine seeds 17/29/43 with price-only or price+BLS inputs. Each gets 100 optimizer updates, batch 16, LoRA rank 16, learning rate0.00005, and checkpoints 0/20/50/100. Checkpoint zero is the actual unadapted model under the corresponding input condition. Lowest development seven-day pinball selects the checkpoint, with the earliest update winning exact ties.

Both arms use 326 training tasks, 20 development tasks and 22 retrospective tasks. Training contains 284 A100 and 42 H100 examples. These are overlapping windows, not independent market experiments. Seven BLS reference months occur in training and eight releases occur across all task origins. Ten original monthly releases are retained for source coverage.

Training labels end September 19. September 27/October 4 are development origins. October 11/18/25 are previously accessible retrospective evaluation origins. The three dates, correlated series and seed replications do not establish population significance or prospective accuracy.

## Original economic releases

BLS [archived monthly reports](https://www.bls.gov/ppi/detailed-report/) preserve each release's original values. We use industry 221122, base 12/03, matching series PCU221122221122. This index measures electricity-distribution producer prices, not a cloud electricity tariff.

The acquisition adapter retrieves official PDFs through Exa after direct XLSX downloads returned 403 and ALFRED vintage requests timed out. The retained content hash identifies extracted PDF text, not the binary PDF. Exact index rows and ordered monthly captions are checked. September's last caption was omitted by the extractor; it is independently verified against original PDF page 184 and exact five-column values.

Actual publication dates, including delayed early 2026 releases, are converted from 8:30 America/New_York to UTC. Retrieval/first-observed timestamps remain November 16; they are never backdated. The original monthly archive supplies the historical-availability basis. Current revised series values do not replace these vintages.

The structured evidence block contains index level, month-over-month log change and release age. Both arms have identical targets, histories, seeds, update budgets, inference budgets, eligibility and fallback rules. Evidence adds about 100 prompt tokens in the observed preflight; actual token usage is retained separately. This is an information comparison, not a claim of identical token charges.

## Charts

The learning chart answers whether development forecasting quality changed at measured optimizer checkpoints. It plots saved seven-day pinball observations and original selection markers; connecting lines are guides. Six runs remain identifiable, including exact overlaps.

The linked price chart answers what each checkpoint actually forecast on a source-bound development case. It combines compatible history, fixed origin, actual quantiles and development outcomes with fixed axes across checkpoints. The default is the lexicographically first development case with an observed price change, selected independently of model forecasts or scores. This helps explain a real price movement. It is not a representative final-test case. The separate visual configuration records the rule; it does not change training or checkpoint selection.

## Reproduction

Training and dataset preparation run in [GitHub Actions](https://github.com/howdymary/mochi-demo/actions/runs/43966729631), with Tinker providing genuine optimization and sampling. Numerical reconstruction from a downloaded public result directory needs no model credentials:

~~~sh
PYTHONPATH=src python -m compute_forecast.verify_evidence_v14 --results RESULTS_DIRECTORY
~~~

Exact stochastic regeneration need not match. Retained sample vectors, source hashes and deterministic arithmetic reproduce published scores. Numerical reruns need the unchanged Pacific pack; weight training needs Tinker credentials. Provider-reported charges remain unknown when no receipt is available.

[Findings](evidence-v14-findings.md) · [Public artifacts](../results/evidence-v14/README.md) · [Checkpoint retention](checkpoint-retention-2026-11-16.md).

## Interpretation limits

The BLS block can identify calendar position as well as operating economics. A measured difference would support this input condition, not a causal electricity-cost mechanism. Provider geography and global monthly release alignment remain limitations. The evidence arm uses more input tokens, so equal optimizer/sample budgets are not identical token charges.

The base model’s complete pretraining history is not verified. Supplying origin-safe inputs does not prove that all historical public outcomes were absent from pretraining. Both arms share the same base model; genuinely later observations remain necessary.

The separate [prospective protocol](../configs/evidence-v14-prospective.json) requires a checkpoint lock, compatible retained source history, advance issuance and matured outcomes. It is registered, with no forecasts issued in this study yet. Existing collection and November 23 gates remain unchanged.

## Resource-accounting convention

The frozen trainer's `completion_tokens` field stores normalized loss-weight mass, not a token count. The corrected resource audit separately counts positive-weight supervised token positions, full training sequence tokens and loss-weight mass. It reconstructs the registered batches and checks their mass against completed optimizer updates. The earlier audit is retained with its correction identified; model training, sampled forecasts and scores are unchanged. Neither reconstruction nor elapsed runtime is a provider billing receipt.

## Sampling records

Saved valid return vectors reproduce the empirical quantiles exactly. The frozen trainer retains malformed-sample counts, but not the raw malformed completion text. The public report distinguishes sample diversity, zero-width forecast cells and parsing failures. A zero-width interval can coexist with diverse sampled vectors when at least 80% of one horizon's probability mass is concentrated on no change; it is not automatically a request-seed failure.

The price-history control shows 21 days by default and can reveal the full 42-day model context. It changes the displayed time window, never the model input or score. Axes remain fixed while inspecting checkpoints within the chosen case and window. Pins retain the immutable publication ID and dataset hash along with their original values.

## Frozen operational models

The prospective registration fixes seed 17 for both input conditions. Both original development selections were update 50. Their hash-only [model lock and retention receipt](../results/evidence-v14/audits/43972363425/model-lock.json) bind the source report and private saved-state identities. Tinker accepted retention through March 15, 2027, covering the registered panel's intended scoring period. No new checkpoint copies or optimizer updates were needed. This is model availability, not a forecast issuance or evidence of future accuracy.

## Process exit after saved results

The seed43 price-only process saved all100 updates, its development-selected update20, both evaluation files and the final result, then aborted during process teardown (exit134). GitHub successfully uploaded all9 result files. The original workflow failure is retained. Numerical publication independently verifies the saved samples, checkpoint selection, baselines and scores; the optimizer was not rerun.

[Prospective execution and readiness](evidence-future-v15.md) describe the separately deployed runner. No future accuracy is inferred from deployment.
