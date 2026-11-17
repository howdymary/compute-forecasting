# Next continuation experiment: proposal, not an executed study

This proposal follows the v21 continuation campaign. It is **not a preregistration, training launch, checkpoint promotion or new accuracy result**. Final campaign results must be read from the [canonical pointer](../results/ce-continuation-v21/latest.json). Current retrospective diagnostics use retained predictions and do not create a new held-out test.

## The question to test next

Can a short continuation learn from real observed prices while retaining the useful conditional uncertainty of the frozen categorical forecaster?

The seed-17 pilot improved development pinball but worsened retrospective pinball. In its nine changed-price cases, mean probability of no change rose from 0.36035 in the incumbent to 0.52070 for original-data continuation and 0.49086 for expanded-data continuation. Interval width and coverage fell. The expanded arm's mean entropy over all cases actually increased: a generic entropy bonus would therefore target an incomplete description of the problem.

These are behavioral diagnostics, not proof of a causal explanation such as overfitting. Final ordering checks must be interpreted alongside them. [Reproducible distribution audit](../.github/workflows/diagnose-ce-continuation-v21.yml).

## First recommended intervention: anchored categorical CE

Keep the existing Qwen3.5-4B, LoRA rank 16, input format, 19 price levels, unchanged-price level, normalization and deterministic probability-to-quantile conversion. Start each candidate from the **same frozen v19 update-30 weights and Adam state**.

Compare three conditions:

1. Frozen incumbent.
2. Short ordinary categorical CE continuation.
3. The same continuation with a penalty for departing from the incumbent's full 19-level probabilities on the same training inputs.

Proposed loss:

```
ordinary = CE(observed_price_level, student_probabilities)
anchored = ordinary + lambda * KL(parent_probabilities || student_probabilities)
```

The parent is frozen and sees exactly the same origin-safe price inputs, without the future target supplied in its prompt. Its probabilities are a regularizer, **not additional market observations or ground truth**. Use the complete 19-level forecasting support; no top-K approximation over the language model vocabulary is needed for this categorical readout.

Use lambda = 1 as one fixed initial hypothesis, rather than searching a large grid. Keep the observed-label CE term at the same weight in both arms. The KL gradient is zero when parent and student agree at initialization. This avoids weakening the hard-label term silently by averaging two targets without retaining its original scale.

The aim is not to make intervals uniformly wider. It is to test whether a parent-dependent constraint preserves useful tail probabilities while allowing beneficial updates. This remains an unproven intervention.

## Bounded initial design

Before execution, register a new unused study ID, model/configuration/code hashes, teacher probabilities, eligibility, controls, failure behavior and analysis dates.

- Original 314-window corpus first, so data expansion does not confound the regularization test.
- Identical examples and batch ordering for matched ordinary/anchored runs.
- Learning rate 0.00002, batch size 16, at most 20 additional updates.
- Save additional updates 0, 5, 10 and 20; checkpoint zero stays eligible.
- Start with ordering seed 17: two updated runs, at most 40 optimizer updates total. This is a mechanism pilot, not a seed-robust accuracy claim.
- Check technical checkpoint capacity before launch. At updates 5, 10 and 20, two runs require up to six new retained states; checkpoint zero reuses the parent. If preservation capacity is unavailable, gate execution. Do not delete existing checkpoints or change billing. Any additional ordering run needs its own prespecified gate and sufficient retention capacity.
- Same optimizer-state restoration and inference interface as v21.
- Development seven-day pinball selects checkpoints; report median MAE, coverage, width, probability drift, no-change mass and failures alongside it.
- Numerical controls and existing fixed ensembles remain available only on matching cells.
- No new architecture, price support, quantile heads, RL, news or BLS feature intervention in this comparison.

First validate the KL gradient, normalization and first-step agreement with ordinary CE on explicitly synthetic contracts. Keep teacher probabilities hashed and unchanged. Preserve all negative runs and forbid expansion beyond the registered budget merely because a result is unfavorable.

## Evaluation limits and better data

