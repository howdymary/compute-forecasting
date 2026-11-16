# Price history versus price plus BLS

This separately registered post-event study trains fresh Qwen3.5-4B LoRA forecasting models under two matched input conditions. The model predicts observed1/3/7-day log-price changes directly;64 stochastic samples produce empirical quantiles. No fixed request seed is supplied.

The primary question is whether original-release electricity-distribution PPI features improve seven-day quantile pinball beyond price history and configuration metadata. News and infrastructure features are excluded. Current pages have not established origin-safe historical event features.

## Registered comparison

[Final protocol](../configs/direct-evidence-v14-final.json) · [Initial hypothesis](../configs/direct-evidence-v14.json) · [Source registry](../configs/evidence-v14-bls-sources.json).

Six runs combine seeds17/29/43 with price-only or price+BLS inputs. Each gets100 optimizer updates, batch16, LoRA rank16, learning rate0.00005, and checkpoints0/20/50/100. Checkpoint zero is the actual unadapted model under the corresponding input condition. Lowest development seven-day pinball selects the checkpoint, with the earliest update winning exact ties.

Both arms use326 training tasks,20 development tasks and22 retrospective tasks. Training contains284 A100 and42 H100 examples. These are overlapping windows, not independent market experiments. Seven BLS reference months occur in training and eight releases occur across all task origins. Ten original monthly releases are retained for source coverage.

Training labels end September19. September27/October4 are development origins. October11/18/25 are previously accessible retrospective evaluation origins. The three dates, correlated series and seed replications do not establish population significance or prospective accuracy.

## Original economic releases

BLS [archived monthly reports](https://www.bls.gov/ppi/detailed-report/) preserve each release's original values. We use industry221122, base12/03, matching seriesPCU221122221122. This index measures electricity-distribution producer prices, not a cloud electricity tariff.

The acquisition adapter retrieves official PDFs through Exa after direct XLSX downloads returned403 and ALFRED vintage requests timed out. The retained content hash identifies extracted PDF text, not the binary PDF. Exact index rows and ordered monthly captions are checked. September's last caption was omitted by the extractor; it is independently verified against original PDF page184 and exact five-column values.

Actual publication dates, including delayed early2026 releases, are converted from8:30 America/New_York to UTC. Retrieval/first-observed timestamps remain November16; they are never backdated. The original monthly archive supplies the historical-availability basis. Current revised series values do not replace these vintages.

The structured evidence block contains index level, month-over-month log change and release age. Both arms have identical targets, histories, seeds, update budgets, inference budgets, eligibility and fallback rules. Evidence adds about100 prompt tokens in the observed preflight; actual token usage is retained separately. This is an information comparison, not a claim of identical token charges.

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

The separate [prospective protocol](../configs/evidence-v14-prospective.json) requires a checkpoint lock, compatible retained source history, advance issuance and matured outcomes. It is registered, with no forecasts issued in this study yet. Existing collection and November23 gates remain unchanged.
