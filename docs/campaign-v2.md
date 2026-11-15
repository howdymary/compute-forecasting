# Compute Forecast v2: registered experimental campaign

This version preserves the original release and official forecasts. The config in configs/campaign-v2.json is registered by its GitHub commit before training or v2 evaluation.

## Research questions
1. Can stronger numerical forecasters improve official pinball on broader eligible H100/A100 daily targets?
2. Do hard-label SFT, soft-label SFT, or outcome-reward RL improve bounded experiment selection against starting, static, random, and numerical adaptive selectors?
3. Do evidence and criticism change decisions usefully when they are separately controlled?

## Evaluation status
This is retrospective reuse of the inspected Pacific frozen pack. V1 development dates include the v2 evaluation dates. They are withheld from new weights and checkpoint selection, but are not an untouched scientific test. The opened September27–October25 final period is excluded from this campaign. November7–13 competition outcomes are never loaded.

All numerical comparisons use the unmodified official target builder and scorer. Phase boundaries, label maturity, six-trial budgets, seeds and checkpoint selection are fixed in the versioned config. Cross-series cases and overlapping origins remain dependent. No training loss or update count proves improved research ability.

## Measurement gate
Audit official catalog membership, history, changes, missingness, basket coverage, identity ambiguity and capture dates before attributing improvements to price information. Observation recency is not quote-verification age. The pack is a retrospective frozen vintage; each calibration residual's original historical vintage is unproven.

## Campaign
Use the existing 24 Ridge candidates and four official references, plus bounded autoregressive, EWMA, quantile-tree, convex-mixture and coverage-only controls. Cap the registry below48. Record every fallback and quantile repair.

Train the primary supported small Tinker model using seeds17,29,43 and hard/soft objectives. Select checkpoints on development only, then freeze before evaluation. Gate genuine RL on valid sampled-action log probabilities and nonconstant training rewards. Tool-use activity, adaptation, training improvement and forecasting improvement are separate claims.

Use Exa for current methods research. Historical page snapshots may be used only after account capability and page availability are established; do not backdate current retrieval or memory. Exact responses stay private when terms require it; publish provenance and permitted summaries.

## Resource and release boundaries
No topups or billing changes. Max six Modal containers, bounded jobs and resumable artifacts. Preserve every experiment's source/data hashes and actual usage; unavailable charges remain unknown. Keep raw data private. Public v1 artifacts and video assets are not rewritten.

Official documentation inspected November14:
- https://tinker-docs.thinkingmachines.ai/cookbook/recipes/decisions/
- https://tinker-docs.thinkingmachines.ai/cookbook/rl/
- https://tinker-docs.thinkingmachines.ai/tinker/losses/importance-sampling/
- https://exa.ai/docs/search/snapshot
- https://modal.com/docs/guide/function-invocation-methods
- https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html
