# Direct quantile training and fixed ensembles

This post-event study follows market-state-v19. It tests a price-only forecast objective and two explicit ensemble controls. It does not alter any official export or existing prospective panel.

## Why this next experiment

V19 fine-tuning improved over the corresponding untuned models on reused historical cases, while other-provider context worsened mean seven-day loss across three seeds. Its CE objective learns a categorical price distribution; the scored output is three quantiles. A direct asymmetric quantile objective is a useful bounded alternative, not an established remedy.

[Multi-horizon quantile forecasting](https://arxiv.org/abs/1711.11053) motivates the proper asymmetric loss. [Quantile averaging versus probability averaging](https://pubsonline.informs.org/doi/10.1287/mnsc.1120.1667) motivates distinct fixed ensemble controls. [Monotone rearrangement](https://arxiv.org/abs/0704.3649) motivates ordered outputs. These are established methods; no novelty claim is made for them.

## Registered method

See [the immutable configuration](../configs/quantile-training-v20.json). Each quantile-specific prompt obtains conditional answer-token coefficients over the frozen 19 price levels. Their weighted mean encodes one scalar. Sort the three means and optimize their mean dollar pinball loss through the sort. The coefficients are **not predictive probability mass**. There is no CRPS claim for these heads.

One global median training anchor scales the loss; cell weights remain dollar-based. The model predicts the quantiles itself. The old numerical programs are controls, not the model's outputs.

Warm-start each child from the corresponding frozen v19 price-only checkpoint with fresh optimizer moments. The seed-17 pilot is bounded at 64 updates, eight horizon groups per batch, three quantile heads per group, checkpoints 0/16/32/64, learning rate 0.00002. This conservative fivefold reduction is fixed before optimization, not selected by an additional sweep. Checkpoint zero is the parent weights through the new head interface. It is distinct from the unchanged categorical parent control. Only head-zero versus trained identifies changes due to further updates within this interface.

A passing development gate can permit the same bounded experiment with seeds 29/43; it does not establish statistical improvement. No other hyperparameter search is authorized by the campaign. The first task is a pilot; failed gates and interrupted runs are public results.

[Tinker's supported custom callback](https://tinker-docs.thinkingmachines.ai/tinker/losses/custom/) computes the gradient through answer-token log probabilities. [Weight-only warm starts](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/serviceclient/) reset optimizer state. We reuse SDK0.39.1 and the committed v19 environment. A double-precision finite-difference test checks the gradient before a real update. This is direct supervised quantile optimization, not RL.

## Fixed ensembles

Uniform quantile averaging and uniform probability pooling use all three frozen price-only seeds. No fitted weights. Select one on the existing development cases before calculating new retrospective ensemble scores; preserve both. Convex pinball implies the averaged quantiles cannot have higher loss than the average individual quantile loss on identical cells. It does not guarantee beating the best seed, numerical baseline or future prices.

## Data and interpretation

The exact v19 dataset hash, 314 training windows and 942 horizon examples are retained. Three heads per horizon do not create additional independent market data. Sixteen development seven-day cases cover two reused dates; 24 retrospective cases cover three reused dependent dates. All new historical conclusions are exploratory. The source-reported collection vintage and unknown base-model pretraining exposure remain limitations. No November7–13 protected outcomes are used.

No current market news, BLS or availability feature is included. This isolates a price-only modeling intervention after the negative market-context comparison.

## Future test

[The separate prospective protocol](../configs/quantile-training-v20-prospective.json) leaves v18/v19 and the November23 gate unchanged. It plans 16 weekly origins from December20 through April4, final analysis no earlier than April12. It shares the source-qualified contract cohort with v19; this is a matched comparison, not an independent replication. New captures must be current and compatible. Missing or stale source observations cannot establish eligibility.

Only timestamp-verified commitments issued before outcomes resolve are eligible. A later challenger requires another registration; do not extend a losing panel until it wins. Future accuracy remains pending.

## Remote reproduction

The training workflow loads unchanged hash-bound private historical inputs through Modal, checks checkpoint preservation, runs the supported Tinker callback and saves private recovery state. It never deletes checkpoints or changes billing. Public artifacts contain numerical predictions, coefficients, summaries, diagnostics and hashes; resource paths and credentials remain private.

Credential-free arithmetic:

```bash
python -m pip install -e .
python -m compute_forecast.verify_quantile_v20
```

Authorized numerical reruns additionally require the original CC-BY-4.0 Pacific pack, Modal data access and Tinker resources. Regeneration can differ because provider computation is not promised byte-identical; arithmetic from saved predictions is exact. Original successful optimization is recovered rather than duplicated after a publication failure.

The interactive chart must distinguish a categorical forecast from scalar quantile heads, show actual saved checkpoints and fixed axes, and retain every regression. No video is created.

## Additional loss diagnostic

The registered preflight also decomposed the already opened v19 market-minus-price losses. Averaged across the three training seeds, the seven-day difference was +0.00058069 dollar pinball (market worse). Contributions were approximately +0.00036894 from q10, +0.00020790 from q50 and +0.00000385 from q90; their sum reconstructs the difference. This is descriptive arithmetic, not a confirmed causal explanation. Seeds share the same 24 seven-day market cases.

[Exact cell and group contributions](../results/quantile-training-v20/preflight/44057806631/diagnostics.json) preserve the origin/series breakdown and cancellations. The quantile objective was fixed before this decomposition, and was not retuned in response.