The two v21 development origins are a weak basis for stable selection. Additional post-parent historical origins can be designated as **retrospective development**, with overlap and repeated testing disclosed. They cannot be renamed untouched evaluation.

Do not run historical rolling validation before the parent's training cutoff and call it leak-free: the parent already learned from later labels. Truly origin-safe historical folds require prefix-trained parents. Otherwise, evaluate the frozen existing parent and its continuations on subsequently observed prices.

Register any new future challenger separately before issuance. Do not change current v18/v19/v20/v21 candidates, dates or gates. Use matched inputs, exact source identities, immutable probabilities and verified publication timestamps. Shared origins and contracts remain dependent; ordering seeds are not independent market outcomes.

Prioritize new compatible, first-vintage price observations and genuine repricing episodes. A large number of overlapping old windows is not a substitute for new market regimes. Keep spot prices, source-defined quote medians and individual rate-card contracts separate. A fixed panel with little repricing may remain inconclusive; do not extend it until it wins.

## Why this is the next test

The first v21 pilot supplies no reason to assume another long unconstrained continuation will improve forecasting. The original-data arm revisited942 unique horizon examples; the expanded arm saw 1,600 of 11,511. Under the same compute budget, corpus composition and effective passes changed together. The result does not show that more data is generally harmful or that full training on the expanded corpus would behave identically.

A short anchored continuation changes one defined training mechanism while preserving the representation that previously worked. If it fails, retain the incumbent. If it improves development or reused historical results, describe that scope; only separately registered later outcomes can support a prospective improvement claim.

## Primary sources checked November 17, 2026

- [Tinker cross-entropy and soft-target API](https://tinker-docs.thinkingmachines.ai/tinker/losses/cross-entropy/): supports probability-weighted supervision. Our proposed regularizer is over the existing 19 forecasting choices, not a claim to reproduce a full-vocabulary distillation recipe.
- [Tinker custom differentiable losses](https://tinker-docs.thinkingmachines.ai/tutorials/core-concepts/loss-functions/): supports custom regularizers on log-probabilities. The existing forecaster already uses a differentiable categorical loss.
- [Thinking Machines' direct forecasting example](https://thinkingmachines.ai/news/inkling-2-small/), published November 5 and subsequently updated: reports a useful short recency top-up, an unhelpful additional epoch, and an RL trial that became overconfident. Those vendor-reported results use different data and metrics and do not establish gains for GPU prices.
- [Tinker SDFT recipe](https://tinker-docs.thinkingmachines.ai/cookbook/recipes/sdft/): motivates preserving capabilities through distribution matching, but explicitly warns about applying its released demonstrations to Qwen3.5-style long-thinking models. This proposal is a smaller categorical parent-anchor test, not an out-of-the-box application of that recipe.
- [Chernov, Fine-Tuning a Time Series Foundation Model with Wasserstein Loss](https://arxiv.org/abs/2409.15367),2024 preprint: reports a point-accuracy versus probabilistic-score tradeoff. It supports checking uncertainty rather than substituting better median error for better probabilistic forecasting; its scores are not comparable with this dataset.

Research retrieved today belongs to the current methods review. It is not backdated into frozen benchmark inputs.

Prospective improvement is not yet established.

## Matched exposure audit

The [read-only exposure workflow](../.github/workflows/audit-ce-continuation-exposure-v21.yml) reconstructs the exact batch-order hashes from the frozen input snapshot. Its first completed version is [here](../results/ce-continuation-v21/exposure/44151662905/exposure.json); it reruns after campaign completion.

Restricting both corpora to the same evaluation-series identities and seven-day horizon, the unchanged-level fraction is **77.73%** in the original historical pool and **77.99%** in the expanded pool. There are no small nonzero changes mapped to zero in those matched seven-day slices. The retrospective cohort has 15 unchanged outcomes out of 24, or 62.5%.

This identifies a marginal difference in the observed check period, not a proven causal explanation or evidence of a persistent market regime. It also argues against treating near-zero rounding as the principal demonstrated failure. Both corpora remain dominated by unchanged labels, while the full expanded pool includes a different mix of configurations. Conditional prediction quality cannot be deduced from those aggregate frequencies alone.
